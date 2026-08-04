"""Selo tipografico: um QR code desenhado com as letras da propria obra.

Um selo por arte vendida. Aponta para `/s/<CODE>` no site, onde mora a ficha
daquela peca. As letras que preenchem os modulos escuros saem do MESMO .txt que
gerou a arte — o selo da Magalenha e feito de Magalenha, uns 380 caracteres, que
dao 4 a 5 versos.

Por que isto NAO passa pelo `typography.py`
-------------------------------------------
O halftone consome uma matriz de tons e a de um QR serviria — mas a passada de
letras nao pode desenhar a saida. Ela anda com baseline ondulada, avanca por
`gw * advance_factor + advance_pad` (passo derivado da largura do glifo, nunca
de uma grade), rotaciona cada glifo com `expand=True` e cola sem clipe nenhum.
Nao existe combinacao de sliders que garanta "este glifo nao invade o modulo
vizinho", e um vazamento mata o codigo. Dar grade ao motor seria mexer no
algoritmo, que a regra de ouro proibe.

Entao este modulo e uma primitiva nova, na familia do `display.py`: geometria
propria, reaproveitando `fonts` (resolucao de familia + carga), `Scale` (mm/cm
por dpi) e `text_source` (o stream de caracteres). O motor nao e tocado.

As tres garantias de que a letra fica presa a grade
---------------------------------------------------
1. **Modulo em pixel inteiro.** `module_px = round(...)` e a imagem tem
   exatamente `total * module_px` de lado. O tamanho fisico REAL sai disso
   (`size_cm` no resultado), nunca o contrario: pedir 7,0 cm e receber 6,94 cm
   e o certo, porque a alternativa e borda de modulo em pixel fracionario, que
   borra na reamostragem e e' o comeco de toda leitura que falha.
2. **Clipe duro.** Cada glifo e desenhado num tile de `module_px x module_px` e
   colado na celula dele. Vazar nao e' improvavel: e' impossivel, porque nao ha
   para onde. O ajuste de corpo (`fill_frac`) e' estetica; o clipe e' a garantia.
3. **Nucleo solido** (`core_ratio`). O decodificador amostra o CENTRO do modulo
   depois de achar a grade. Letra redonda (o, e, a, c, 0) tem contra-forma vazia
   justo no centro — sem nucleo, todo `o` do texto vira um bit errado, e isso
   nao e' ruido de impressao, e' erro sistematico comendo a margem do ECC. O
   nucleo enche a contra-forma. Custa um engrossamento invisivel a um palmo.

   E' ele que carrega a robustez, nao o `min_coverage`: filtrar por cobertura
   nao distingue pontuacao de letra estreita (ver a medicao no campo), entao
   selecionar caractere e' um instrumento cego. Escurecer o centro nao e'.

Zonas protegidas
----------------
Saem SOLIDAS, nunca tipografadas: finders, separadores, timing, alignment,
format info, version info e o modulo escuro obrigatorio. As tres primeiras sao
as citadas em qualquer tutorial; as outras matam o codigo do mesmo jeito:

- **alignment** — o decodificador usa para corrigir perspectiva (papel curvo,
  foto de angulo). Tipografar isso quebra a leitura fora do angulo reto.
- **format info** — carrega o nivel de ECC e a mascara. Tem BCH proprio, mas o
  nivel H protege DADOS, nao o format info: se as duas copias se perdem, o
  codigo inteiro e' ilegivel. `protect_format=False` libera esses 31 modulos
  para letra — e a primeira coisa a experimentar se os cantos ficarem pesados
  demais, com o custo medido pelo teste de decodificacao.

Quem diz o que e' cada modulo e' o `segno`, via `matrix_iter(verbose=True)`:
proteger zona de funcao e' uma consulta a `segno.consts`, nao uma
reimplementacao das tabelas de posicao da ISO 18004.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
from PIL import Image, ImageDraw

from typo import fonts, text_source
from typo.config import Scale, TextCfg, hex_to_rgb


class SealError(RuntimeError):
    pass


def _segno():
    """Import tardio: `segno` e' o extra [seal], nao dependencia do motor."""
    try:
        import segno
        from segno import consts
    except ImportError as exc:  # pragma: no cover - depende do ambiente
        raise SealError(
            "o selo precisa do `segno`, que nao e' dependencia do motor.\n"
            '    .venv/Scripts/python.exe -m pip install -e ".[seal]"'
        ) from exc
    return segno, consts


# --------------------------------------------------------------------------- #
# tipos de modulo
# --------------------------------------------------------------------------- #
def _type_sets():
    """(escuros, de_dado, de_format) a partir das constantes nomeadas do segno.

    O segno codifica claro < 512 <= escuro, mas montar por nome sobrevive a uma
    eventual renumeracao — e deixa legivel o que entra em cada conjunto.
    """
    _, c = _segno()
    dark = frozenset(
        {
            c.TYPE_DARKMODULE,
            c.TYPE_DATA_DARK,
            c.TYPE_FINDER_PATTERN_DARK,
            c.TYPE_ALIGNMENT_PATTERN_DARK,
            c.TYPE_TIMING_DARK,
            c.TYPE_FORMAT_DARK,
            c.TYPE_VERSION_DARK,
        }
    )
    data = frozenset({c.TYPE_DATA_DARK, c.TYPE_DATA_LIGHT})
    fmt = frozenset({c.TYPE_FORMAT_DARK, c.TYPE_FORMAT_LIGHT})
    return dark, data, fmt


# --------------------------------------------------------------------------- #
# spec / resultado
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class SealSpec:
    """Tudo que define um selo. Sem I/O de projeto e sem rede."""

    payload: str  # a URL que o celular abre
    text_path: str  # o .txt da obra — de onde vem cada letra
    family: str = "DejaVu Sans Condensed"
    size_cm: float = 7.0  # alvo; o real sai arredondado, ver SealResult.size_cm
    dpi: int = 600
    ecc: Literal["l", "m", "q", "h"] = "h"
    quiet_modules: int = 4  # obrigatorio pela spec; 4 e' o minimo
    ink: str = "#111111"
    background: str = "#FFFFFF"
    bold: bool = True  # glifo mais gordo = mais tinta por modulo
    #: fracao do modulo que o glifo ocupa. 1.0 encosta na borda da celula e as
    #: letras de modulos vizinhos se tocam, o que borra a grade na impressao.
    fill_frac: float = 0.82
    #: diametro do nucleo solido, x modulo. 0 desliga.
    #:
    #: 0.18 nao e' chute: e' o menor valor que empata com um QR LISO na bateria
    #: de degradacoes do tests/test_seal.py (23 leituras: reducao ate' 160px,
    #: blur, rotacao, jpeg, contraste lavado). A varredura deu
    #:
    #:     core   0.00 -> 2/23      core   0.18 -> 23/23
    #:     core   0.10 -> 20/23     core   0.25+ -> 23/23  (nao compra nada)
    #:     QR liso (controle)      -> 23/23
    #:
    #: Duas coisas ficam ditas ai. Sem nucleo o selo NAO escaneia — as letras
    #: sozinhas nao fazem QR, por larga margem. E acima de 0.18 so' se paga em
    #: contra-forma: a 0.35 o 'o' e o 'e' viram bolota e um quarto do alfabeto
    #: deixa de ser legivel, sem nenhum ganho de leitura.
    core_ratio: float = 0.18
    #: cobertura minima de tinta do glifo no modulo; abaixo disso o cursor pula
    #: para o proximo caractere.
    #:
    #: NAO e' um filtro de pontuacao, embora pareca. Medindo a DejaVu Sans bold
    #: num modulo de 40px: j=0.113, virgula=0.119, i=0.133, l=0.147, m=0.183,
    #: e o grosso do alfabeto entre 0.24 e 0.34. A virgula cai ENTRE o j e o i —
    #: nao existe limiar que separe pontuacao de letra estreita. Um piso alto
    #: (0.18) come todo i, j e l: "Magalenha" vira "Magaenha" no selo, o que
    #: estraga justamente a peca que existe para ser lida de perto.
    #: Entao o piso e' baixo de proposito: pega glifo que a fonte nao tem e
    #: caractere sem tinta nenhuma. Quem garante o modulo escuro e' o
    #: `core_ratio`, nao isto.
    min_coverage: float = 0.02
    max_tries: int = 8
    protect_format: bool = True

    def validate(self) -> "SealSpec":
        errs: list[str] = []
        if not self.payload:
            errs.append("payload vazio")
        if not self.text_path:
            errs.append("text_path vazio")
        if self.size_cm <= 0:
            errs.append("size_cm precisa ser > 0")
        if self.dpi < 72:
            errs.append("dpi baixo demais (< 72) para um selo impresso")
        if self.ecc not in ("l", "m", "q", "h"):
            errs.append(f"ecc invalido: {self.ecc!r} (use l, m, q ou h)")
        if self.quiet_modules < 4:
            errs.append(
                f"quiet_modules={self.quiet_modules}: a spec exige 4 modulos de "
                "zona silenciosa em volta"
            )
        if not 0 < self.fill_frac <= 1:
            errs.append("fill_frac precisa estar em (0, 1]")
        if not 0 <= self.core_ratio < 1:
            errs.append("core_ratio precisa estar em [0, 1)")
        if not 0 <= self.min_coverage < 1:
            errs.append("min_coverage precisa estar em [0, 1)")
        for label, value in (("ink", self.ink), ("background", self.background)):
            try:
                hex_to_rgb(value)
            except ValueError as exc:
                errs.append(f"{label}: {exc}")
        if errs:
            raise SealError("SealSpec invalida:\n  - " + "\n  - ".join(errs))
        return self


@dataclass(frozen=True)
class SealResult:
    image: Image.Image
    payload: str
    version: int
    mode: str  # 'alphanumeric' economiza modulos; ver make_seal.py
    ecc: str
    modules: int  # lado do codigo, sem a quiet zone
    module_px: int
    module_mm: float
    size_cm: float  # REAL, ja arredondado ao pixel inteiro
    letters: int  # modulos de dado escuros que viraram glifo
    solid: int  # modulos de funcao desenhados solidos
    skipped: int  # caracteres pulados por cobertura baixa
    fallbacks: int  # modulos onde nenhum candidato passou (so nucleo/solido)
    text: str  # as letras efetivamente usadas, em ordem de varredura
    warnings: tuple[str, ...] = ()

    def summary(self) -> str:
        w, h = self.image.size
        return (
            f"{self.payload}\n"
            f"  V{self.version} ecc={self.ecc.upper()} modo={self.mode}  "
            f"{self.modules}x{self.modules} modulos (+{(w // self.module_px - self.modules) // 2} quiet)\n"
            f"  {w}x{h}px @ {self.module_px}px/modulo = {self.module_mm:.2f}mm  "
            f"selo {self.size_cm:.2f}cm\n"
            f"  {self.letters} letras  {self.solid} solidos  "
            f"{self.skipped} pulados  {self.fallbacks} sem glifo"
        )


# --------------------------------------------------------------------------- #
# glifos
# --------------------------------------------------------------------------- #
class _TileCache:
    """Tiles `m x m` com o glifo centrado pelo bbox de tinta, e a cobertura.

    Todo modulo tem o mesmo tamanho, entao a chave e' so' o caractere: o corpo
    da fonte e' resolvido uma vez por letra e reusado nos ~380 modulos.

    O tile tem EXATAMENTE o tamanho do modulo. Isso e' o clipe duro: o que
    passar da celula e' cortado pelo Pillow ao desenhar, nao por checagem
    minha — que e' onde erros deste tipo costumam se esconder.
    """

    __slots__ = ("_font_path", "_module_px", "_target", "_ink", "_cache")

    def __init__(self, font_path: str, module_px: int, fill_frac: float, ink) -> None:
        self._font_path = font_path
        self._module_px = module_px
        self._target = max(1.0, module_px * fill_frac)
        self._ink = ink
        self._cache: dict[str, tuple[Image.Image, float] | None] = {}

    def _fit_size(self, ch: str) -> tuple[int, tuple[int, int, int, int]] | None:
        """Maior corpo cujo bbox de tinta cabe em `target`. None = sem tinta.

        Encolhe ate' caber, depois cresce de 1 em 1 ate' estourar, e devolve o
        ultimo que coube. Guardar o `best` em vez de confiar na convergencia
        importa: sem ele, estourar o teto de iteracoes devolveria None e o
        caractere seria descartado como "sem tinta" — um pulo silencioso, que e'
        o tipo de erro que so' aparece olhando o selo pronto e achando estranho.
        """
        target = self._target
        best: tuple[int, tuple[int, int, int, int]] | None = None
        size = max(2, int(round(target * 1.4)))  # tinta e' menor que o em
        for _ in range(16):
            bbox = fonts.load(self._font_path, size).getbbox(ch)
            w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
            if w <= 0 or h <= 0:
                return best  # espaco, glifo ausente, ou corpo pequeno demais
            if max(w, h) <= target:
                if best is None or size > best[0]:
                    best = (size, bbox)
                size += 1
                continue
            if best is not None:
                return best  # passou do ponto: fica com o ultimo que coube
            nxt = int(size * target / max(w, h))
            size = max(2, nxt if nxt < size else size - 1)
        return best

    def get(self, ch: str) -> tuple[Image.Image, float] | None:
        """(tile, cobertura) ou None se o caractere nao produz tinta."""
        if ch in self._cache:
            return self._cache[ch]

        result: tuple[Image.Image, float] | None = None
        fitted = self._fit_size(ch)
        if fitted is not None:
            size, bbox = fitted
            m = self._module_px
            tile = Image.new("RGBA", (m, m), (0, 0, 0, 0))
            w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
            # centra o BBOX DE TINTA, nao a caixa em da fonte: num corpo destes
            # o vazio de ascender jogaria a letra pra baixo do centro do modulo,
            # que e' justamente onde o decodificador amostra
            ImageDraw.Draw(tile).text(
                ((m - w) / 2 - bbox[0], (m - h) / 2 - bbox[1]),
                ch,
                font=fonts.load(self._font_path, size),
                fill=self._ink + (255,),
            )
            alpha = np.asarray(tile, dtype=np.uint8)[:, :, 3]
            coverage = float(alpha.mean()) / 255.0
            result = (tile, coverage)

        self._cache[ch] = result
        return result


# --------------------------------------------------------------------------- #
# render
# --------------------------------------------------------------------------- #
def render(spec: SealSpec) -> SealResult:
    """Desenha o selo. Sem rede, sem leitura de project.yaml — so' a spec."""
    spec.validate()
    segno, _ = _segno()
    dark_types, data_types, format_types = _type_sets()

    # make_qr, nao make: `make` cai em Micro QR quando o payload e' curto, e
    # Micro nao tem alignment pattern nem a mesma estrutura de format info —
    # metade do que este modulo protege deixaria de existir sem aviso.
    qr = segno.make_qr(spec.payload, error=spec.ecc)
    matrix = [list(row) for row in qr.matrix_iter(scale=1, border=0, verbose=True)]
    n = len(matrix)
    total = n + 2 * spec.quiet_modules

    module_px = int(round(Scale(spec.dpi).cm(spec.size_cm) / total))
    warnings: list[str] = []
    if module_px < 3:
        raise SealError(
            f"modulo de {module_px}px: {spec.size_cm}cm a {spec.dpi}dpi nao cabe "
            f"{total} modulos. Aumente size_cm ou dpi."
        )
    if module_px < 12:
        warnings.append(
            f"modulo de {module_px}px: abaixo de ~12px a letra nao desenha "
            f"(vira textura). Suba o dpi para a letra aparecer."
        )

    side = total * module_px
    ink = hex_to_rgb(spec.ink)
    canvas = Image.new("RGB", (side, side), hex_to_rgb(spec.background))
    draw = ImageDraw.Draw(canvas)

    pair = fonts.resolve_family(spec.family)
    if spec.bold and pair.synthetic_bold:
        warnings.append(
            f"a familia {pair.family!r} nao tem bold de verdade (regular == bold): "
            "o glifo sai mais leve e cobre menos modulo."
        )
    tiles = _TileCache(
        pair.bold if spec.bold else pair.regular, module_px, spec.fill_frac, ink
    )

    stream = text_source.build_stream_cached(
        TextCfg(text_path=spec.text_path, mode="chars", repeat=1)
    )
    if not stream:
        raise SealError(f"texto vazio: {spec.text_path}")

    core_px = int(round(module_px * spec.core_ratio))
    origin = spec.quiet_modules * module_px
    cursor = 0
    letters = solid = skipped = fallbacks = 0
    used: list[str] = []

    # varredura em ordem de leitura: o texto do selo anda como o da arte
    for my in range(n):
        for mx in range(n):
            kind = matrix[my][mx]
            is_dark = kind in dark_types
            typographable = kind in data_types or (
                not spec.protect_format and kind in format_types
            )
            if not is_dark:
                continue  # modulo claro: papel, sempre

            x0 = origin + mx * module_px
            y0 = origin + my * module_px

            if not typographable:
                # zona de funcao: solida, sem excecao
                draw.rectangle(
                    [x0, y0, x0 + module_px - 1, y0 + module_px - 1], fill=ink
                )
                solid += 1
                continue

            # nucleo primeiro: garante o centro escuro mesmo sob letra redonda
            if core_px >= 1:
                cx, cy = x0 + module_px / 2, y0 + module_px / 2
                r = core_px / 2
                draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=ink)

            tile = None
            for _ in range(max(1, spec.max_tries)):
                ch = stream[cursor % len(stream)]
                cursor += 1
                got = tiles.get(ch)
                if got is not None and got[1] >= spec.min_coverage:
                    tile = got[0]
                    used.append(ch)
                    break
                skipped += 1
            if tile is None:
                # nenhum dos candidatos cobriu o bastante. Solido, nao so' o
                # nucleo: o modulo precisa ficar escuro de qualquer jeito, e o
                # codigo vem antes da estetica. `fallbacks` no resultado diz
                # quantas vezes isso aconteceu — se for muito, o texto ou a
                # fonte e' que estao errados para o tamanho de modulo.
                draw.rectangle(
                    [x0, y0, x0 + module_px - 1, y0 + module_px - 1], fill=ink
                )
                fallbacks += 1
                continue

            canvas.paste(tile, (x0, y0), tile)
            letters += 1

    return SealResult(
        image=canvas,
        payload=spec.payload,
        version=qr.version,
        mode=qr.mode,
        ecc=spec.ecc,
        modules=n,
        module_px=module_px,
        module_mm=module_px / spec.dpi * 25.4,
        size_cm=side / spec.dpi * 2.54,
        letters=letters,
        solid=solid,
        skipped=skipped,
        fallbacks=fallbacks,
        text="".join(used),
        warnings=tuple(warnings),
    )


__all__ = ["SealError", "SealResult", "SealSpec", "render"]
