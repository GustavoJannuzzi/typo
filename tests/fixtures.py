"""Referencia sintetica para os testes.

NAO e a foto do magalenha — e um substituto deterministico com as mesmas
caracteristicas que o motor precisa exercitar: fundo claro, uma paisagem de
contorno na faixa alta, tres figuras escuras isoladas e uma regiao vermelha
na figura central (para o accent).
"""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw

WIDTH, HEIGHT = 820, 727


def make_reference_image(path: str | Path) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (WIDTH, HEIGHT), (242, 242, 240))
    d = ImageDraw.Draw(img)

    # ceu com um degrade suave (da textura para o sobel da paisagem)
    for y in range(int(HEIGHT * 0.60)):
        t = y / (HEIGHT * 0.60)
        d.line([(0, y), (WIDTH, y)], fill=(int(226 + 18 * t),) * 3)

    # montanhas: linhas de contorno na faixa 0.06..0.66
    for k, (amp, base, shade) in enumerate(((46, 0.34, 176), (34, 0.44, 192))):
        pts = [
            (x, HEIGHT * base + amp * math.sin(x / (70 + 25 * k) + k))
            for x in range(0, WIDTH + 8, 8)
        ]
        d.line(pts, fill=(shade,) * 3, width=3)

    # tres figuras escuras
    figures = [(120, 300), (400, 250), (660, 320)]
    for cx, top in figures:
        d.ellipse([cx - 42, top, cx + 42, top + 96], fill=(38, 36, 34))  # cabeca
        d.polygon(
            [(cx - 96, HEIGHT - 10), (cx + 96, HEIGHT - 10), (cx + 56, top + 70), (cx - 56, top + 70)],
            fill=(46, 42, 40),
        )

    # vestido vermelho na figura central (regiao de accent)
    cx, top = figures[1]
    d.polygon(
        [(cx - 78, HEIGHT - 20), (cx + 78, HEIGHT - 20), (cx + 44, top + 150), (cx - 44, top + 150)],
        fill=(168, 46, 34),
    )

    img.save(p)
    return p


def make_text_file(path: str | Path) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        "\n".join(
            [
                "Vem, Magalenha Rojão",
                "Traz a lenha pro fogão",
                "Vem fazer armação",
                "Hoje é um dia de Sol",
            ]
        ),
        encoding="utf-8",
    )
    return p


__all__ = ["HEIGHT", "WIDTH", "make_reference_image", "make_text_file"]
