"""Texto por regiao da arte — qual .txt (e qual tinta) vale em cada ponto.

O motor do `print_v4.py` tem UM stream de caracteres varrendo a arte inteira: a
imagem toda e feita do mesmo texto. Aqui a arte pode ser dividida em regioes
desenhadas a mao, cada uma com o seu proprio arquivo e, opcionalmente, a sua
propria tinta — o que permite uma figura falar uma coisa e a do lado outra.

    text:
      file: text/fundo.txt              # stream 0: o que vale fora das regioes
      regions:
        - name: datena
          file: text/datena.txt
          ink: "#6E6E6E"
          polygons: [[[0.00, 0.28], [0.36, 0.24], [0.36, 0.99], [0.00, 0.99]]]
        - name: bancadas
          file: text/brasil.txt
          boxes: [[0.0, 0.86, 1.0, 1.0]]

Geometria em **fracao do tamanho da arte** (0..1), nao em px: o mesmo
project.yaml serve para o preview a 40 dpi e para o export a 150. `polygons` e
uma lista de poligonos (cada um uma lista de pares `[x, y]`); `boxes` e acucar
para retangulos `[x0, y0, x1, y1]`. As duas coisas somam.

**A ordem da lista e ordem de pintura**: quem vem depois cobre quem veio antes.
E o que resolve sobreposicao — a mao de uma figura em cima do objeto que ela
segura — sem precisar recortar poligono com furo.

O resultado e um `TextField`: um mapa achatado de indices (uint8, 0 = stream
default) que a `typography.draw` consulta no centro da sonda de cada glifo, do
mesmo jeito que a paleta amostra a cor. Achatado em `bytes` de proposito:
indexar um ndarray 2D devolve `np.uint8` (alocacao por acesso) e isso esta no
loop mais quente do motor.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from PIL import Image, ImageDraw

from typo import text_source
from typo.config import TextCfg, hex_to_rgb

#: o mapa e uint8 e o indice 0 e o stream default
MAX_REGIONS = 255

_KEYS = {"name", "text_path", "mode", "separator", "repeat", "ink", "polygons", "boxes"}


@dataclass(frozen=True)
class Region:
    """Uma regiao ja validada (o que sai do parse do project.yaml)."""

    name: str
    text_path: str
    mode: str  # '' = herda de text.mode
    separator: str | None  # None = herda de text.separator
    repeat: int  # 0 = herda de text.repeat
    ink: tuple[int, int, int] | None  # None = herda a tinta normal
    polygons: tuple[tuple[tuple[float, float], ...], ...]


class TextField:
    """Qual stream e qual tinta valem em cada ponto da arte.

    `index is None` e o caminho do `print_v4.py`: um stream so, sem consulta
    nenhuma no loop.
    """

    __slots__ = ("streams", "inks", "index", "width", "names")

    def __init__(
        self,
        streams: tuple[tuple[str, ...], ...],
        inks: tuple[tuple[int, int, int] | None, ...],
        index: bytes | None,
        width: int,
        names: tuple[str, ...] = (),
    ) -> None:
        self.streams = streams
        self.inks = inks
        self.index = index
        self.width = width
        self.names = names

    @property
    def enabled(self) -> bool:
        return self.index is not None


# --------------------------------------------------------------------------- #
# parse
# --------------------------------------------------------------------------- #
def _polygon(raw, where: str) -> tuple[tuple[float, float], ...]:
    if not isinstance(raw, (list, tuple)) or len(raw) < 3:
        raise ValueError(f"{where}: um poligono precisa de pelo menos 3 pontos")
    pts = []
    for i, pt in enumerate(raw):
        if not isinstance(pt, (list, tuple)) or len(pt) != 2:
            raise ValueError(f"{where}[{i}]={pt!r}: cada ponto e um par [x, y] em fracao")
        pts.append((float(pt[0]), float(pt[1])))
    return tuple(pts)


def _box(raw, where: str) -> tuple[tuple[float, float], ...]:
    if not isinstance(raw, (list, tuple)) or len(raw) != 4:
        raise ValueError(f"{where}={raw!r}: uma caixa e [x0, y0, x1, y1] em fracao")
    x0, y0, x1, y1 = (float(v) for v in raw)
    if x1 <= x0 or y1 <= y0:
        raise ValueError(f"{where}={raw!r}: precisa de x1 > x0 e y1 > y0")
    return ((x0, y0), (x1, y0), (x1, y1), (x0, y1))


def parse_regions(cfg: TextCfg) -> tuple[Region, ...]:
    """`text.regions` (lista de mapas do YAML) -> tupla de `Region` validada."""
    out: list[Region] = []
    if len(cfg.regions) > MAX_REGIONS:
        raise ValueError(
            f"text.regions: {len(cfg.regions)} regioes, o maximo e {MAX_REGIONS} "
            "(o mapa de indices e uint8)"
        )
    for i, raw in enumerate(cfg.regions):
        if not isinstance(raw, dict):
            raise ValueError(f"text.regions[{i}] precisa ser um mapa, recebi {raw!r}")
        unknown = set(raw) - _KEYS
        if unknown:
            raise ValueError(
                f"text.regions[{i}]: chaves desconhecidas {sorted(unknown)} "
                f"(validas: {sorted(_KEYS)})"
            )
        name = str(raw.get("name") or f"regiao {i}")
        where = f"text.regions[{i}] ({name})"
        text_path = str(raw.get("text_path") or "")
        if not text_path:
            raise ValueError(f"{where}: falta o arquivo de texto (`file`)")

        polys = [_polygon(p, f"{where}.polygons[{j}]") for j, p in enumerate(raw.get("polygons") or [])]
        polys += [_box(b, f"{where}.boxes[{j}]") for j, b in enumerate(raw.get("boxes") or [])]
        if not polys:
            raise ValueError(f"{where}: sem geometria — declare `polygons` ou `boxes`")

        mode = str(raw.get("mode") or "")
        if mode and mode not in ("phrases", "words", "chars"):
            raise ValueError(f"{where}: mode invalido: {mode!r}")
        repeat = int(raw.get("repeat") or 0)
        if repeat < 0:
            raise ValueError(f"{where}: repeat precisa ser >= 0 (0 = herda)")
        ink_raw = raw.get("ink") or ""
        try:
            ink = hex_to_rgb(ink_raw) if ink_raw else None
        except ValueError as exc:
            raise ValueError(f"{where}.ink: {exc}") from None
        sep = raw.get("separator")

        out.append(
            Region(
                name=name,
                text_path=text_path,
                mode=mode,
                separator=None if sep is None else str(sep),
                repeat=repeat,
                ink=ink,
                polygons=tuple(polys),
            )
        )
    return tuple(out)


# --------------------------------------------------------------------------- #
# rasterizacao
# --------------------------------------------------------------------------- #
@lru_cache(maxsize=2)
def _rasterize(polys_by_region: tuple, art_w: int, art_h: int) -> bytes:
    """Mapa achatado de indices (0 = default, 1..n = ordem das regioes)."""
    img = Image.new("L", (art_w, art_h), 0)
    draw = ImageDraw.Draw(img)
    for i, polys in enumerate(polys_by_region, start=1):
        for poly in polys:
            draw.polygon(
                [(x * art_w, y * art_h) for x, y in poly], fill=i
            )
    return img.tobytes()


def build_field(cfg: TextCfg, art_w: int, art_h: int) -> TextField:
    """Monta o `TextField` do render: streams, tintas e mapa de indices.

    Sem `text.regions` devolve o campo degenerado (um stream, `index=None`), que
    e exatamente o caminho do `print_v4.py`.
    """
    base = text_source.build_stream_cached(cfg)
    regions = parse_regions(cfg)
    if not regions:
        return TextField((base,), (None,), None, art_w, ("",))

    streams = [base]
    inks: list[tuple[int, int, int] | None] = [None]
    names = [""]
    for r in regions:
        streams.append(
            text_source.build_stream_cached(
                TextCfg(
                    text_path=r.text_path,
                    mode=r.mode or cfg.mode,
                    separator=cfg.separator if r.separator is None else r.separator,
                    repeat=r.repeat or cfg.repeat,
                )
            )
        )
        inks.append(r.ink)
        names.append(r.name)

    index = _rasterize(tuple(r.polygons for r in regions), art_w, art_h)
    return TextField(tuple(streams), tuple(inks), index, art_w, tuple(names))


def clear_cache() -> None:
    _rasterize.cache_clear()


__all__ = [
    "MAX_REGIONS",
    "Region",
    "TextField",
    "build_field",
    "clear_cache",
    "parse_regions",
]
