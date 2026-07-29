"""Passada principal de letras — o coracao do print_v4.py.

Varredura por linhas com baseline ondulada; em cada posicao mede a escuridao
local dentro da mascara, mapeia para o tamanho da fonte, aplica bold acima do
limiar, rotaciona o glifo pelo fluxo e pinta com accent ou tinta.

    A = 0.4*LINE_H; row = 0; yb = LINE_H
    while yb < art_h:  ...  yb += LINE_H*0.9; row += 1
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass

from PIL import Image

from typo.config import FlowCfg, FontCfg, LayoutCfg, MaskCfg, clamp
from typo.fonts import GlyphCache
from typo.image_prep import Field, PreparedImage


@dataclass
class TypographyStats:
    glyphs: int = 0
    probes: int = 0
    rows: int = 0


def draw(
    canvas: Image.Image,
    prep: PreparedImage,
    mask: Field,
    lum: Field,
    accent: Field | None,
    stream,
    glyphs: GlyphCache,
    font_cfg: FontCfg,
    flow: FlowCfg,
    layout: LayoutCfg,
    mask_cfg: MaskCfg,
    line_h: int,
    size_min: int,
    size_max: int,
    ink: tuple[int, int, int],
    accent_color: tuple[int, int, int],
    accent_hit: float,
    origin: tuple[int, int],
    advance_pad: float,
    jitter_px: float,
) -> TypographyStats:
    art_w, art_h = prep.art_w, prep.art_h
    ox, oy = origin
    stats = TypographyStats()

    fill_min = float(mask_cfg.interior_fill_min)
    fill_span = max(1.0 - fill_min, 1e-6)
    gamma = float(font_cfg.size_gamma)
    bold_threshold = float(font_cfg.bold_threshold)
    size_span = size_max - size_min

    probe_w = line_h * layout.probe_ahead_ratio
    half_h = line_h * 0.5
    row_step = line_h * layout.row_step_ratio
    blank_step = line_h * layout.blank_step_ratio

    amp = flow.undulation_amp_ratio * line_h * flow.flex
    wave = max(art_w * flow.undulation_wavelength_ratio, 1e-6)
    rot_amp = flow.rotation_amp_deg * flow.flex
    rot_wave = max(art_w * flow.rotation_wavelength_ratio, 1e-6)
    rot_y_wave = max(art_h * flow.rotation_y_wavelength_ratio, 1e-6)
    rot_clamp = flow.rotation_clamp_deg
    quantum = glyphs.quantum

    stream_len = len(stream)
    idx = 0
    rng = random.Random(layout.jitter_seed) if jitter_px > 0 else None
    has_accent = accent is not None

    row = 0
    yb = float(line_h)
    while yb < art_h:
        row_phase_rot = row * flow.rotation_row_phase + flow.rotation_y_phase_amp * math.sin(
            2 * math.pi * yb / rot_y_wave
        )
        row_phase_und = row * flow.undulation_row_phase
        x = 0.0
        while x < art_w:
            y = yb + amp * math.sin(2 * math.pi * x / wave + row_phase_und)

            x0 = max(0, int(x))
            x1 = min(art_w, int(x + probe_w))
            y0 = max(0, int(y - half_h))
            y1 = min(art_h, int(y + half_h))
            stats.probes += 1
            if x1 <= x0 or y1 <= y0 or mask.mean(y0, y1, x0, x1) <= mask_cfg.hit_threshold:
                x += blank_step
                continue

            dark = (1.0 - lum.mean(y0, y1, x0, x1)) ** gamma
            if dark < fill_min:
                dark = fill_min
            fs = int(size_min + size_span * (dark - fill_min) / fill_span)
            fs = max(size_min, min(size_max, fs))
            bold = dark > bold_threshold

            ch = stream[idx % stream_len]
            idx += 1
            if ch == " ":
                x += fs * layout.space_advance_factor
                continue

            is_accent = has_accent and accent.mean(y0, y1, x0, x1) > accent_hit
            ang = rot_amp * math.sin(2 * math.pi * x / rot_wave + row_phase_rot)
            step = int(round(clamp(ang, -rot_clamp, rot_clamp) / quantum))
            tile, gw = glyphs.tile(
                ch, fs, bold, step, accent_color if is_accent else ink
            )

            px = ox + x
            py = oy + y - fs * layout.baseline_offset_ratio
            if rng is not None:
                px += rng.uniform(-jitter_px, jitter_px)
                py += rng.uniform(-jitter_px, jitter_px)
            canvas.paste(tile, (int(px), int(py)), tile)
            stats.glyphs += 1
            x += gw * layout.advance_factor + advance_pad
        yb += row_step
        row += 1
        stats.rows += 1
    return stats


__all__ = ["TypographyStats", "draw"]
