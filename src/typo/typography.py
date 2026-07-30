"""Passada principal de letras — o coracao do print_v4.py.

Varredura por linhas com baseline ondulada; em cada posicao mede a escuridao
local dentro da mascara, mapeia para o tamanho da fonte, aplica bold acima do
limiar, rotaciona o glifo pelo fluxo e pinta com a paleta, o accent ou a tinta.

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
from typo.palette import PaletteMap
from typo.regions import TextField


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
    palette: PaletteMap | None,
    text_field: TextField,
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

    # sem `text.regions` isto e um stream so e `region_map is None`: o caminho
    # do print_v4.py, com um cursor unico. Com regioes, cada stream tem o SEU
    # cursor — se todos dividissem o mesmo indice, mudar de regiao picaria as
    # frases no meio e o texto deixaria de se ler em pedacos.
    streams = text_field.streams
    stream_lens = [len(s) for s in streams]
    cursors = [0] * len(streams)
    region_inks = text_field.inks
    region_map = text_field.index
    region_w = text_field.width
    rng = random.Random(layout.jitter_seed) if jitter_px > 0 else None
    has_accent = accent is not None
    palette_at = palette.at if palette is not None else None

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

            # max(0.0, ...): ruido de ponto flutuante da SAT (soma acumulada em
            # float64) pode fazer lum.mean() passar de 1.0 por uma fracao
            # infinitesimal em regioes de branco puro; sem o clamp, uma base
            # negativa elevada a gamma fracionario vira numero complexo.
            dark = max(0.0, 1.0 - lum.mean(y0, y1, x0, x1)) ** gamma
            if dark < fill_min:
                dark = fill_min
            fs = int(size_min + size_span * (dark - fill_min) / fill_span)
            fs = max(size_min, min(size_max, fs))
            bold = dark > bold_threshold

            cy = (y0 + y1) >> 1
            cx = (x0 + x1) >> 1
            rid = 0 if region_map is None else region_map[cy * region_w + cx]
            ch = streams[rid][cursors[rid] % stream_lens[rid]]
            cursors[rid] += 1
            if ch == " ":
                x += fs * layout.space_advance_factor
                continue

            # a tinta declarada na regiao ganha de tudo: ela e uma decisao de
            # projeto grafico, enquanto paleta e accent sao derivados da imagem.
            # A paleta, por sua vez, ganha do accent quando ligada — ela ja
            # cobre o caso geral (inclusive os neutros), e sobrepor os dois
            # daria uma cor unica invadindo blocos que a tabela resolveu de
            # proposito.
            region_ink = region_inks[rid]
            if region_ink is not None:
                color = region_ink
            elif palette_at is not None:
                color = palette_at(cy, cx)
            elif has_accent and accent.mean(y0, y1, x0, x1) > accent_hit:
                color = accent_color
            else:
                color = ink
            ang = rot_amp * math.sin(2 * math.pi * x / rot_wave + row_phase_rot)
            step = int(round(clamp(ang, -rot_clamp, rot_clamp) / quantum))
            tile, gw = glyphs.tile(ch, fs, bold, step, color)

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
