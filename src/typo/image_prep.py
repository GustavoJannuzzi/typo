"""Carga da imagem de referencia: crop, resize e luminancia (+ cache).

Equivale a estas linhas do print_v4.py:

    im = Image.open(SRC).convert("RGB").crop(CROP); cw, ch = im.size
    art_h = int(ART_H_CM/2.54*DPI); art_w = int(art_h*cw/ch)
    src = im.resize((art_w, art_h), Image.LANCZOS); a = np.asarray(src).astype(float)
    lum = (0.299*r + 0.587*g + 0.114*b)/255.0
"""
from __future__ import annotations

from array import array
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image

#: acima disso as tabelas de soma acumulada custam memoria demais e a sondagem
#: volta ao modo direto (numpy slice .mean()). Preview usa SAT, export nao.
SAT_MAX_PX = 8_000_000


class ImagePrepError(RuntimeError):
    pass


class Field:
    """Um mapa 2D sondavel por janelas retangulares.

    Com `use_sat=True` pre-computa a tabela de soma acumulada e a media de uma
    janela vira O(1) — numericamente igual a `arr[y0:y1, x0:x1].mean()`.

    A tabela fica num `array.array('d')` plano em vez de um ndarray: indexar
    um ndarray 2D devolve um `np.float64` (alocacao a cada acesso), enquanto o
    array plano devolve `float` nativo. No loop de tipografia isso e a
    diferenca entre ~5us e ~1us por sonda.
    """

    __slots__ = ("arr", "_sat", "_stride")

    def __init__(self, arr: np.ndarray, use_sat: bool = False) -> None:
        self.arr = arr
        self._sat: array | None = None
        self._stride = arr.shape[1] + 1
        if use_sat:
            acc = np.zeros((arr.shape[0] + 1, arr.shape[1] + 1), dtype=np.float64)
            np.cumsum(
                np.cumsum(arr.astype(np.float64, copy=False), axis=0), axis=1,
                out=acc[1:, 1:],
            )
            flat = array("d")
            flat.frombytes(np.ascontiguousarray(acc).tobytes())
            self._sat = flat

    def mean(self, y0: int, y1: int, x0: int, x1: int) -> float:
        sat = self._sat
        if sat is None:
            return float(self.arr[y0:y1, x0:x1].mean())
        s = self._stride
        a = y1 * s
        b = y0 * s
        return (sat[a + x1] - sat[b + x1] - sat[a + x0] + sat[b + x0]) / (
            (y1 - y0) * (x1 - x0)
        )


@dataclass(frozen=True)
class PreparedImage:
    """Imagem ja recortada e redimensionada para o tamanho da arte."""

    art_w: int
    art_h: int
    dpi: float
    rgb: np.ndarray  # (h, w, 3) float 0..255
    lum: np.ndarray  # (h, w) float 0..1

    @property
    def r(self) -> np.ndarray:
        return self.rgb[:, :, 0]

    @property
    def g(self) -> np.ndarray:
        return self.rgb[:, :, 1]

    @property
    def b(self) -> np.ndarray:
        return self.rgb[:, :, 2]

    @property
    def use_sat(self) -> bool:
        return self.art_w * self.art_h <= SAT_MAX_PX


def open_source(image_path: str, crop: tuple[int, int, int, int] | None) -> Image.Image:
    """Abre a imagem em RGB e aplica o crop (validando os limites)."""
    p = Path(image_path)
    if not p.is_file():
        raise ImagePrepError(
            f"imagem de referencia nao encontrada: {p}\n"
            "Coloque o arquivo em projects/<nome>/refs/ e aponte source.image "
            "no project.yaml."
        )
    img = Image.open(p).convert("RGB")
    if crop is None:
        return img
    left, top, right, bottom = (int(v) for v in crop)
    w, h = img.size
    if right > w or bottom > h or left < 0 or top < 0:
        raise ImagePrepError(
            f"crop {crop} fora da imagem {w}x{h} ({p.name}). "
            "Ajuste source.crop no project.yaml (use 'Ver crop' na UI)."
        )
    return img.crop((left, top, right, bottom))


def crop_size(image_path: str, crop: tuple[int, int, int, int] | None) -> tuple[int, int]:
    """Tamanho do crop sem manter a imagem inteira em memoria."""
    return _crop_size_cached(image_path, _mtime(image_path), _crop_key(crop))


def prepare(
    image_path: str,
    crop: tuple[int, int, int, int] | None,
    art_w: int,
    art_h: int,
    dpi: float,
) -> PreparedImage:
    """Versao memoizada por (arquivo, mtime, crop, tamanho da arte)."""
    return _prepare_cached(image_path, _mtime(image_path), _crop_key(crop), art_w, art_h, dpi)


# --------------------------------------------------------------------------- #
# cache
# --------------------------------------------------------------------------- #
def _mtime(path: str) -> float:
    p = Path(path)
    return p.stat().st_mtime if p.is_file() else 0.0


def _crop_key(crop) -> tuple | None:
    return tuple(int(v) for v in crop) if crop is not None else None


@lru_cache(maxsize=8)
def _crop_size_cached(image_path: str, mtime: float, crop) -> tuple[int, int]:
    with open_source(image_path, crop) as img:
        return img.size


@lru_cache(maxsize=4)
def _prepare_cached(
    image_path: str, mtime: float, crop, art_w: int, art_h: int, dpi: float
) -> PreparedImage:
    img = open_source(image_path, crop)
    src = img.resize((art_w, art_h), Image.LANCZOS)
    arr = np.asarray(src).astype(float)
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255.0
    return PreparedImage(art_w=art_w, art_h=art_h, dpi=dpi, rgb=arr, lum=lum)


def clear_cache() -> None:
    _prepare_cached.cache_clear()
    _crop_size_cached.cache_clear()


__all__ = [
    "Field",
    "ImagePrepError",
    "PreparedImage",
    "SAT_MAX_PX",
    "clear_cache",
    "crop_size",
    "open_source",
    "prepare",
]
