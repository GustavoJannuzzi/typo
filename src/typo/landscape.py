"""Camada de paisagem: contorno fino em cinza claro, atras das figuras.

Traducao do bloco "---- paisagem (contornos finos, atras das figuras) ----" e
da "passada da paisagem" do print_v4.py. Le apenas o *contorno* (edge-dominado),
restrito a uma faixa vertical e ao lado de fora da mascara dilatada.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter, sobel

from typo.config import LandscapeCfg, Scale, clamp
from typo.fonts import GlyphCache
from typo.image_prep import Field, PreparedImage


@dataclass(frozen=True)
class LandscapeFields:
    edge: Field  # gradiente normalizado 0..1
    window: Field  # faixa valida (banda vertical x rampa lateral x fora da mascara)


def build_fields(
    prep: PreparedImage, dilated: np.ndarray, cfg: LandscapeCfg
) -> LandscapeFields:
    art_w, art_h = prep.art_w, prep.art_h
    smooth = gaussian_filter(prep.lum, cfg.blur_sigma)
    edge = np.hypot(sobel(smooth, axis=1), sobel(smooth, axis=0))
    edge /= edge.max() + 1e-6

    yy = (np.arange(art_h) / art_h)[:, None]
    lo, hi = cfg.band
    ramp_lo, ramp_hi = cfg.band_ramp
    vband = np.clip((yy - lo) / max(ramp_lo, 1e-9), 0, 1) * np.clip(
        (hi - yy) / max(ramp_hi, 1e-9), 0, 1
    )
    vband = np.repeat(vband, art_w, axis=1)
    xs = np.arange(art_w)
    xwb = np.clip(
        np.minimum(xs, art_w - 1 - xs) / max(cfg.side_ramp_frac * art_w, 1e-9), 0, 1
    )[None, :]
    window = vband * xwb * (~dilated)

    use_sat = prep.use_sat
    return LandscapeFields(edge=Field(edge, use_sat), window=Field(window, use_sat))


def draw(
    canvas: Image.Image,
    prep: PreparedImage,
    fields: LandscapeFields,
    lum: Field,
    stream,
    glyphs: GlyphCache,
    cfg: LandscapeCfg,
    scale: Scale,
    line_h: int,
    origin: tuple[int, int],
) -> int:
    """Desenha a paisagem no canvas. Devolve quantos glifos foram pintados."""
    art_w, art_h = prep.art_w, prep.art_h
    ox, oy = origin
    probe_w = line_h * cfg.probe_ahead_ratio
    row_h = max(1, int(line_h * cfg.row_step_ratio))
    fs_lo = scale.mm(cfg.size_mm[0])
    fs_hi = scale.mm(cfg.size_mm[1])
    fs_floor = max(1, int(scale.mm(cfg.size_min_clamp_mm)))
    pad = scale.px(cfg.advance_pad_px)
    shade_span = cfg.shade_light - cfg.shade_dark
    stream_len = len(stream)
    idx = 0
    painted = 0

    def probe(x: float, y: float) -> float:
        x0 = max(0, int(x))
        x1 = min(art_w, int(x + probe_w))
        y0 = max(0, int(y - line_h * 0.5))
        y1 = min(art_h, int(y + line_h * 0.5))
        if x1 <= x0 or y1 <= y0:
            return 0.0
        w = fields.window.mean(y0, y1, x0, x1)
        if w < cfg.min_window:
            return 0.0
        e = fields.edge.mean(y0, y1, x0, x1)
        d = 1.0 - lum.mean(y0, y1, x0, x1)
        if d < cfg.min_darkness:  # ignora fundo claro chapado
            return 0.0
        return min(1.0, e * cfg.edge_gain) * w

    yb = row_h
    while yb < art_h * cfg.max_y_ratio:
        x = 0.0
        while x < art_w:
            score = probe(x, yb)
            if score < cfg.floor:
                x += line_h * cfg.skip_step_ratio
                continue
            capped = min(1.0, score)
            fs = max(fs_floor, int(fs_lo + (fs_hi - fs_lo) * capped))
            ch = stream[idx % stream_len]
            idx += 1
            if ch == " ":
                x += fs * cfg.space_advance_factor
                continue
            shade = int(cfg.shade_light - shade_span * capped)
            color = (shade, shade, shade)
            ang = cfg.rotation_amp_deg * math.sin(
                2 * math.pi * x / (art_w * cfg.rotation_wavelength_ratio)
            )
            step = int(
                round(
                    clamp(ang, -cfg.rotation_clamp_deg, cfg.rotation_clamp_deg)
                    / glyphs.quantum
                )
            )
            tile, gw = glyphs.tile(ch, fs, False, step, color)
            canvas.paste(
                tile,
                (int(ox + x), int(oy + yb - fs * cfg.baseline_offset_ratio)),
                tile,
            )
            painted += 1
            x += gw * cfg.advance_factor + pad
        yb += row_h
    return painted


__all__ = ["LandscapeFields", "build_fields", "draw"]
