"""Orquestracao do pipeline: `render(config, mode) -> PIL.Image`.

Ordem (identica ao `main()` do print_v4.py):

    1. image_prep  — abre, recorta, redimensiona, calcula luminancia
    2. mask        — isola as figuras (+ regiao de accent)
    3. landscape   — contorno fino ao fundo, fora da mascara dilatada
    4. typography  — passada principal de letras
    5. compose     — titulo, subtitulo, quadradinhos, rodape, moldura

A camada `display` (letras gigantes / rotulo invertido, desligada por default)
entra fora dessa ordem: as marcas `under` antes do passo 3 e as `over` depois
do passo 5. Ver `typo/display.py`.

O passo pesado (1-3) fica numa `Scene` memoizada por (imagem, crop, resolucao,
params de mascara/accent/paisagem), de forma que mexer nos sliders de
tipografia so re-roda o passo 4.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Literal

from PIL import Image

from typo import (
    compose,
    display as display_mod,
    landscape,
    mask as mask_mod,
    palette as palette_mod,
    regions as regions_mod,
    text_source,
    typography,
)
from typo.config import RenderConfig, Scale, hex_to_rgb
from typo.fonts import FontPair, GlyphCache, resolve_family
from typo.image_prep import Field, PreparedImage, crop_size, prepare

Mode = Literal["preview", "export"]


# --------------------------------------------------------------------------- #
# cena precomputada (o que os sliders de tipografia NAO invalidam)
# --------------------------------------------------------------------------- #
@dataclass
class Scene:
    prep: PreparedImage
    mask_result: mask_mod.MaskResult
    lum: Field
    mask: Field
    accent: Field | None
    palette: palette_mod.PaletteMap | None
    landscape_fields: landscape.LandscapeFields | None


_SCENE_CACHE: dict[tuple, Scene] = {}
_SCENE_ORDER: list[tuple] = []
_SCENE_MAX = 3


def _scene_key(cfg: RenderConfig, art_w: int, art_h: int, dpi: float) -> tuple:
    return (
        cfg.source.image_path,
        repr(cfg.source.crop),
        art_w,
        art_h,
        round(dpi, 4),
        repr(cfg.mask),
        repr(cfg.accent),
        repr(cfg.palette),
        repr(cfg.landscape),
    )


def build_scene(cfg: RenderConfig, art_w: int, art_h: int, dpi: float) -> Scene:
    key = _scene_key(cfg, art_w, art_h, dpi)
    hit = _SCENE_CACHE.get(key)
    if hit is not None:
        return hit

    prep = prepare(cfg.source.image_path, cfg.source.crop, art_w, art_h, dpi)
    mask_result = mask_mod.build(prep, cfg.mask, cfg.accent)
    use_sat = prep.use_sat
    accent_field = (
        Field(mask_result.accent, use_sat)
        if cfg.accent.enabled and bool(mask_result.accent.any())
        else None
    )
    land = (
        landscape.build_fields(prep, mask_result.dilated, cfg.landscape)
        if cfg.landscape.enabled
        else None
    )
    scene = Scene(
        prep=prep,
        mask_result=mask_result,
        lum=Field(prep.lum, use_sat),
        mask=Field(mask_result.mask, use_sat),
        accent=accent_field,
        palette=palette_mod.build(prep, cfg.palette),
        landscape_fields=land,
    )
    _SCENE_CACHE[key] = scene
    _SCENE_ORDER.append(key)
    while len(_SCENE_ORDER) > _SCENE_MAX:
        _SCENE_CACHE.pop(_SCENE_ORDER.pop(0), None)
    return scene


def clear_cache() -> None:
    _SCENE_CACHE.clear()
    _SCENE_ORDER.clear()


# --------------------------------------------------------------------------- #
# resultado
# --------------------------------------------------------------------------- #
@dataclass
class RenderResult:
    image: Image.Image
    mode: str
    dpi: float
    page_cm: tuple[float, float]
    art_px: tuple[int, int]
    font: FontPair
    stats: dict = field(default_factory=dict)

    def summary(self) -> str:
        w, h = self.image.size
        return (
            f"{self.mode}: {w}x{h}px  pagina {self.page_cm[0]:.1f}x{self.page_cm[1]:.1f}cm "
            f"@ {self.dpi:.1f}dpi  fonte {self.font.family}  "
            f"glifos {self.stats.get('glyphs', 0)} (+{self.stats.get('landscape_glyphs', 0)} paisagem)  "
            f"tiles {self.stats.get('tiles', 0)}  {self.stats.get('seconds', 0):.1f}s"
        )


#: abaixo desta amplitude (max - min dos canais) a cor e cinza, e um
#: quadradinho cinza no cabecalho nao comunica nada
_CHIP_MIN_CHROMA = 24


def _chip_colors(
    pmap: palette_mod.PaletteMap | None,
) -> list[tuple[int, int, int]] | None:
    """Cores *cromaticas* da paleta, na ordem dos stops e sem repetir.

    Os neutros da tabela (traco, papel, branco) existem para manter o desenho
    em tinta — nao sao a paleta da arte. A fileira do cabecalho mostra so as
    cores, que e a informacao que ela carrega.
    """
    if pmap is None:
        return None
    chips: list[tuple[int, int, int]] = []
    for color in pmap.colors:
        if max(color) - min(color) < _CHIP_MIN_CHROMA or color in chips:
            continue
        chips.append(color)
    return chips or None


# --------------------------------------------------------------------------- #
# render
# --------------------------------------------------------------------------- #
def render(config: RenderConfig, mode: Mode = "preview") -> Image.Image:
    """Renderiza a arte inteira. Ver `render_result` para os metadados."""
    return render_result(config, mode).image


def render_result(config: RenderConfig, mode: Mode = "preview") -> RenderResult:
    if mode not in ("preview", "export"):
        raise ValueError(f"mode invalido: {mode!r} (use 'preview' ou 'export')")
    config.validate()
    t0 = time.perf_counter()

    crop_w, crop_h = crop_size(config.source.image_path, config.source.crop)
    if mode == "export":
        dpi = float(config.page.dpi_export)
        downscale_to = None
    else:
        dpi, _target = config.preview_dpi(crop_w, crop_h)
        downscale_to = config.page.preview_max_px

    scale = Scale(dpi)
    art_w, art_h = config.art_size(crop_w, crop_h, dpi)
    scene = build_scene(config, art_w, art_h, dpi)

    # --- medidas de tipografia (LINE_H / FS_MIN / FS_MAX do print_v4.py) ---
    f = config.font
    line_h = max(int(scale.px(f.min_line_px)), int(scale.mm(f.base_line_mm)))
    size_min = max(int(scale.px(f.min_size_px)), int(scale.mm(f.size_min_mm)))
    size_max = max(size_min, int(line_h * f.size_max_ratio))

    pw, ph = config.page_size(art_w, art_h, dpi)
    canvas = Image.new("RGB", (pw, ph), hex_to_rgb(config.colors.background))
    ox = (pw - art_w) // 2
    oy = int(scale.cm(config.page.margin_top_cm))

    # a paisagem e contorno de FUNDO, fora da mascara: fica sempre no stream
    # default, mesmo quando a arte esta dividida em regioes.
    stream = text_source.build_stream_cached(config.text)
    text_field = regions_mod.build_field(config.text, art_w, art_h)
    pair = resolve_family(f.family)
    glyphs = GlyphCache(pair, config.flow.rotation_quantum_deg)

    ink = hex_to_rgb(config.colors.ink)
    accent_rgb = hex_to_rgb(config.accent.color)

    # letras gigantes ATRAS da malha: a passada de letras desenha por cima e a
    # mancha aparece pelos vaos de papel entre os glifos.
    display_under = display_mod.draw(
        canvas, config.display, config.colors, f.family, scale, layer="under"
    )

    land_glyphs = 0
    if config.landscape.enabled and scene.landscape_fields is not None:
        land_glyphs = landscape.draw(
            canvas=canvas,
            prep=scene.prep,
            fields=scene.landscape_fields,
            lum=scene.lum,
            stream=stream,
            glyphs=glyphs,
            cfg=config.landscape,
            scale=scale,
            line_h=line_h,
            origin=(ox, oy),
        )

    stats = typography.draw(
        canvas=canvas,
        prep=scene.prep,
        mask=scene.mask,
        lum=scene.lum,
        accent=scene.accent,
        palette=scene.palette,
        text_field=text_field,
        glyphs=glyphs,
        font_cfg=config.font,
        flow=config.flow,
        layout=config.layout,
        mask_cfg=config.mask,
        line_h=line_h,
        size_min=size_min,
        size_max=size_max,
        ink=ink,
        accent_color=accent_rgb,
        accent_hit=config.accent.hit_threshold,
        origin=(ox, oy),
        advance_pad=scale.px(config.layout.advance_pad_px),
        jitter_px=scale.px(config.layout.jitter_px),
    )

    compose.draw(
        canvas=canvas,
        pair=pair,
        blocks=config.text_blocks,
        colors=config.colors,
        accent_rgb=accent_rgb,
        accent_enabled=config.accent.enabled,
        scale=scale,
        art_origin_x=ox,
        bottom_margin_cm=config.page.margin_bottom_cm,
        chip_colors=_chip_colors(scene.palette),
    )

    display_over = display_mod.draw(
        canvas, config.display, config.colors, f.family, scale, layer="over"
    )

    page_cm = (pw / dpi * 2.54, ph / dpi * 2.54)
    if downscale_to is not None and max(pw, ph) > downscale_to:
        ratio = downscale_to / max(pw, ph)
        canvas = canvas.resize(
            (max(1, int(pw * ratio)), max(1, int(ph * ratio))), Image.LANCZOS
        )

    return RenderResult(
        image=canvas,
        mode=mode,
        dpi=dpi,
        page_cm=page_cm,
        art_px=(art_w, art_h),
        font=pair,
        stats={
            "glyphs": stats.glyphs,
            "probes": stats.probes,
            "rows": stats.rows,
            "landscape_glyphs": land_glyphs,
            "display_marks": display_under + display_over,
            "tiles": len(glyphs),
            "seconds": time.perf_counter() - t0,
        },
    )


__all__ = ["Mode", "RenderResult", "Scene", "build_scene", "clear_cache", "render", "render_result"]
