"""RenderConfig — fonte unica de parametros, compartilhada por UI, CLI e engine.

Todos os defaults sao o preset `magalenha`, extraidos literalmente do `print_v4.py`.
Constantes que no script original eram *pixels* estao anotadas com `_px` e sao
escaladas por `dpi / REFERENCE_DPI`, de forma que em 150 dpi o valor bate exato
com o original e em outros dpi a arte escala proporcionalmente.
"""
from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass, replace
from typing import Any, Literal

# DPI em que o print_v4.py foi calibrado. Constantes em px se referem a este dpi.
REFERENCE_DPI = 150


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def hex_to_rgb(value: str | tuple) -> tuple[int, int, int]:
    """'#963A2A' -> (150, 58, 42). Aceita tupla/lista ja pronta."""
    if isinstance(value, (tuple, list)):
        if len(value) != 3:
            raise ValueError(f"cor deve ter 3 componentes, recebi {value!r}")
        return tuple(int(c) for c in value)  # type: ignore[return-value]
    s = str(value).strip().lstrip("#")
    if len(s) == 3:
        s = "".join(c * 2 for c in s)
    if len(s) != 6:
        raise ValueError(f"cor hex invalida: {value!r}")
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))


def rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02X}{:02X}{:02X}".format(*rgb)


class Scale:
    """Conversao de unidades para um DPI efetivo (preview ou export)."""

    __slots__ = ("dpi",)

    def __init__(self, dpi: float) -> None:
        self.dpi = float(dpi)

    def mm(self, x: float) -> float:
        """mm -> px (equivalente ao `mm()` do print_v4.py)."""
        return x / 25.4 * self.dpi

    def cm(self, x: float) -> float:
        return x / 2.54 * self.dpi

    def px(self, px_at_reference: float) -> float:
        """px medido a 150 dpi -> px no dpi efetivo."""
        return px_at_reference * self.dpi / REFERENCE_DPI


# --------------------------------------------------------------------------- #
# grupos de configuracao
# --------------------------------------------------------------------------- #
@dataclass
class SourceCfg:
    image_path: str = ""
    #: (left, top, right, bottom) em px da imagem original; None = imagem inteira
    crop: tuple[int, int, int, int] | None = (600, 55, 1420, 782)


@dataclass
class MaskCfg:
    """Isola as figuras do fundo (fundo branco de verdade)."""

    enabled: bool = True
    lum_threshold: float = 0.56
    min_component_frac: float = 0.0009
    close_iters: int = 2
    dilate_frac: float = 0.006  # x altura da arte (usada pela paisagem)
    interior_fill_min: float = 0.30  # piso de preenchimento dentro da figura
    #: borra a luminancia ANTES de aplicar lum_threshold (so para decidir
    #: dentro/fora da mascara; a nitidez do halftone continua vindo da
    #: luminancia original). 0 = desligado (default do preset magalenha,
    #: identico ao print_v4.py). Uso: fotos com textura fina (tweed, tricot)
    #: onde o proprio tecido oscila acima/abaixo do limiar e fragmenta a
    #: mascara num contorno fractal. Ver projects/emicida.
    blur_sigma: float = 0.0
    border_frac: float = 0.03  # rampa da janela de borda
    border_threshold: float = 0.5  # janela xw*yw precisa passar disso
    hit_threshold: float = 0.4  # fracao de mascara na sonda p/ considerar "dentro"


@dataclass
class TextCfg:
    text_path: str = ""
    mode: Literal["phrases", "words", "chars"] = "phrases"
    separator: str = "   "
    repeat: int = 60


@dataclass
class FontCfg:
    family: str = "DejaVu Sans Condensed"
    base_line_mm: float = 3.5  # "Tamanho da fonte" (altura de linha)
    size_min_mm: float = 1.5
    size_max_ratio: float = 1.7  # size_max = base_line x ratio
    size_gamma: float = 1.5  # "Divergencia de tamanho" (>1 = mais contraste)
    bold_threshold: float = 0.5  # "Espessura" (menor = mais glifos em bold)
    min_line_px: float = 9.0  # piso do print_v4: max(9, mm(3.5))
    min_size_px: float = 7.0  # piso do print_v4: max(7, mm(1.5))


@dataclass
class FlowCfg:
    """Curvatura / "flexibilidade das linhas"."""

    undulation_amp_ratio: float = 0.4  # x base_line
    undulation_wavelength_ratio: float = 0.5  # x largura da arte
    undulation_row_phase: float = 0.5  # rad por linha
    rotation_amp_deg: float = 13.0
    rotation_wavelength_ratio: float = 0.22  # x largura da arte
    rotation_row_phase: float = 0.4
    rotation_y_phase_amp: float = 0.7
    rotation_y_wavelength_ratio: float = 0.32  # x altura da arte
    rotation_clamp_deg: float = 18.0
    rotation_quantum_deg: float = 3.0  # quantizacao p/ cache de glifos
    flex: float = 1.0  # multiplicador global de ondulacao + rotacao


@dataclass
class LayoutCfg:
    """"Posicao das letras"."""

    advance_factor: float = 0.98  # espacamento horizontal entre glifos
    advance_pad_px: float = 1.0  # `+1` do print_v4 (px @150dpi)
    row_step_ratio: float = 0.9  # x base_line
    blank_step_ratio: float = 0.5  # passo fora da mascara, x base_line
    space_advance_factor: float = 0.34  # passo quando o char e espaco, x font size
    jitter_px: float = 0.0  # deslocamento aleatorio opcional (px @150dpi)
    jitter_seed: int = 0
    baseline_offset_ratio: float = 0.72  # y do glifo = baseline - fs * este fator
    probe_ahead_ratio: float = 0.7  # largura da sonda, x base_line


@dataclass
class AccentCfg:
    """Destaque de cor (ex.: o vestido)."""

    enabled: bool = True
    color: str = "#963A2A"  # terracota
    source_rule: str = "red"  # regra p/ detectar a regiao na imagem fonte
    red_min: int = 105  # r > red_min
    red_delta: int = 30  # r-g > delta e r-b > delta
    central_x: tuple[float, float] = (0.30, 0.70)
    hit_threshold: float = 0.25  # fracao de accent na sonda p/ pintar


@dataclass
class LandscapeCfg:
    """Paisagem ao fundo, em contorno fino."""

    enabled: bool = True
    edge_gain: float = 6.5
    shade_dark: int = 150  # cinza no contorno mais forte
    shade_light: int = 206  # cinza no contorno mais fraco
    band: tuple[float, float] = (0.06, 0.66)  # faixa vertical (ceu/montanha)
    band_ramp: tuple[float, float] = (0.06, 0.10)  # rampas de entrada/saida da faixa
    side_ramp_frac: float = 0.05
    size_mm: tuple[float, float] = (1.3, 2.2)
    size_min_clamp_mm: float = 1.2
    floor: float = 0.14  # abaixo disso nao desenha
    min_window: float = 0.05
    min_darkness: float = 0.04  # ignora fundo claro chapado
    blur_sigma: float = 1.0
    row_step_ratio: float = 0.95  # x base_line
    max_y_ratio: float = 0.72  # ate onde a paisagem desce
    advance_factor: float = 1.35
    advance_pad_px: float = 2.0
    space_advance_factor: float = 0.5
    skip_step_ratio: float = 0.7  # passo quando nao ha contorno, x base_line
    probe_ahead_ratio: float = 0.7  # largura da sonda, x base_line
    rotation_amp_deg: float = 10.0
    rotation_wavelength_ratio: float = 0.3
    rotation_clamp_deg: float = 12.0
    baseline_offset_ratio: float = 0.7


@dataclass
class ColorsCfg:
    ink: str = "#111111"
    background: str = "#FFFFFF"
    subtitle: str = "#696969"
    footer: str = "#3C3C3C"
    frame: str = "#BCBCBC"


@dataclass
class PageCfg:
    mode: Literal["from_art", "fixed"] = "from_art"
    art_height_cm: float = 88.0
    margin_top_cm: float = 13.0
    margin_bottom_cm: float = 10.5
    margin_side_cm: float = 7.0
    width_cm: float | None = None  # modo fixed
    height_cm: float | None = None  # modo fixed
    dpi_export: int = 150
    preview_max_px: int = 900
    #: o preview renderiza internamente a `preview_max_px * supersample` e so
    #: entao reduz por LANCZOS. Sem isso, `int(mm(base_line))` colapsa em dpi
    #: baixo e a densidade do preview nao bate com a do export. O fator e fixo
    #: de proposito: se dependesse de `base_line_mm`, mexer no slider de
    #: tamanho invalidaria o cache da cena (mascara/paisagem) a cada arrasto.
    preview_supersample: float = 2.0


@dataclass
class TextBlocksCfg:
    title: str = "MAGALENHA"
    subtitle: str = "SÉRGIO MENDES · BRASILEIRO"
    footer: str = "EXPERIMENTO TIPOGRÁFICO — GUSTAVO JANNUZZI"
    accent_squares: bool = True
    frame: bool = True
    # geometria (mm), tal como no print_v4.py
    title_size_mm: float = 32.0
    title_y_mm: float = 15.0
    subtitle_size_mm: float = 6.8
    subtitle_dy_mm: float = 34.0
    subtitle_dx_px: float = 4.0
    squares_dy_mm: float = 46.0
    square_size_mm: float = 4.6
    square_gap_mm: float = 8.2
    square_count: int = 4
    footer_size_mm: float = 7.6
    footer_dy_mm: float = 26.0
    frame_inset_mm: float = 12.0
    frame_width_mm: float = 0.4
    letter_spacing: int = 1  # espacos inseridos entre letras de subtitulo/rodape


# --------------------------------------------------------------------------- #
# config principal
# --------------------------------------------------------------------------- #
@dataclass
class RenderConfig:
    source: SourceCfg = field(default_factory=SourceCfg)
    mask: MaskCfg = field(default_factory=MaskCfg)
    text: TextCfg = field(default_factory=TextCfg)
    font: FontCfg = field(default_factory=FontCfg)
    flow: FlowCfg = field(default_factory=FlowCfg)
    layout: LayoutCfg = field(default_factory=LayoutCfg)
    accent: AccentCfg = field(default_factory=AccentCfg)
    landscape: LandscapeCfg = field(default_factory=LandscapeCfg)
    colors: ColorsCfg = field(default_factory=ColorsCfg)
    page: PageCfg = field(default_factory=PageCfg)
    text_blocks: TextBlocksCfg = field(default_factory=TextBlocksCfg)
    name: str = "magalenha"

    # ---------------------------------------------------------------- merge --
    def merge(self, overrides: dict[str, Any] | None) -> "RenderConfig":
        """Retorna uma copia com `overrides` (dict aninhado) aplicados."""
        if not overrides:
            return self.copy()
        return _merge_dataclass(self, overrides)

    def copy(self) -> "RenderConfig":
        return _deep_copy_dataclass(self)

    def to_dict(self) -> dict[str, Any]:
        return _to_dict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RenderConfig":
        return cls().merge(data)

    @classmethod
    def from_project(cls, project_yaml: str) -> "RenderConfig":
        """Atalho: `RenderConfig.from_project('projects/x/project.yaml')`."""
        from typo.project import Project

        return Project.load(project_yaml).config()

    # ------------------------------------------------------------- validate --
    def validate(self) -> "RenderConfig":
        errs: list[str] = []
        if not self.source.image_path:
            errs.append("source.image_path vazio")
        if self.source.crop is not None:
            c = self.source.crop
            if len(c) != 4:
                errs.append("source.crop precisa ter 4 valores (l, t, r, b)")
            elif c[2] <= c[0] or c[3] <= c[1]:
                errs.append(f"source.crop invalido: {c}")
        if not self.text.text_path:
            errs.append("text.text_path vazio")
        if self.text.mode not in ("phrases", "words", "chars"):
            errs.append(f"text.mode invalido: {self.text.mode!r}")
        if self.text.repeat < 1:
            errs.append("text.repeat precisa ser >= 1")
        if self.font.base_line_mm <= 0:
            errs.append("font.base_line_mm precisa ser > 0")
        if self.font.size_min_mm <= 0:
            errs.append("font.size_min_mm precisa ser > 0")
        if self.font.size_max_ratio <= 0:
            errs.append("font.size_max_ratio precisa ser > 0")
        if self.font.size_gamma <= 0:
            errs.append("font.size_gamma precisa ser > 0")
        if self.page.mode not in ("from_art", "fixed"):
            errs.append(f"page.mode invalido: {self.page.mode!r}")
        if self.page.mode == "from_art" and self.page.art_height_cm <= 0:
            errs.append("page.art_height_cm precisa ser > 0")
        if self.page.mode == "fixed" and not (self.page.width_cm and self.page.height_cm):
            errs.append("page.mode='fixed' exige page.width_cm e page.height_cm")
        if self.page.dpi_export < 24:
            errs.append("page.dpi_export baixo demais (< 24)")
        if self.page.preview_max_px < 200:
            errs.append("page.preview_max_px baixo demais (< 200)")
        if self.accent.source_rule != "red":
            errs.append(
                f"accent.source_rule={self.accent.source_rule!r} nao implementado "
                "(apenas 'red'); veja typo/mask.py"
            )
        for label, value in (
            ("colors.ink", self.colors.ink),
            ("colors.background", self.colors.background),
            ("accent.color", self.accent.color),
        ):
            try:
                hex_to_rgb(value)
            except ValueError as exc:
                errs.append(f"{label}: {exc}")
        if errs:
            raise ValueError("RenderConfig invalida:\n  - " + "\n  - ".join(errs))
        return self

    # -------------------------------------------------------------- derived --
    def art_size(self, crop_w: int, crop_h: int, dpi: float) -> tuple[int, int]:
        """Tamanho da arte (px) para um dpi, preservando o aspecto do crop."""
        p = self.page
        if p.mode == "from_art":
            art_h = int(p.art_height_cm / 2.54 * dpi)
            art_w = int(art_h * crop_w / crop_h)
        else:
            avail_h_cm = float(p.height_cm) - p.margin_top_cm - p.margin_bottom_cm
            avail_w_cm = float(p.width_cm) - 2 * p.margin_side_cm
            if avail_h_cm <= 0 or avail_w_cm <= 0:
                raise ValueError("margens maiores que a pagina em page.mode='fixed'")
            art_h = int(avail_h_cm / 2.54 * dpi)
            art_w = int(art_h * crop_w / crop_h)
            max_w = int(avail_w_cm / 2.54 * dpi)
            if art_w > max_w:
                art_w = max_w
                art_h = int(art_w * crop_h / crop_w)
        return max(1, art_w), max(1, art_h)

    def page_size(self, art_w: int, art_h: int, dpi: float) -> tuple[int, int]:
        """Tamanho da pagina (px). No modo from_art, replica o print_v4.py."""
        p = self.page
        if p.mode == "from_art":
            pw = int((art_w / dpi * 2.54 + 2 * p.margin_side_cm) / 2.54 * dpi)
            ph = int(
                (p.art_height_cm + p.margin_top_cm + p.margin_bottom_cm) / 2.54 * dpi
            )
        else:
            pw = int(float(p.width_cm) / 2.54 * dpi)
            ph = int(float(p.height_cm) / 2.54 * dpi)
        return pw, ph

    def page_cm(self, art_w: int, art_h: int, dpi: float) -> tuple[float, float]:
        pw, ph = self.page_size(art_w, art_h, dpi)
        return pw / dpi * 2.54, ph / dpi * 2.54

    def preview_dpi(self, crop_w: int, crop_h: int) -> tuple[float, float]:
        """(dpi interno do preview, dpi alvo da imagem mostrada).

        Depende so da geometria da pagina — nunca dos parametros de
        tipografia — para que os sliders reaproveitem a cena em cache.
        """
        p = self.page
        art_w, art_h = self.art_size(crop_w, crop_h, p.dpi_export)
        pw_cm, ph_cm = self.page_cm(art_w, art_h, p.dpi_export)
        long_in = max(pw_cm, ph_cm) / 2.54
        target = p.preview_max_px / long_in
        return target * max(1.0, p.preview_supersample), target


# --------------------------------------------------------------------------- #
# merge / copy utilitarios
# --------------------------------------------------------------------------- #
_TUPLE_FIELDS = {"crop", "central_x", "band", "band_ramp", "size_mm"}


def _coerce(name: str, current: Any, value: Any) -> Any:
    if value is None:
        return None
    if name in _TUPLE_FIELDS and isinstance(value, (list, tuple)):
        return tuple(value)
    if isinstance(current, bool):
        if isinstance(value, str):
            return value.strip().lower() in ("1", "true", "yes", "on", "sim")
        return bool(value)
    if isinstance(current, int) and not isinstance(current, bool):
        return int(value)
    if isinstance(current, float):
        return float(value)
    return value


def _merge_dataclass(obj: Any, overrides: dict[str, Any]) -> Any:
    known = {f.name for f in fields(obj)}
    unknown = set(overrides) - known
    if unknown:
        raise ValueError(
            f"campos desconhecidos em {type(obj).__name__}: {sorted(unknown)} "
            f"(validos: {sorted(known)})"
        )
    changes: dict[str, Any] = {}
    for key, value in overrides.items():
        current = getattr(obj, key)
        if is_dataclass(current) and isinstance(value, dict):
            changes[key] = _merge_dataclass(current, value)
        else:
            changes[key] = _coerce(key, current, value)
    base = _deep_copy_dataclass(obj)
    return replace(base, **changes)


def _deep_copy_dataclass(obj: Any) -> Any:
    changes = {
        f.name: _deep_copy_dataclass(getattr(obj, f.name))
        for f in fields(obj)
        if is_dataclass(getattr(obj, f.name))
    }
    return replace(obj, **changes) if changes else replace(obj)


def _to_dict(obj: Any) -> Any:
    if is_dataclass(obj):
        return {f.name: _to_dict(getattr(obj, f.name)) for f in fields(obj)}
    if isinstance(obj, tuple):
        return list(obj)
    return obj


def clamp(v: float, lo: float, hi: float) -> float:
    return lo if v < lo else (hi if v > hi else v)


__all__ = [
    "REFERENCE_DPI",
    "RenderConfig",
    "SourceCfg",
    "MaskCfg",
    "TextCfg",
    "FontCfg",
    "FlowCfg",
    "LayoutCfg",
    "AccentCfg",
    "LandscapeCfg",
    "ColorsCfg",
    "PageCfg",
    "TextBlocksCfg",
    "Scale",
    "hex_to_rgb",
    "rgb_to_hex",
    "clamp",
]
