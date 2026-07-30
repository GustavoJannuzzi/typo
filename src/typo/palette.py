"""Cor por glifo: mapa de tinta quantizado a partir da imagem fonte.

Complementa o `accent` (uma cor, regra booleana) com o caso geral: uma tabela
de `stops` `(cor_na_fonte -> cor_da_tinta)`. Cada pixel da fonte e atribuido ao
stop mais proximo, e o resultado e um mapa de indices `uint8` do tamanho da
arte. Na passada de tipografia a cor do glifo sai de *uma* consulta ao mapa, no
centro da sonda — nao ha media, nao ha tabela de soma acumulada, e o custo por
glifo e o de indexar um array plano.

Amostrar o centro (e nao a media da janela) e proposital: a media entre dois
blocos de cor vizinhos daria uma terceira cor que nao existe na arte. Com o
centro, cada glifo herda a cor de onde ele efetivamente cai, e a fronteira
entre dois blocos fica nitida — que e o que se quer em arte de cor chapada.

## O espaco de comparacao

O casamento *nao* e euclidiano em RGB, e por um motivo concreto. Em RGB puro,
um pixel de anti-aliasing na borda entre o traco preto e o papel creme
(~120,116,100 no cartaz do turnstile) fica a distancia 65 do verde-oliva
(132,178,85) e a 193 do preto e do creme: a borda inteira do desenho sortearia
glifos verdes. Nenhum stop neutro intermediario resolve isso, porque o
verde-oliva e genuinamente mais perto do cinza-medio do que os extremos da
rampa sao.

A saida e comparar num espaco onde os eixos de *cor* pesam mais que o de
*brilho*:

    (R - G,  G - B,  value_weight * (R + G + B) / 3)

Com `value_weight` 0.25, o mesmo pixel de borda fica a 32 do preto e a 92 do
verde — resolve como neutro, que e o certo. Cores de verdade continuam batendo
exato (a distancia ao proprio stop e zero), e hues vizinhos seguem separados:
no cartaz, ceu (#ACD9FF) e ciano (#66B7CA) ficam a 46 um do outro. Nao ha
limiar de saturacao nem regra escondida — so a metrica e a tabela.
"""
from __future__ import annotations

from array import array

import numpy as np
from scipy.ndimage import gaussian_filter

from typo.config import PaletteCfg, hex_to_rgb
from typo.image_prep import PreparedImage

#: acima disto o bloco de distancias custa memoria demais; ver `build`
_BLOCK_FLOATS = 4_000_000


class PaletteMap:
    """Mapa (h, w) de indices de tinta + a lista de cores correspondente.

    O mapa fica num `array.array('B')` plano pelo mesmo motivo que a `Field`
    guarda a soma acumulada num `array('d')`: indexar um ndarray devolve um
    `np.uint8` (alocacao por acesso), o array plano devolve `int` nativo.
    """

    __slots__ = ("colors", "_idx", "_w")

    def __init__(self, idx: np.ndarray, colors: list[tuple[int, int, int]]) -> None:
        if idx.ndim != 2:
            raise ValueError(f"mapa de paleta precisa ser 2D, recebi {idx.shape}")
        if not colors:
            raise ValueError("mapa de paleta sem cores")
        if len(colors) > 256:
            raise ValueError(f"maximo 256 stops de paleta, recebi {len(colors)}")
        self.colors = colors
        self._w = int(idx.shape[1])
        flat = array("B")
        flat.frombytes(np.ascontiguousarray(idx, dtype=np.uint8).tobytes())
        self._idx = flat

    def at(self, y: int, x: int) -> tuple[int, int, int]:
        return self.colors[self._idx[y * self._w + x]]

    def index_map(self) -> np.ndarray:
        """Mapa de indices como ndarray (para overlays de diagnostico)."""
        return np.frombuffer(self._idx, dtype=np.uint8).reshape(-1, self._w)


def features(rgb: np.ndarray, value_weight: float) -> np.ndarray:
    """RGB -> espaco de comparacao (ver docstring do modulo).

    Aceita (..., 3) e devolve (..., 3): dois eixos oponentes de cor mais um
    eixo de brilho atenuado por `value_weight`.
    """
    r = rgb[..., 0]
    g = rgb[..., 1]
    b = rgb[..., 2]
    return np.stack(
        [r - g, g - b, value_weight * (r + g + b) / 3.0], axis=-1
    )


def build(prep: PreparedImage, cfg: PaletteCfg) -> PaletteMap | None:
    """Constroi o mapa de tinta, ou None se a paleta estiver desligada."""
    if not cfg.enabled or not cfg.stops:
        return None

    inks = [hex_to_rgb(stop[1]) for stop in cfg.stops]
    stops = features(
        np.array([hex_to_rgb(stop[0]) for stop in cfg.stops], dtype=np.float64),
        cfg.value_weight,
    )  # (n, 3)

    rgb = prep.rgb
    if cfg.blur_sigma > 0:
        # borra so os eixos espaciais; sigma 0 no eixo de cor
        rgb = gaussian_filter(rgb, (cfg.blur_sigma, cfg.blur_sigma, 0))

    # em blocos de linhas para nao alocar um (h, w, n) inteiro de uma vez —
    # a 44 MP com 11 stops isso seria ~4 GB
    h, w = prep.art_h, prep.art_w
    idx = np.empty((h, w), dtype=np.uint8)
    rows = max(1, int(_BLOCK_FLOATS / max(w * len(inks), 1)))
    for y0 in range(0, h, rows):
        y1 = min(h, y0 + rows)
        feat = features(rgb[y0:y1], cfg.value_weight).reshape(-1, 1, 3)
        d2 = ((feat - stops[None, :, :]) ** 2).sum(axis=2)  # (m, n)
        idx[y0:y1] = d2.argmin(axis=1).reshape(y1 - y0, w).astype(np.uint8)

    return PaletteMap(idx, inks)


__all__ = ["PaletteMap", "build", "features"]
