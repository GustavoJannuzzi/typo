"""Camada `display`: letras gigantes e rotulos posicionados a mao sobre a arte.

O `compose.py` desenha a ficha de especime: titulo no alto, arte com moldura,
rodape centralizado, tudo em colunas que nunca se cruzam. Esta e a outra
familia de layout — a linha de display do especime SOLTA em cima da arte, com
glifos em corpo de dezenas de cm sangrando pela borda e um rotulo invertido
nomeando a obra. Mesma informacao, geometria nova.

Uma unica primitiva, a `mark`: um texto em corpo grande, posicionado em cm a
partir de uma borda da pagina, opcionalmente com caixa chapada atras e
rotacao. A letra gigante, o rotulo invertido (obra/autor) e a linha vertical da
lateral sao todos marks — nao ha tres blocos separados com tres conjuntos de
medidas, como no `compose.py`.

Duas decisoes que valem explicacao:

**Posicionamento pelo BBOX DE TINTA, nao pelas metricas da fonte.** `x_cm`/
`y_cm` diz onde a mancha preta comeca, e nao onde comeca a caixa em do glifo.
Com metricas, o vazio de ascender/descender — que num corpo de 40 cm passa de
10 cm — faria toda posicao parecer errada, e cada familia de fonte erraria de
um jeito diferente. Trimar pelo alfa resolve isso e torna a medida verificavel
com uma regua no papel.

**`x_cm` e recuo a partir da borda nomeada em `anchor`, e negativo sangra.**
Com `anchor: rt`, `x_cm: -6` joga 6 cm da letra pra fora da margem direita.
E a mesma logica do designer: "encosta na direita e deixa vazar".

A camada roda duas vezes por render: `layer: under` antes da passada de letras
(a malha do halftone atravessa a letra gigante, que aparece por tras dos vaos
de papel) e `layer: over` depois de tudo (letra chapada, o contraste da
referencia). Nenhuma das duas entra na chave de cache da cena.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFont

from typo import fonts
from typo.compose import spaced
from typo.config import ColorsCfg, DisplayCfg, Scale, hex_to_rgb

_MARK_KEYS = {
    "text",
    "size_cm",
    "size_mm",
    "x_cm",
    "y_cm",
    "anchor",
    "family",
    "variation",
    "weight",
    "color",
    "box",
    "box_color",
    "pad_mm",
    "layer",
    "rotate_deg",
    "leading",
    "letter_spacing",
}

_LAYERS = ("over", "under")
_WEIGHTS = ("bold", "regular")


@dataclass(frozen=True)
class Mark:
    """Uma marca normalizada e validada (ver `DisplayCfg` para as chaves)."""

    text: str
    size_mm: float
    x_cm: float = 0.0
    y_cm: float = 0.0
    anchor: str = "lt"
    family: str = ""
    variation: str = ""
    weight: str = "bold"
    color: tuple[int, int, int] = (17, 17, 17)
    box: bool = False
    box_color: tuple[int, int, int] = (17, 17, 17)
    pad_mm: float = 4.0
    layer: str = "over"
    rotate_deg: float = 0.0
    leading: float = 1.2
    letter_spacing: int = 0


# --------------------------------------------------------------------------- #
# parse / validacao
# --------------------------------------------------------------------------- #
def parse_marks(cfg: DisplayCfg, colors: ColorsCfg) -> list[Mark]:
    """`display.marks` (mapas do YAML) -> `Mark`s validadas.

    Levanta `ValueError` com todos os problemas de uma vez — quem chama e o
    `RenderConfig.validate()`, que acumula erros em vez de estourar no primeiro.
    """
    errs: list[str] = []
    marks: list[Mark] = []
    ink = hex_to_rgb(colors.ink)
    background = hex_to_rgb(colors.background)

    for i, raw in enumerate(cfg.marks):
        where = f"display.marks[{i}]"
        if not isinstance(raw, dict):
            errs.append(f"{where}: precisa ser um mapa, recebi {type(raw).__name__}")
            continue
        unknown = set(raw) - _MARK_KEYS
        if unknown:
            errs.append(
                f"{where}: chaves desconhecidas {sorted(unknown)} "
                f"(validas: {sorted(_MARK_KEYS)})"
            )
            continue

        text = str(raw.get("text") or "")
        if not text:
            errs.append(f"{where}: 'text' vazio")

        has_cm, has_mm = "size_cm" in raw, "size_mm" in raw
        if has_cm == has_mm:
            errs.append(f"{where}: declare 'size_cm' OU 'size_mm' (exatamente um)")
            size_mm = 10.0
        else:
            size_mm = float(raw["size_cm"]) * 10.0 if has_cm else float(raw["size_mm"])
            if size_mm <= 0:
                errs.append(f"{where}: corpo precisa ser > 0")

        anchor = str(raw.get("anchor") or "lt").lower()
        if len(anchor) != 2 or anchor[0] not in "lcr" or anchor[1] not in "tcb":
            errs.append(
                f"{where}: anchor={anchor!r} invalido (horizontal l|c|r + "
                "vertical t|c|b, ex 'lt', 'rb', 'ct')"
            )
            anchor = "lt"

        weight = str(raw.get("weight") or "bold").lower()
        if weight not in _WEIGHTS:
            errs.append(f"{where}: weight={weight!r} invalido (bold | regular)")
            weight = "bold"

        layer = str(raw.get("layer") or "over").lower()
        if layer not in _LAYERS:
            errs.append(f"{where}: layer={layer!r} invalido (over | under)")
            layer = "over"

        box = bool(raw.get("box", False))
        box_rgb = ink
        # rotulo invertido: sem cor declarada, o texto sai na cor do fundo
        color_rgb = background if box else ink
        for key, default in (("color", color_rgb), ("box_color", box_rgb)):
            value = raw.get(key)
            if not value:
                continue
            try:
                rgb = hex_to_rgb(value)
            except ValueError as exc:
                errs.append(f"{where}.{key}: {exc}")
                continue
            if key == "color":
                color_rgb = rgb
            else:
                box_rgb = rgb

        marks.append(
            Mark(
                text=text,
                size_mm=size_mm,
                x_cm=float(raw.get("x_cm", 0.0)),
                y_cm=float(raw.get("y_cm", 0.0)),
                anchor=anchor,
                family=str(raw.get("family") or ""),
                variation=str(raw.get("variation") or ""),
                weight=weight,
                color=color_rgb,
                box=box,
                box_color=box_rgb,
                pad_mm=float(raw.get("pad_mm", 4.0)),
                layer=layer,
                rotate_deg=float(raw.get("rotate_deg", 0.0)),
                leading=float(raw.get("leading", 1.2)),
                letter_spacing=int(raw.get("letter_spacing", 0)),
            )
        )

    if errs:
        raise ValueError("; ".join(errs))
    return marks


# --------------------------------------------------------------------------- #
# fonte
# --------------------------------------------------------------------------- #
@lru_cache(maxsize=128)
def load_font(
    path: str, size: int, variation: str = ""
) -> ImageFont.FreeTypeFont:
    """`fonts.load` + instancia nomeada de fonte variavel.

    A Bahnschrift (a DIN 1451 que vem no Windows) e variavel: o arquivo unico
    carrega de 'Light' a 'Bold Condensed'. Sem escolher a instancia, PIL
    desenha a default e a letra gigante sai leve demais para o papel de
    display. `variation` e o nome tal como a fonte declara.
    """
    font = ImageFont.truetype(path, max(1, int(size)))
    if variation:
        try:
            font.set_variation_by_name(variation)
        except Exception as exc:  # fonte estatica ou nome inexistente
            available = ""
            try:
                names = [
                    n.decode() if isinstance(n, bytes) else str(n)
                    for n in font.get_variation_names()
                ]
                available = f" (disponiveis: {names})"
            except Exception:
                available = " (a fonte nao e variavel)"
            raise ValueError(
                f"variation={variation!r} nao existe em {path}{available}"
            ) from exc
    return font


# --------------------------------------------------------------------------- #
# desenho
# --------------------------------------------------------------------------- #
def _tile(mark: Mark, pair_family: str, scale: Scale) -> Image.Image | None:
    """Desenha a marca num RGBA justo (trimado pelo alfa) e ja rotacionado."""
    pair = fonts.resolve_family(mark.family or pair_family)
    size_px = max(1, int(round(scale.mm(mark.size_mm))))
    font = load_font(
        pair.bold if mark.weight == "bold" else pair.regular, size_px, mark.variation
    )
    lines = [spaced(line, mark.letter_spacing) for line in mark.text.split("\n")]
    body = "\n".join(lines)
    spacing = int(round(size_px * (mark.leading - 1.0)))
    pad = int(round(scale.mm(mark.pad_mm))) if mark.box else 0

    probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    bbox = probe.multiline_textbbox((0, 0), body, font=font, spacing=spacing)
    tw = max(1, bbox[2] - bbox[0]) + 2 * pad
    th = max(1, bbox[3] - bbox[1]) + 2 * pad
    # margem de folga: bbox de metricas as vezes corta 1-2 px de tinta em
    # corpo grande, e um glifo de 40 cm cortado na borda salta aos olhos.
    slack = max(2, size_px // 32)

    tile = Image.new("RGBA", (tw + 2 * slack, th + 2 * slack), (0, 0, 0, 0))
    d = ImageDraw.Draw(tile)
    if mark.box:
        d.rectangle([slack, slack, slack + tw - 1, slack + th - 1], fill=mark.box_color)
    d.multiline_text(
        (slack + pad - bbox[0], slack + pad - bbox[1]),
        body,
        font=font,
        fill=mark.color,
        spacing=spacing,
    )
    if mark.rotate_deg:
        tile = tile.rotate(mark.rotate_deg, expand=True, resample=Image.BICUBIC)
    ink_box = tile.getbbox()
    if ink_box is None:
        return None
    return tile.crop(ink_box)


def _position(
    mark: Mark, tile: Image.Image, page: tuple[int, int], scale: Scale
) -> tuple[int, int]:
    pw, ph = page
    tw, th = tile.size
    dx, dy = int(round(scale.cm(mark.x_cm))), int(round(scale.cm(mark.y_cm)))
    ax, ay = mark.anchor[0], mark.anchor[1]
    x = dx if ax == "l" else (pw - tw - dx if ax == "r" else (pw - tw) // 2 + dx)
    y = dy if ay == "t" else (ph - th - dy if ay == "b" else (ph - th) // 2 + dy)
    return x, y


def draw(
    canvas: Image.Image,
    cfg: DisplayCfg,
    colors: ColorsCfg,
    art_family: str,
    scale: Scale,
    layer: str,
) -> int:
    """Desenha as marcas de `layer` ('under' | 'over'). Devolve quantas."""
    if not cfg.enabled:
        return 0
    if layer not in _LAYERS:
        raise ValueError(f"layer invalido: {layer!r} (use 'under' ou 'over')")
    drawn = 0
    for mark in parse_marks(cfg, colors):
        if mark.layer != layer:
            continue
        tile = _tile(mark, cfg.family or art_family, scale)
        if tile is None:  # texto que nao gerou tinta (so espacos)
            continue
        canvas.paste(tile, _position(mark, tile, canvas.size, scale), tile)
        drawn += 1
    return drawn


__all__ = ["Mark", "draw", "load_font", "parse_marks"]
