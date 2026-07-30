"""Blocos de texto da pagina: titulo, subtitulo, quadradinhos, rodape e moldura.

Ultimo bloco do print_v4.py, com as mesmas medidas em mm.
"""
from __future__ import annotations

from PIL import Image, ImageDraw

from typo import fonts
from typo.config import ColorsCfg, Scale, TextBlocksCfg, hex_to_rgb
from typo.fonts import FontPair


def spaced(text: str, n: int = 1) -> str:
    """'ABC' -> 'A B C' (letter-spacing do print_v4.py)."""
    if n <= 0:
        return text
    return (" " * n).join(list(text))


def draw(
    canvas: Image.Image,
    pair: FontPair,
    blocks: TextBlocksCfg,
    colors: ColorsCfg,
    accent_rgb: tuple[int, int, int],
    accent_enabled: bool,
    scale: Scale,
    art_origin_x: int,
    bottom_margin_cm: float,
    chip_colors: list[tuple[int, int, int]] | None = None,
) -> None:
    """Desenha os blocos de texto da pagina.

    Com `blocks.draw=False` nao desenha nada: os textos continuam existindo como
    metadado do projeto (o site le `title`/`subtitle` deles) e a nomeacao da
    obra na pagina fica por conta da camada `display`.

    `chip_colors`, quando dado, substitui os quadradinhos (accent + tinta) por
    uma fileira de amostras — e o que a paleta usa para mostrar as cores de
    tinta da arte no cabecalho. Sem ele, o comportamento e o do print_v4.py:
    primeiro quadradinho no accent, os demais na tinta.
    """
    if not blocks.draw:  # layout `display`: o rotulo invertido faz esse papel
        return
    pw, ph = canvas.size
    d = ImageDraw.Draw(canvas)
    ink = hex_to_rgb(colors.ink)
    subtitle_rgb = hex_to_rgb(colors.subtitle)
    footer_rgb = hex_to_rgb(colors.footer)
    frame_rgb = hex_to_rgb(colors.frame)
    sp = blocks.letter_spacing

    tx = art_origin_x
    ty = int(scale.mm(blocks.title_y_mm))

    if blocks.title:
        d.text(
            (tx, ty),
            blocks.title,
            font=fonts.load(pair.bold, int(scale.mm(blocks.title_size_mm))),
            fill=ink,
        )
    if blocks.subtitle:
        d.text(
            (tx + int(scale.px(blocks.subtitle_dx_px)), ty + int(scale.mm(blocks.subtitle_dy_mm))),
            spaced(blocks.subtitle, sp),
            font=fonts.load(pair.regular, int(scale.mm(blocks.subtitle_size_mm))),
            fill=subtitle_rgb,
        )
    if blocks.accent_squares and blocks.square_count > 0:
        ay = ty + int(scale.mm(blocks.squares_dy_mm))
        s = int(scale.mm(blocks.square_size_mm))
        gap = int(scale.mm(blocks.square_gap_mm))
        if chip_colors:
            count = len(chip_colors)
            fills = list(chip_colors)
        else:
            count = int(blocks.square_count)
            first = accent_rgb if accent_enabled else ink
            fills = [first if i == 0 else ink for i in range(count)]
        for i in range(count):
            d.rectangle([tx + i * gap, ay, tx + i * gap + s, ay + s], fill=fills[i])
    if blocks.footer:
        cap = spaced(blocks.footer, sp)
        ff = fonts.load(pair.regular, int(scale.mm(blocks.footer_size_mm)))
        cb = d.textbbox((0, 0), cap, font=ff)
        d.text(
            (
                (pw - (cb[2] - cb[0])) // 2,
                ph - int(scale.cm(bottom_margin_cm)) + int(scale.mm(blocks.footer_dy_mm)),
            ),
            cap,
            font=ff,
            fill=footer_rgb,
        )
    if blocks.frame:
        ins = int(scale.mm(blocks.frame_inset_mm))
        d.rectangle(
            [ins, ins, pw - ins, ph - ins],
            outline=frame_rgb,
            width=max(1, int(scale.px(2)), int(scale.mm(blocks.frame_width_mm))),
        )


__all__ = ["draw", "spaced"]
