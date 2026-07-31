#!/usr/bin/env python3
"""Gera a identidade da marca pro Instagram — avatar, lockups e destaques.

    python scripts/build_brand_assets.py

Escreve em `social/marca/`. Nenhuma cor e nenhuma fonte é inventada aqui: tudo
vem de `site/src/styles/base.css` via `social_kit`, então a conta do Instagram
sai do mesmo desenho que a landing.

## O teste que manda no avatar

O Instagram mostra a foto de perfil **em círculo, com 110 px de lado** no feed.
Isso elimina de saída qualquer marca que dependa de ler texto: a assinatura
"Onde Moram as Palavras" tem 22 caracteres e, com 110 px, cada letra fica com
menos de 4 px. Por isso as variantes de avatar são todas **uma forma só**, e
todas são conferidas na chapa de contato no tamanho real, ao lado da versão
grande — é a única maneira de julgar honestamente.

Duas famílias, que respondem a duas perguntas diferentes:

- **marca** — os quatro quadradinhos, na geometria 2×2 do `favicon.svg` (o
  `.mark-squares` do site é a mesma marca deitada em linha, que é o que cabe
  num cabeçalho). É o sinal que já existe impresso no rodapé de todo pôster.
  Continuidade pronta: quem viu a peça reconhece a conta.
- **letra** — um "O" gigante sangrando pela borda, que é literalmente o gesto
  do layout `display` do motor (`typo/display.py`: glifo em corpo de dezenas
  de centímetros, cortado pela margem). Diz "isto aqui é sobre tipografia"
  sem precisar de nenhuma palavra.

A terceira variante, `letra-tipografada`, preenche esse mesmo "O" com um macro
de obra de verdade. É a marca que *conta o conceito* — e é honesta sobre o
custo: com 110 px a textura vira cinza. Fica marcada como **uso grande**
(capa, banner, camiseta), não como foto de perfil.
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))

import social_kit as kit  # noqa: E402

ROOT = kit.ROOT
OUT = ROOT / "social" / "marca"

#: obra usada para preencher a variante tipografada. Qualquer slug com
#: `-detail.webp` em site/public/art serve.
TEXTURE_SLUG = "ouro-marrom"

#: lado do avatar exportado. O Instagram pede 320; sai maior porque o mesmo
#: arquivo serve de foto de perfil no WhatsApp Business e no e-mail.
AVATAR_PX = 1080

#: o que o Instagram realmente mostra no feed
AVATAR_REAL_PX = 110

#: fração do lado onde a arte pode viver sem o círculo comer nada.
#: O círculo do avatar é inscrito no quadrado, então o canto do quadrado está
#: a 1,41 raio do centro — qualquer coisa nele some.
SAFE = 0.90


# --------------------------------------------------------------------------
# ferramentas de glifo
# --------------------------------------------------------------------------

def glyph_mask(char: str, size_px: int, **font_kw) -> Image.Image:
    """Máscara `L` de um glifo, recortada na **tinta**.

    Mesma escolha do `typo/display.py`: em corpo grande o vazio de ascender
    passa de um terço da altura, e posicionar pelas métricas da fonte deixa
    tudo visualmente torto. Aqui o recorte sai do bitmap, então é exato.
    """
    font = kit.display(size_px, **font_kw)
    pad = size_px
    plate = Image.new("L", (size_px * 3 + pad, size_px * 3 + pad), 0)
    ImageDraw.Draw(plate).text((pad, pad), char, font=font, fill=255)
    box = plate.getbbox()
    if box is None:
        raise ValueError(f"glifo {char!r} não desenhou nada")
    return plate.crop(box)


def paste_mask(base: Image.Image, mask: Image.Image, box: tuple[int, int, int, int], fill) -> None:
    """Pinta `fill` através de `mask`, esticada pra caixa (pode sangrar fora)."""
    x0, y0, x1, y1 = box
    scaled = mask.resize((max(1, x1 - x0), max(1, y1 - y0)), Image.LANCZOS)
    layer = Image.new("RGB", scaled.size, fill)
    base.paste(layer, (x0, y0), scaled)


def paste_texture(base: Image.Image, mask: Image.Image, box: tuple[int, int, int, int],
                  texture: Image.Image) -> None:
    x0, y0, x1, y1 = box
    w, h = max(1, x1 - x0), max(1, y1 - y0)
    scaled = mask.resize((w, h), Image.LANCZOS)
    base.paste(kit.cover(texture, w, h), (x0, y0), scaled)


# --------------------------------------------------------------------------
# avatares
# --------------------------------------------------------------------------

def avatar_marca(px: int = AVATAR_PX, invert: bool = False) -> Image.Image:
    """Os quatro quadradinhos em 2×2 — a geometria do `favicon.svg`.

    O bloco 2×2 é dimensionado pela **diagonal**, não pelo lado: são os cantos
    dos quadrados externos que encostam no círculo primeiro.
    """
    c = kit.colors()
    field = c["ink"] if invert else c["paper"]
    solid = c["paper"] if invert else c["ink"]
    img = Image.new("RGB", (px, px), field)
    draw = ImageDraw.Draw(img)

    block = int(px * SAFE / (2 ** 0.5))        # cabe inteiro dentro do círculo
    gap = round(block * 4 / 48)                # 4/48 do favicon
    side = (block - gap) // 2
    left = (px - block) // 2
    top = (px - block) // 2
    for row in range(2):
        for col in range(2):
            x = left + col * (side + gap)
            y = top + row * (side + gap)
            first = row == 0 and col == 0
            draw.rectangle([x, y, x + side - 1, y + side - 1],
                           fill=c["accent"] if first else solid)
    return img


def _letra_box(px: int, mask: Image.Image) -> tuple[int, int, int, int]:
    """Caixa do "O" — larga, alta, e **inteira dentro do círculo**.

    A primeira versão esticava o glifo até sangrar pela borda, imitando o
    layout `display` do pôster. Não sobrevive: o avatar já é recortado em
    círculo, e um "O" cortado em cima e embaixo vira dois parênteses. O corte
    da margem é um gesto de página retangular — no círculo, quem corta é o
    círculo.
    """
    w = round(px * 0.72)
    h = round(px * 0.84)
    return ((px - w) // 2, (px - h) // 2, (px - w) // 2 + w, (px - h) // 2 + h)


def _selo_accent(img: Image.Image, px: int) -> None:
    """O quadradinho de destaque no vazio da letra — o único lugar onde ele
    não disputa espaço com o desenho."""
    side = round(px * 0.118)
    cx, cy = px // 2, px // 2
    ImageDraw.Draw(img).rectangle(
        [cx - side // 2, cy - side // 2, cx + side // 2, cy + side // 2],
        fill=kit.colors()["accent"],
    )


def avatar_letra(px: int = AVATAR_PX, invert: bool = False, char: str = "O") -> Image.Image:
    """Um "O" em corpo de selo, com o quadradinho de destaque no vazio."""
    c = kit.colors()
    field = c["ink"] if invert else c["paper"]
    solid = c["paper"] if invert else c["ink"]
    img = Image.new("RGB", (px, px), field)
    mask = glyph_mask(char, 400, wght=800, wdth=100.0)
    paste_mask(img, mask, _letra_box(px, mask), solid)
    _selo_accent(img, px)
    return img


def avatar_marca_tipografada(px: int = AVATAR_PX) -> Image.Image:
    """A grade 2×2, com os três quadrados de tinta preenchidos por obra real.

    É a variante que **degrada bem**, que é o problema de todas as outras
    ideias de "marca feita de texto": com 110 px a textura vira cinza. Aqui
    isso não quebra nada — os três quadrados viram cinza *juntos*, então o
    sinal continua sendo a grade 2×2 com um quadrado em terracota. De perto,
    numa capa ou numa camiseta, aparece que o cinza é texto.
    """
    c = kit.colors()
    src = ROOT / "site" / "public" / "art" / f"{TEXTURE_SLUG}-detail.webp"
    if not src.exists():
        raise FileNotFoundError(
            f"a variante tipografada precisa de {src.relative_to(ROOT)}.\n"
            "Rode `python scripts/build_site_assets.py` antes."
        )
    with Image.open(src) as raw:
        texture = raw.convert("RGB")

    img = Image.new("RGB", (px, px), c["paper"])
    draw = ImageDraw.Draw(img)
    block = int(px * SAFE / (2 ** 0.5))
    gap = round(block * 4 / 48)
    side = (block - gap) // 2
    left = top = (px - block) // 2
    for row in range(2):
        for col in range(2):
            x, y = left + col * (side + gap), top + row * (side + gap)
            if row == 0 and col == 0:
                draw.rectangle([x, y, x + side - 1, y + side - 1], fill=c["accent"])
            else:
                # cada quadrado puxa um pedaço diferente do macro, senão os
                # três repetem o mesmo trecho e a marca fica com cara de erro
                fx, fy = (0.5, 0.15) if row == 0 else (0.15 + 0.7 * col, 0.85)
                img.paste(kit.cover(texture, side, side, focus=(fx, fy)), (x, y))
    return img


def avatar_letra_tipografada(px: int = AVATAR_PX, char: str = "O") -> Image.Image:
    """O mesmo "O", preenchido com o macro de uma obra de verdade.

    A marca que explica o produto: de longe é uma letra, de perto é feita de
    texto. Levanta `FileNotFoundError` se o recorte da obra não existir — não
    tem versão de mentira que finge ser textura.
    """
    c = kit.colors()
    src = ROOT / "site" / "public" / "art" / f"{TEXTURE_SLUG}-detail.webp"
    if not src.exists():
        raise FileNotFoundError(
            f"a variante tipografada precisa de {src.relative_to(ROOT)}.\n"
            "Rode `python scripts/build_site_assets.py` antes."
        )
    img = Image.new("RGB", (px, px), c["paper"])
    with Image.open(src) as raw:
        texture = raw.convert("RGB")

    mask = glyph_mask(char, 400, wght=800, wdth=100.0)
    paste_texture(img, mask, _letra_box(px, mask), texture)
    _selo_accent(img, px)
    return img


# --------------------------------------------------------------------------
# lockups
# --------------------------------------------------------------------------

def lockup_horizontal(w: int = 2000, invert: bool = False) -> Image.Image:
    """Marca deitada — cabeçalho, banner, assinatura de e-mail.

    Aqui os quadradinhos voltam pra linha (o `.mark-squares` do site), porque
    em faixa larga a linha acompanha a leitura e o bloco 2×2 empilha altura à
    toa.
    """
    c = kit.colors()
    field = c["ink"] if invert else c["paper"]
    solid = c["paper"] if invert else c["ink"]
    grey = c["rule"] if invert else c["grey"]

    name = kit.brand()["BRAND"].upper()
    pad = round(w * 0.06)
    inner = w - pad * 2
    font = kit.fit_display(name, inner, max_size=round(w * 0.14))
    bbox = font.getbbox(name, anchor="ls")
    cap = -bbox[1]

    sq = round(cap * 0.42)
    kicker = kit.mono(max(10, round(cap * 0.26)), 500)
    gap_a = round(cap * 0.55)
    gap_b = round(cap * 0.42)
    h = pad * 2 + sq + gap_a + cap + gap_b + kicker.size

    img = Image.new("RGB", (w, h), field)
    draw = ImageDraw.Draw(img)
    kit.mark_squares(draw, pad, pad, sq, ink=solid, anchor="lt")
    y = pad + sq + gap_a + cap
    kit.draw_tracked(draw, (pad, y), name, font, solid, anchor="ls")
    kit.draw_tracked(draw, (pad, y + gap_b), "LABORATÓRIO TIPOGRÁFICO",
                     kicker, grey, tracking=kicker.size * 0.14, anchor="la")
    return img


def lockup_empilhado(px: int = 1400, invert: bool = False) -> Image.Image:
    """Marca empilhada — quadrado, pra quando não há faixa larga."""
    c = kit.colors()
    field = c["ink"] if invert else c["paper"]
    solid = c["paper"] if invert else c["ink"]
    grey = c["rule"] if invert else c["grey"]

    img = Image.new("RGB", (px, px), field)
    draw = ImageDraw.Draw(img)
    pad = round(px * 0.12)
    inner = px - pad * 2

    words = ["ONDE", "MORAM", "AS", "PALAVRAS"]
    font = kit.fit_display(max(words, key=len), inner, max_size=round(px * 0.30))
    line = round(font.size * 0.92)                    # o line-height do `.display`
    total = line * len(words)

    sq = round(font.size * 0.16)
    top = (px - total - sq * 3) // 2
    kit.mark_squares(draw, px // 2, top, sq, ink=solid, anchor="mt")
    y = top + sq * 3
    for i, word in enumerate(words):
        kit.draw_tracked(draw, (px // 2, y + i * line + line * 0.82), word,
                         font, solid, anchor="ms")
    kicker = kit.mono(max(10, round(px * 0.022)), 500)
    kit.draw_tracked(draw, (px // 2, y + total + round(px * 0.05)),
                     "LABORATÓRIO TIPOGRÁFICO", kicker, grey,
                     tracking=kicker.size * 0.14, anchor="ma")
    return img


# --------------------------------------------------------------------------
# capas de destaque
# --------------------------------------------------------------------------

#: (nome do destaque, letra da capa). O Instagram já escreve o nome embaixo da
#: bolinha, então a capa carrega a letra — repetir a palavra dentro do círculo
#: só faz o texto encolher até sumir.
DESTAQUES = [
    ("colecao", "C"),
    ("processo", "P"),
    ("encomenda", "E"),
    ("sobre", "S"),
    ("precos", "$"),
]


def capa_destaque(char: str, variant: int, px: int = 1080) -> Image.Image:
    """Capa de destaque: um campo chapado e uma letra condensada no meio.

    Os campos alternam entre papel, tinta e terracota, então a fileira de
    destaques no perfil ganha ritmo em vez de virar cinco bolinhas iguais.
    """
    c = kit.colors()
    fields = [(c["paper"], c["ink"]), (c["ink"], c["paper"]), (c["accent"], c["paper"])]
    field, solid = fields[variant % len(fields)]
    img = Image.new("RGB", (px, px), field)
    mask = glyph_mask(char, 400, wght=800, wdth=kit.condensed_wdth())
    h = round(px * 0.42)
    w = round(h * mask.width / mask.height)
    box = ((px - w) // 2, (px - h) // 2, (px - w) // 2 + w, (px - h) // 2 + h)
    paste_mask(img, mask, box, solid)
    return img


# --------------------------------------------------------------------------
# chapa de contato
# --------------------------------------------------------------------------

def circle(img: Image.Image, px: int) -> Image.Image:
    """Recorta em círculo como o Instagram faz, sobre papel."""
    small = img.resize((px, px), Image.LANCZOS)
    mask = Image.new("L", (px * 4, px * 4), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, px * 4 - 1, px * 4 - 1], fill=255)
    out = Image.new("RGB", (px, px), kit.colors()["paper"])
    out.paste(small, (0, 0), mask.resize((px, px), Image.LANCZOS))
    return out


def chapa_avatares(variants: list[tuple[str, Image.Image, str]]) -> Image.Image:
    """Prova de contato: cada avatar grande, em círculo, e no tamanho real.

    A coluna de 110 px é o ponto da chapa. É o tamanho em que a marca vai ser
    vista de verdade no feed, e é onde as ideias bonitas morrem.
    """
    c = kit.colors()
    pad, big, gap = 70, 300, 46
    row_h = big + 96
    w = 1500
    h = pad * 2 + 150 + row_h * len(variants)
    img = Image.new("RGB", (w, h), c["paper"])
    draw = ImageDraw.Draw(img)

    kit.eyebrow(draw, pad, pad + 16, "avatar · prova de contato", kit.mono(21, 500))
    kit.draw_tracked(draw, (pad, pad + 92), "COMO O INSTAGRAM MOSTRA",
                     kit.display(46), c["ink"], anchor="la")

    head_y = pad + 150
    for label, x in (("arquivo", pad), ("círculo", pad + big + gap),
                     ("110 px real", pad + (big + gap) * 2)):
        kit.draw_tracked(draw, (x, head_y), label.upper(), kit.mono(17, 500),
                         c["grey"], tracking=17 * 0.14, anchor="la")

    y = head_y + 40
    for name, avatar, note in variants:
        img.paste(avatar.resize((big, big), Image.LANCZOS), (pad, y))
        draw.rectangle([pad, y, pad + big - 1, y + big - 1], outline=c["rule"])
        img.paste(circle(avatar, big), (pad + big + gap, y))
        real = circle(avatar, AVATAR_REAL_PX)
        img.paste(real, (pad + (big + gap) * 2, y + (big - AVATAR_REAL_PX) // 2))

        tx = pad + (big + gap) * 2 + AVATAR_REAL_PX + 60
        kit.draw_tracked(draw, (tx, y + big / 2 - 26), name.upper(),
                         kit.display(34, wdth=80), c["ink"], anchor="ls")
        for i, line in enumerate(kit.wrap(note, kit.mono(18, 400), w - tx - pad)):
            kit.draw_tracked(draw, (tx, y + big / 2 - 6 + i * 26), line,
                             kit.mono(18, 400), c["footer-grey"], anchor="la")
        y += row_h
    return img


def chapa_grade(title: str, items: list[tuple[str, Image.Image]], cols: int = 3,
                cell: int = 380) -> Image.Image:
    c = kit.colors()
    pad, gap = 70, 40
    rows = (len(items) + cols - 1) // cols
    w = pad * 2 + cell * cols + gap * (cols - 1)
    h = pad * 2 + 150 + rows * (cell + 60)
    img = Image.new("RGB", (w, h), c["paper"])
    draw = ImageDraw.Draw(img)
    kit.eyebrow(draw, pad, pad + 16, "identidade · instagram", kit.mono(21, 500))
    kit.draw_tracked(draw, (pad, pad + 92), title.upper(), kit.display(46),
                     c["ink"], anchor="la")
    for i, (label, art) in enumerate(items):
        x = pad + (i % cols) * (cell + gap)
        y = pad + 150 + (i // cols) * (cell + 60)
        img.paste(kit.contain(art, cell, cell), (x, y))
        draw.rectangle([x, y, x + cell - 1, y + cell - 1], outline=c["rule"])
        kit.draw_tracked(draw, (x, y + cell + 26), label.upper(), kit.mono(17, 500),
                         c["grey"], tracking=17 * 0.14, anchor="la")
    return img


# --------------------------------------------------------------------------

def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    c = kit.colors()
    written: list[Path] = []

    def emit(img: Image.Image, name: str) -> Path:
        path = kit.save(img, OUT / name)
        written.append(path)
        return path

    # --- avatares -------------------------------------------------------
    variants: list[tuple[str, Image.Image, str]] = []
    marca = avatar_marca()
    marca_inv = avatar_marca(invert=True)
    letra = avatar_letra()
    letra_inv = avatar_letra(invert=True)
    emit(marca, "avatar-marca.png")
    emit(marca_inv, "avatar-marca-invertido.png")
    emit(letra, "avatar-letra.png")
    emit(letra_inv, "avatar-letra-invertido.png")
    variants += [
        ("marca", marca,
         "Os quatro quadradinhos do rodapé do pôster, na grade 2×2 do favicon. "
         "Quem tem a peça na parede reconhece a conta."),
        ("marca invertida", marca_inv,
         "Mesma marca em campo de tinta. Segura melhor contra fundo claro na "
         "lista de stories."),
        ("letra", letra,
         "Um O em corpo de selo, com o quadradinho de destaque no vazio. Diz "
         "tipografia sem escrever uma palavra."),
        ("letra invertida", letra_inv,
         "A mesma, em campo de tinta. Vira um alvo — é a que mais chama a "
         "atenção numa lista de stories."),
    ]
    try:
        marca_tipo = avatar_marca_tipografada()
        letra_tipo = avatar_letra_tipografada()
    except FileNotFoundError as exc:
        print(f"  ! pulando as variantes tipografadas: {exc}")
    else:
        emit(marca_tipo, "avatar-marca-tipografada.png")
        emit(letra_tipo, "avatar-letra-tipografada.png")
        variants += [
            ("marca tipografada", marca_tipo,
             "Os três quadrados de tinta preenchidos com macro de obra real. "
             "É a única que degrada bem: com 110 px os três viram cinza JUNTOS, "
             "então continua lendo como a grade 2×2."),
            ("letra tipografada", letra_tipo,
             "A marca que conta o conceito: de longe uma letra, de perto texto "
             "de verdade (macro de ouro-marrom). USO GRANDE — com 110 px a "
             "textura vira cinza chapado."),
        ]

    emit(chapa_avatares(variants), "chapa-avatares.png")

    # --- lockups --------------------------------------------------------
    lock_h = lockup_horizontal()
    lock_hi = lockup_horizontal(invert=True)
    lock_v = lockup_empilhado()
    lock_vi = lockup_empilhado(invert=True)
    emit(lock_h, "lockup-horizontal.png")
    emit(lock_hi, "lockup-horizontal-invertido.png")
    emit(lock_v, "lockup-empilhado.png")
    emit(lock_vi, "lockup-empilhado-invertido.png")
    emit(chapa_grade("Assinaturas da marca",
                     [("horizontal", lock_h), ("horizontal invertido", lock_hi),
                      ("empilhado", lock_v), ("empilhado invertido", lock_vi)],
                     cols=2, cell=560),
         "chapa-lockups.png")

    # --- destaques ------------------------------------------------------
    capas = []
    for i, (name, char) in enumerate(DESTAQUES):
        art = capa_destaque(char, i)
        emit(art, f"destaque-{name}.png")
        capas.append((name, art))
    emit(chapa_grade("Capas de destaque", capas, cols=5, cell=280),
         "chapa-destaques.png")

    # --- paleta ---------------------------------------------------------
    emit(chapa_paleta(), "chapa-paleta.png")

    print(f"\n{len(written)} arquivos -> {OUT.relative_to(ROOT)}")
    for path in written:
        print(f"  ok {path.name}")
    if not kit.brand().get("INSTAGRAM"):
        print("\n  ! CONFIG.INSTAGRAM está vazio em site/src/config.js")
    return 0


def chapa_paleta(w: int = 1500) -> Image.Image:
    """A paleta e a escala tipográfica, do jeito que estão no base.css."""
    c = kit.colors()
    img = Image.new("RGB", (w, 900), c["paper"])
    draw = ImageDraw.Draw(img)
    pad = 70
    kit.eyebrow(draw, pad, pad + 16, "tokens · site/src/styles/base.css", kit.mono(21, 500))
    kit.draw_tracked(draw, (pad, pad + 92), "PALETA E TIPOGRAFIA", kit.display(46),
                     c["ink"], anchor="la")

    order = ["paper", "ink", "ink-warm", "grey", "footer-grey", "rule", "accent", "accent-2"]
    sw, gap = 160, 20
    y = pad + 160
    for i, key in enumerate(order):
        x = pad + i * (sw + gap)
        draw.rectangle([x, y, x + sw - 1, y + sw - 1], fill=c[key],
                       outline=c["rule"] if key == "paper" else None)
        kit.draw_tracked(draw, (x, y + sw + 22), f"--{key}", kit.mono(16, 500),
                         c["ink"], tracking=1.2, anchor="la")
        kit.draw_tracked(draw, (x, y + sw + 46), "#%02X%02X%02X" % c[key],
                         kit.mono(16, 400), c["grey"], anchor="la")

    y += sw + 110
    kit.draw_tracked(draw, (pad, y), "DISPLAY — ARCHIVO 800 / WDTH 68%",
                     kit.mono(17, 500), c["grey"], tracking=17 * 0.14, anchor="la")
    kit.draw_tracked(draw, (pad, y + 110), "ONDE MORAM AS PALAVRAS", kit.display(84),
                     c["ink"], anchor="ls")
    y += 160
    kit.draw_tracked(draw, (pad, y), "LABEL — JETBRAINS MONO 500 / 0.14em",
                     kit.mono(17, 500), c["grey"], tracking=17 * 0.14, anchor="la")
    kit.draw_tracked(draw, (pad, y + 44), "ESPÉCIME 01 · 113 × 111 CM · 35.880 GLIFOS",
                     kit.mono(24, 500), c["footer-grey"], tracking=24 * 0.14, anchor="la")
    y += 110
    kit.mark_squares(draw, pad, y, 26)
    kit.draw_tracked(draw, (pad + 170, y + 13), kit.brand()["INSTAGRAM"],
                     kit.mono(24, 500), c["ink"], tracking=1.5, anchor="lm")
    return img


if __name__ == "__main__":
    raise SystemExit(main())
