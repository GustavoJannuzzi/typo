"""Descoberta e carga de fontes + cache de glifos rotacionados.

Substitui os caminhos hardcoded do print_v4.py:

    FB = ".../DejaVuSansCondensed-Bold.ttf"
    FR = ".../DejaVuSansCondensed.ttf"

por uma resolucao `family -> (regular, bold)` que varre `fonts/` (empacotado),
os diretorios do SO e cai no fallback DejaVu Sans que acompanha o projeto.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

PACKAGE_ROOT = Path(__file__).resolve().parents[2]
BUNDLED_FONTS_DIR = PACKAGE_ROOT / "fonts"

#: usado quando a familia pedida nao existe na maquina
FALLBACK_CHAIN = ("DejaVu Sans Condensed", "DejaVu Sans")

_FONT_SUFFIXES = (".ttf", ".otf", ".ttc")
_ITALIC_TOKENS = ("italic", "oblique")
_BOLD_TOKENS = ("bold", "black", "heavy")
_REGULAR_TOKENS = ("regular", "book", "roman", "normal", "")


class FontResolutionError(RuntimeError):
    pass


@dataclass(frozen=True)
class FontPair:
    family: str
    regular: str
    bold: str

    @property
    def synthetic_bold(self) -> bool:
        return self.regular == self.bold


# --------------------------------------------------------------------------- #
# varredura do sistema
# --------------------------------------------------------------------------- #
def font_dirs() -> list[Path]:
    """Diretorios de fontes, do mais especifico (projeto) ao do SO."""
    dirs: list[Path] = [BUNDLED_FONTS_DIR]
    home = Path.home()
    if sys.platform == "darwin":
        dirs += [
            home / "Library" / "Fonts",
            Path("/Library/Fonts"),
            Path("/System/Library/Fonts"),
            Path("/System/Library/Fonts/Supplemental"),
        ]
    elif sys.platform.startswith("win"):
        windir = Path(os.environ.get("WINDIR", r"C:\Windows"))
        local = os.environ.get("LOCALAPPDATA")
        dirs += [windir / "Fonts"]
        if local:
            dirs += [Path(local) / "Microsoft" / "Windows" / "Fonts"]
    else:
        dirs += [
            Path("/usr/share/fonts"),
            Path("/usr/local/share/fonts"),
            home / ".fonts",
            home / ".local" / "share" / "fonts",
        ]
    return [d for d in dirs if d.is_dir()]


def _style_key(style: str) -> str:
    return style.strip().lower()


def _is_italic(style: str) -> bool:
    return any(t in _style_key(style) for t in _ITALIC_TOKENS)


def _is_bold(style: str) -> bool:
    return any(t in _style_key(style) for t in _BOLD_TOKENS)


def _family_keys(family: str, style: str) -> list[str]:
    """Chaves de familia para indexar.

    Algumas builds da DejaVu reportam family='DejaVu Sans' e
    style='Condensed Bold'; nesse caso queremos que
    'DejaVu Sans Condensed' tambem resolva.
    """
    keys = [family]
    tokens = [
        t
        for t in style.split()
        if t.lower() not in ("bold", "italic", "oblique", "regular", "book")
    ]
    if tokens:
        keys.append(f"{family} {' '.join(tokens)}")
    return keys


@lru_cache(maxsize=1)
def font_index() -> dict[str, dict[str, str]]:
    """{familia_normalizada: {'regular': path, 'bold': path, 'name': str}}."""
    index: dict[str, dict[str, str]] = {}
    seen: set[str] = set()
    for directory in font_dirs():
        try:
            paths = sorted(directory.rglob("*"))
        except OSError:
            continue
        for path in paths:
            if path.suffix.lower() not in _FONT_SUFFIXES or not path.is_file():
                continue
            key = path.name.lower()
            if key in seen:
                continue
            seen.add(key)
            try:
                family, style = ImageFont.truetype(str(path), 12).getname()
            except Exception:
                continue
            if not family:
                continue
            style = style or "Regular"
            if _is_italic(style):
                continue
            slot = "bold" if _is_bold(style) else "regular"
            for fam_key in _family_keys(family, style):
                entry = index.setdefault(
                    _norm(fam_key), {"name": fam_key.strip()}
                )
                entry.setdefault(slot, str(path))
    return index


def _norm(name: str) -> str:
    return "".join(ch for ch in name.lower() if ch.isalnum())


@lru_cache(maxsize=1)
def available_families() -> list[str]:
    """Nomes de familia (com regular disponivel) para o dropdown da UI."""
    names = {
        entry["name"]
        for entry in font_index().values()
        if "regular" in entry or "bold" in entry
    }
    return sorted(names, key=str.lower)


@lru_cache(maxsize=32)
def resolve_family(family: str) -> FontPair:
    """`family` -> caminhos regular/bold, com fallback garantido."""
    index = font_index()
    candidates = [family, *FALLBACK_CHAIN]
    for candidate in candidates:
        entry = index.get(_norm(candidate))
        if not entry:
            continue
        regular = entry.get("regular") or entry.get("bold")
        bold = entry.get("bold") or regular
        if regular:
            return FontPair(entry.get("name", candidate), regular, bold)
    # ultimo recurso: os arquivos empacotados, direto por nome
    regular = BUNDLED_FONTS_DIR / "DejaVuSans.ttf"
    bold = BUNDLED_FONTS_DIR / "DejaVuSans-Bold.ttf"
    if regular.is_file():
        return FontPair("DejaVu Sans", str(regular), str(bold if bold.is_file() else regular))
    raise FontResolutionError(
        f"nao consegui resolver a fonte {family!r} e o fallback empacotado "
        f"nao esta em {BUNDLED_FONTS_DIR}. Coloque DejaVuSans.ttf e "
        "DejaVuSans-Bold.ttf nessa pasta."
    )


@lru_cache(maxsize=512)
def load(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, max(1, int(size)))


# --------------------------------------------------------------------------- #
# cache de glifos (tile() do print_v4.py)
# --------------------------------------------------------------------------- #
class GlyphCache:
    """Tiles RGBA por (char, size, bold, passo_de_angulo, cor).

    Identico ao `tile()` original: desenha o glifo com padding 2px e rotaciona
    por `abkt * quantum` graus (BICUBIC, expand=True). Devolve `(tile, width)`
    onde `width` e a largura do bbox *antes* da rotacao — e o que governa o
    avanco horizontal no print_v4.py.
    """

    __slots__ = ("regular", "bold", "quantum", "_tiles")

    def __init__(self, pair: FontPair, rotation_quantum_deg: float = 3.0) -> None:
        self.regular = pair.regular
        self.bold = pair.bold
        self.quantum = float(rotation_quantum_deg)
        self._tiles: dict[tuple, tuple[Image.Image, int]] = {}

    def __len__(self) -> int:
        return len(self._tiles)

    def tile(
        self,
        ch: str,
        size: int,
        bold: bool,
        angle_step: int,
        color: tuple[int, int, int],
    ) -> tuple[Image.Image, int]:
        key = (ch, size, bold, angle_step, color)
        cached = self._tiles.get(key)
        if cached is not None:
            return cached
        font = load(self.bold if bold else self.regular, size)
        bbox = font.getbbox(ch)
        w = max(1, bbox[2] - bbox[0])
        h = max(1, bbox[3] - bbox[1])
        pad = 2
        img = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
        ImageDraw.Draw(img).text(
            (pad - bbox[0], pad - bbox[1]), ch, font=font, fill=color + (255,)
        )
        if angle_step:
            img = img.rotate(
                angle_step * self.quantum, expand=True, resample=Image.BICUBIC
            )
        result = (img, w)
        self._tiles[key] = result
        return result


__all__ = [
    "FontPair",
    "FontResolutionError",
    "GlyphCache",
    "available_families",
    "font_dirs",
    "font_index",
    "load",
    "resolve_family",
    "BUNDLED_FONTS_DIR",
]
