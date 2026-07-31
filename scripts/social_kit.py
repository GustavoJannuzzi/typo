#!/usr/bin/env python3
"""Base compartilhada das peças de rede social — tokens, fontes e primitivas.

Quem usa: `build_brand_assets.py` (marca) e `build_instagram.py` (carrossel).

A regra que manda aqui: **nenhuma cor e nenhum nome de fonte é escrito neste
arquivo**. Tudo sai de `site/src/styles/base.css` e de `site/src/config.js`, que
já são a fonte da verdade da identidade no site. Se o Gustavo trocar a
terracota lá, o Instagram troca junto — sem ninguém lembrar de sincronizar.

As fontes da identidade estão em `.woff2` (formato de navegador) e o Pillow só
lê `.ttf`/`.otf`. A conversão é feita uma vez e fica em `scripts/.fontcache/`;
é só descompactar o brotli e reescrever a tabela, os contornos são os mesmos
bytes. A Archivo é **variável** (eixos `wght` 100-900 e `wdth` 62-125%), então
os pesos e larguras que o CSS pede (`wght 800, wdth 68%`) saem da mesma
instância que o navegador desenha, e não de uma imitação com a fonte errada.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
BASE_CSS = SITE / "src" / "styles" / "base.css"
CONFIG_JS = SITE / "src" / "config.js"
WOFF_DIR = SITE / "public" / "fonts"
FONT_CACHE = Path(__file__).resolve().parent / ".fontcache"

#: usado só quando `CONFIG.INSTAGRAM` está vazio em site/src/config.js
HANDLE_FALLBACK = "@ondemoramaspalavras"


# --------------------------------------------------------------------------
# tokens — lidos do CSS, nunca duplicados aqui
# --------------------------------------------------------------------------

def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    v = value.strip().lstrip("#")
    if len(v) == 3:
        v = "".join(c * 2 for c in v)
    return (int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16))


@lru_cache(maxsize=1)
def _root_vars() -> dict[str, str]:
    """Todas as `--custom-properties` do bloco `:root` de base.css."""
    css = BASE_CSS.read_text(encoding="utf-8")
    block = re.search(r":root\s*\{(.*?)\n\}", css, re.S)
    if not block:
        raise RuntimeError(f"não achei o bloco :root em {BASE_CSS}")
    out = {}
    for name, value in re.findall(r"--([\w-]+)\s*:\s*([^;]+);", block.group(1)):
        out[name] = value.strip()
    return out


@lru_cache(maxsize=1)
def colors() -> dict[str, tuple[int, int, int]]:
    """Paleta da identidade em RGB. Só os tokens que são cor sólida."""
    raw = _root_vars()
    wanted = ("paper", "ink", "ink-warm", "grey", "footer-grey", "rule",
              "accent", "accent-2")
    missing = [k for k in wanted if k not in raw]
    if missing:
        raise RuntimeError(f"tokens de cor sumiram de base.css: {missing}")
    return {k: _hex_to_rgb(raw[k]) for k in wanted}


@lru_cache(maxsize=1)
def brand() -> dict[str, str]:
    """`CONFIG` de site/src/config.js — nome, site, instagram."""
    js = CONFIG_JS.read_text(encoding="utf-8")
    out = {}
    for key, value in re.findall(r'^\s*([A-Z_]+):\s*"([^"]*)"', js, re.M):
        out[key] = value
    handle = out.get("INSTAGRAM") or HANDLE_FALLBACK
    out["INSTAGRAM"] = handle if handle.startswith("@") else "@" + handle
    out.setdefault("BRAND", "Onde Moram as Palavras")
    return out


def site_label() -> str:
    """Domínio limpo pro rodapé das peças. Vazio se ainda não foi publicado."""
    url = brand().get("SITE_URL", "")
    return re.sub(r"^https?://", "", url).rstrip("/")


# --------------------------------------------------------------------------
# fontes — woff2 -> ttf, uma vez, em cache
# --------------------------------------------------------------------------

def _ensure_ttf(woff2: Path) -> Path:
    ttf = FONT_CACHE / (woff2.stem + ".ttf")
    if ttf.exists() and ttf.stat().st_mtime >= woff2.stat().st_mtime:
        return ttf
    try:
        from fontTools.ttLib import TTFont
    except ImportError as exc:  # pragma: no cover - ambiente sem a lib
        raise RuntimeError(
            "converter as fontes da identidade precisa de fontTools e brotli:\n"
            "    python -m pip install fonttools brotli"
        ) from exc
    FONT_CACHE.mkdir(parents=True, exist_ok=True)
    font = TTFont(woff2)
    font.flavor = None  # tira o envelope woff2; os contornos não mudam
    font.save(ttf)
    axes = [a.axisTag for a in font["fvar"].axes] if "fvar" in font else []
    ttf.with_suffix(".axes.json").write_text(json.dumps(axes), encoding="utf-8")
    font.close()
    return ttf


@lru_cache(maxsize=None)
def _axes_of(ttf: Path) -> list[str]:
    meta = ttf.with_suffix(".axes.json")
    return json.loads(meta.read_text(encoding="utf-8")) if meta.exists() else []


@lru_cache(maxsize=256)
def display(size_px: int, wght: int = 800, wdth: float = 68.0) -> ImageFont.FreeTypeFont:
    """Archivo Variable — o `.display` do site.

    Os defaults são os do CSS (`font-variation-settings: "wght" 800,
    "wdth" var(--wdth-condensed)`), então chamar sem argumento já dá o mesmo
    desenho que o título da landing.
    """
    ttf = _ensure_ttf(WOFF_DIR / "archivo-variable.woff2")
    font = ImageFont.truetype(str(ttf), size_px)
    axes = _axes_of(ttf)
    if axes:
        by_tag = {"wght": float(wght), "wdth": float(wdth)}
        font.set_variation_by_axes([by_tag.get(tag, 400.0) for tag in axes])
    return font


@lru_cache(maxsize=256)
def mono(size_px: int, weight: int = 500) -> ImageFont.FreeTypeFont:
    """JetBrains Mono — o `.label` / `.readout` do site. Pesos 400..700."""
    weight = min((400, 500, 600, 700), key=lambda w: abs(w - weight))
    ttf = _ensure_ttf(WOFF_DIR / f"jetbrains-mono-{weight}.woff2")
    return ImageFont.truetype(str(ttf), size_px)


def condensed_wdth() -> float:
    """O valor de `--wdth-condensed`, em número (o CSS guarda como `68%`)."""
    return float(_root_vars().get("wdth-condensed", "68%").rstrip("%"))


# --------------------------------------------------------------------------
# primitivas de texto
# --------------------------------------------------------------------------

def text_width(text: str, font: ImageFont.FreeTypeFont, tracking: float = 0.0) -> float:
    if not text:
        return 0.0
    if not tracking:
        return font.getlength(text)
    return sum(font.getlength(c) for c in text) + tracking * (len(text) - 1)


def draw_tracked(
    draw: ImageDraw.ImageDraw,
    xy: tuple[float, float],
    text: str,
    font: ImageFont.FreeTypeFont,
    fill,
    tracking: float = 0.0,
    anchor: str = "la",
) -> float:
    """Escreve com entreletra (o `letter-spacing` do CSS) e devolve a largura.

    Com `tracking=0` desenha a string inteira de uma vez — é o caminho que
    preserva o kerning da fonte, e é o certo pros títulos em Archivo. Com
    entreletra o desenho vai caractere a caractere; nas etiquetas em mono isso
    não custa nada, porque monoespaçada não tem kerning pra perder.
    """
    w = text_width(text, font, tracking)
    x, y = xy
    halign, valign = anchor[0], anchor[1]
    if halign == "m":
        x -= w / 2
    elif halign == "r":
        x -= w
    if not tracking:
        draw.text((x, y), text, font=font, fill=fill, anchor="l" + valign)
        return w
    for char in text:
        draw.text((x, y), char, font=font, fill=fill, anchor="l" + valign)
        x += font.getlength(char) + tracking
    return w


def fit_display(text: str, max_w: float, max_size: int, min_size: int = 8, **kw) -> ImageFont.FreeTypeFont:
    """Maior corpo de Archivo em que `text` ainda cabe em `max_w`."""
    lo, hi = min_size, max_size
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if display(mid, **kw).getlength(text) <= max_w:
            lo = mid
        else:
            hi = mid - 1
    return display(lo, **kw)


def wrap(text: str, font: ImageFont.FreeTypeFont, max_w: float, tracking: float = 0.0) -> list[str]:
    lines, current = [], ""
    for word in text.split():
        trial = f"{current} {word}".strip()
        if current and text_width(trial, font, tracking) > max_w:
            lines.append(current)
            current = word
        else:
            current = trial
    if current:
        lines.append(current)
    return lines


def ink_bbox(text: str, font: ImageFont.FreeTypeFont) -> tuple[float, float, float, float]:
    """Caixa da **tinta**, não das métricas da fonte.

    Mesma escolha do `typo/display.py`: em corpo grande o vazio de ascender
    engana qualquer medida de topo. Alinhar caixa alta com caixa alta pede a
    tinta.
    """
    return font.getbbox(text, anchor="ls")


# --------------------------------------------------------------------------
# marcas da identidade
# --------------------------------------------------------------------------

def mark_squares(
    draw: ImageDraw.ImageDraw,
    x: float,
    y: float,
    side: float,
    gap: float | None = None,
    ink=None,
    accent=None,
    anchor: str = "lm",
) -> float:
    """Os quatro quadradinhos do rodapé do pôster (`.mark-squares` no site).

    Quatro em linha, o primeiro na cor de destaque. Devolve a largura total.
    """
    c = colors()
    ink = c["ink"] if ink is None else ink
    accent = c["accent"] if accent is None else accent
    gap = side * 0.645 if gap is None else gap  # 0.4em / 0.62em, como no CSS
    total = side * 4 + gap * 3
    if anchor[0] == "m":
        x -= total / 2
    elif anchor[0] == "r":
        x -= total
    if anchor[1] == "m":
        y -= side / 2
    for i in range(4):
        left = x + i * (side + gap)
        draw.rectangle([left, y, left + side - 1, y + side - 1],
                       fill=accent if i == 0 else ink)
    return total


def eyebrow(
    draw: ImageDraw.ImageDraw,
    x: float,
    y: float,
    text: str,
    font: ImageFont.FreeTypeFont,
    fill=None,
    accent=None,
    tracking: float | None = None,
) -> float:
    """Etiqueta de laboratório com o quadradinho de destaque na frente.

    É o `.eyebrow` do site: `::before` de 0.5em na cor de destaque, folga de
    0.55em, e o texto em mono maiúsculo com 0.14em de entreletra.
    """
    c = colors()
    fill = c["grey"] if fill is None else fill
    accent = c["accent"] if accent is None else accent
    size = font.size
    tracking = size * 0.14 if tracking is None else tracking
    box = size * 0.5
    draw.rectangle([x, y - box / 2, x + box - 1, y + box / 2 - 1], fill=accent)
    start = x + box + size * 0.55
    w = draw_tracked(draw, (start, y), text.upper(), font, fill, tracking, "lm")
    return start + w - x


def hairline(draw: ImageDraw.ImageDraw, box, width: int = 1, fill=None) -> None:
    """A moldura fina com recuo (`.framed::after`)."""
    fill = colors()["rule"] if fill is None else fill
    draw.rectangle(box, outline=fill, width=width)


# --------------------------------------------------------------------------
# canvas
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Format:
    """Um formato de saída do Instagram."""
    name: str
    w: int
    h: int

    @property
    def size(self) -> tuple[int, int]:
        return (self.w, self.h)


FEED = Format("feed", 1080, 1350)      # 4:5 — o maior retrato que o feed aceita
STORY = Format("story", 1080, 1920)    # 9:16
SQUARE = Format("quadrado", 1080, 1080)

#: faixas que a interface do Instagram cobre no story (topo: avatar/nome,
#: base: campo de resposta). Nada essencial pode cair aqui.
STORY_SAFE_TOP = 250
STORY_SAFE_BOTTOM = 320


def canvas(fmt: Format, bg=None) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    bg = colors()["paper"] if bg is None else bg
    img = Image.new("RGB", fmt.size, bg)
    return img, ImageDraw.Draw(img)


def cover(img: Image.Image, w: int, h: int, focus: tuple[float, float] = (0.5, 0.5)) -> Image.Image:
    """`object-fit: cover` — preenche w×h sem distorcer, cortando o excesso."""
    scale = max(w / img.width, h / img.height)
    new = img.resize((max(w, round(img.width * scale)), max(h, round(img.height * scale))),
                     Image.LANCZOS)
    fx, fy = focus
    left = round((new.width - w) * min(max(fx, 0.0), 1.0))
    top = round((new.height - h) * min(max(fy, 0.0), 1.0))
    return new.crop((left, top, left + w, top + h))


def contain(img: Image.Image, w: int, h: int, bg=None) -> Image.Image:
    """`object-fit: contain` — cabe inteira em w×h, sobra vira campo.

    É o que a prova de contato precisa: `cover` numa faixa larga corta o miolo
    e a assinatura aparece sem começo nem fim.
    """
    bg = colors()["paper"] if bg is None else bg
    scale = min(w / img.width, h / img.height)
    small = img.resize((max(1, round(img.width * scale)), max(1, round(img.height * scale))),
                       Image.LANCZOS)
    out = Image.new("RGB", (w, h), bg)
    out.paste(small, ((w - small.width) // 2, (h - small.height) // 2))
    return out


def save(img: Image.Image, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, optimize=True)
    return path
