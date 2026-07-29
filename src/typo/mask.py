"""Mascara das figuras + regiao de accent.

Traducao literal do bloco "---- mascara das figuras ----" do print_v4.py:

    fg = lum < 0.56
    fg = binary_fill_holes(fg); fg = binary_closing(fg, iterations=2)
    lbl,n = label(fg); mantem componentes com area > 0.0009*art_w*art_h
    mask = fill_holes(...) & (janela de borda > 0.5)
    red  = (r>105)&(r-g>30)&(r-b>30)&mask & (0.30*W < x < 0.70*W)
    mdil = binary_dilation(mask, iterations=max(2, int(art_h*0.006)))
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import ndimage as ndi
from scipy.ndimage import gaussian_filter

from typo.config import AccentCfg, MaskCfg
from typo.image_prep import PreparedImage


@dataclass(frozen=True)
class MaskResult:
    mask: np.ndarray  # bool (h, w) — figuras isoladas
    dilated: np.ndarray  # bool (h, w) — mascara dilatada (usada pela paisagem)
    accent: np.ndarray  # bool (h, w) — regiao de destaque de cor


def border_window(art_w: int, art_h: int, frac: float) -> np.ndarray:
    """Janela que apaga uma faixa nas bordas da arte (xw * yw)."""
    xs = np.arange(art_w)
    ys = np.arange(art_h)
    xw = np.clip(np.minimum(xs, art_w - 1 - xs) / max(frac * art_w, 1e-9), 0, 1)[None, :]
    yw = np.clip(np.minimum(ys, art_h - 1 - ys) / max(frac * art_h, 1e-9), 0, 1)[:, None]
    return xw * yw


def accent_region(prep: PreparedImage, mask: np.ndarray, cfg: AccentCfg) -> np.ndarray:
    """Regiao de destaque na imagem fonte, restrita a `mask` e a faixa central."""
    if not cfg.enabled:
        return np.zeros_like(mask)
    if cfg.source_rule != "red":
        raise NotImplementedError(
            f"accent.source_rule={cfg.source_rule!r} nao implementado. "
            "Hoje so existe a regra 'red' (r>red_min e r-g/r-b > red_delta). "
            "TODO: regras por matiz (hsv) ou por poligono desenhado na UI."
        )
    r, g, b = prep.r, prep.g, prep.b
    sel = (
        (r > cfg.red_min)
        & (r - g > cfg.red_delta)
        & (r - b > cfg.red_delta)
        & mask
    )
    xs = np.arange(prep.art_w)[None, :]
    lo, hi = cfg.central_x
    return sel & (xs > prep.art_w * lo) & (xs < prep.art_w * hi)


def build(prep: PreparedImage, cfg: MaskCfg, accent_cfg: AccentCfg) -> MaskResult:
    art_w, art_h = prep.art_w, prep.art_h
    win = border_window(art_w, art_h, cfg.border_frac) > cfg.border_threshold

    if cfg.enabled:
        # blur_sigma so afeta a decisao dentro/fora da mascara; a luminancia
        # crua (prep.lum) continua sendo usada por typography.py para o
        # mapeamento de tamanho/peso. Com blur_sigma=0.0 (default) este ramo
        # nem roda: mesmo array, mesmo resultado do print_v4.py.
        lum_for_mask = (
            gaussian_filter(prep.lum, cfg.blur_sigma) if cfg.blur_sigma > 0 else prep.lum
        )
        fg = lum_for_mask < cfg.lum_threshold
        fg = ndi.binary_fill_holes(fg)
        if cfg.close_iters > 0:
            fg = ndi.binary_closing(fg, iterations=int(cfg.close_iters))
        lbl, _n = ndi.label(fg)
        sizes = np.bincount(lbl.ravel())
        keep = set(np.where(sizes > cfg.min_component_frac * art_w * art_h)[0]) - {0}
        mask = np.isin(lbl, list(keep))
        mask = ndi.binary_fill_holes(mask)
        mask = mask & win
    else:
        # halftone puro: a arte inteira e "figura" (so a borda continua limpa)
        mask = win

    iters = max(2, int(art_h * cfg.dilate_frac))
    dilated = ndi.binary_dilation(mask, iterations=iters)
    accent = accent_region(prep, mask, accent_cfg)
    return MaskResult(mask=mask, dilated=dilated, accent=accent)


__all__ = [
    "MaskResult",
    "accent_region",
    "border_window",
    "build",
]
