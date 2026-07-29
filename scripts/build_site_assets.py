#!/usr/bin/env python3
"""Gera os assets web da landing page a partir dos exports de 150 dpi.

    python scripts/build_site_assets.py

Le `projects/*/output/*150dpi.png` + cada `project.yaml` e escreve:

    site/public/art/<slug>-full.webp     (arte pura, 1600px no lado maior —
                                          sem titulo/margem/moldura do poster)
    site/public/art/<slug>-thumb.webp    (800px)
    site/public/art/<slug>-detail.webp   (recorte 1:1 em resolucao nativa —
                                          e onde se ve que a imagem e feita de letras)
    site/src/data/works.json             (metadados de especime)

Alem disso, para a peca de comparacao antes/depois (COMPARE_SLUG), recorta a
imagem de referencia ORIGINAL com o mesmo `source.crop` do project.yaml e
redimensiona pro mesmo tamanho da arte pura — as duas casam pixel a pixel
na faixa, o que da pro slider de arrastar alinhar sem distorcer nada.

O recorte "pura" (sem a moldura do compose.py) usa a MESMA matematica do
engine.py: ox = (pagina_w - arte_w)//2, oy = margem_topo em px. Nao e um
reimplementacao do algoritmo — e so a geometria de posicionamento, que ja
esta exposta em RenderConfig.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from typo.config import Scale  # noqa: E402
from typo.image_prep import crop_size, open_source  # noqa: E402
from typo.project import load_project  # noqa: E402

Image.MAX_IMAGE_PIXELS = None

ART_DIR = ROOT / "site" / "public" / "art"
DATA_DIR = ROOT / "site" / "src" / "data"

FULL_PX = 1600
THUMB_PX = 800
DETAIL_PX = 1100
EXPORT_DPI = 150

#: par usado na secao "como funciona" (arrasta pra revelar)
COMPARE_SLUG = "ouro-marrom"

ORDER = [
    "ouro-marrom",
    "nossa-senhora",
    "cidade-de-deus",
    "dom-casmurro",
    "garota-de-ipanema",
    "central-do-brasil",
    "ainda-estou-aqui",
    "emicida",
    "jotape",
]

GLYPHS = {
    "ouro-marrom": 35880,
    "nossa-senhora": 26668,
    "cidade-de-deus": 21216,
    "dom-casmurro": 36603,
    "garota-de-ipanema": 3322 + 20125,
    "central-do-brasil": 11029 + 1813,
    "ainda-estou-aqui": 109353,
    "emicida": 40413,
    "jotape": 171724,
}

BLURB = {
    "ouro-marrom": "O chapéu vira massa sólida e a pele é o destaque em ouro.",
    "nossa-senhora": "A oração inteira cabe no véu. Fundo liso, recorte limpo.",
    "cidade-de-deus": "O letreiro da capa vira letra feita de letra.",
    "dom-casmurro": "Placa de colódio: a vinheta escura virou moldura natural.",
    "garota-de-ipanema": "Figura recortada, Dois Irmãos em contorno fino ao fundo.",
    "central-do-brasil": "Caligrafia: o filme é sobre cartas escritas à mão.",
    "ainda-estou-aqui": "Datilografia — o filme é feito de papel timbrado.",
    "emicida": "Sem máscara: o contraste tonal separa terno, gola e fundo.",
    "jotape": "Halftone puro. A pichação do trailer lê inteira.",
}

STYLE_FAMILY = {
    "ouro-marrom": "retrato",
    "nossa-senhora": "retrato",
    "dom-casmurro": "retrato",
    "cidade-de-deus": "estencil",
    "jotape": "cena",
    "emicida": "cena",
    "garota-de-ipanema": "paisagem",
    "central-do-brasil": "paisagem",
    "ainda-estou-aqui": "paisagem",
}


def art_bbox_px(cfg, dpi: float = EXPORT_DPI) -> tuple[int, int, int, int]:
    """(x0,y0,x1,y1) da arte pura dentro da pagina exportada — sem titulo/
    margem/moldura. Mesma geometria de engine.render_result."""
    crop_w, crop_h = crop_size(cfg.source.image_path, cfg.source.crop)
    scale = Scale(dpi)
    art_w, art_h = cfg.art_size(crop_w, crop_h, dpi)
    pw, ph = cfg.page_size(art_w, art_h, dpi)
    ox = (pw - art_w) // 2
    oy = int(scale.cm(cfg.page.margin_top_cm))
    return ox, oy, ox + art_w, oy + art_h


def find_densest_window(img: Image.Image, size: int) -> tuple[int, int]:
    step = 8
    small = img.convert("L").resize(
        (max(1, img.width // step), max(1, img.height // step)), Image.BILINEAR
    )
    arr = 255.0 - np.asarray(small, dtype=np.float64)
    win = max(1, size // step)
    if arr.shape[0] <= win or arr.shape[1] <= win:
        return max(0, (img.width - size) // 2), max(0, (img.height - size) // 2)
    acc = np.zeros((arr.shape[0] + 1, arr.shape[1] + 1), dtype=np.float64)
    np.cumsum(np.cumsum(arr, axis=0), axis=1, out=acc[1:, 1:])
    tot = acc[win:, win:] - acc[:-win, win:] - acc[win:, :-win] + acc[:-win, :-win]
    y, x = np.unravel_index(int(np.argmax(tot)), tot.shape)
    return min(int(x) * step, img.width - size), min(int(y) * step, img.height - size)


def fit(img: Image.Image, max_px: int) -> Image.Image:
    ratio = max_px / max(img.size)
    if ratio >= 1:
        return img.copy()
    return img.resize(
        (max(1, round(img.width * ratio)), max(1, round(img.height * ratio))),
        Image.LANCZOS,
    )


def layers_of(cfg) -> list[str]:
    out = ["máscara" if cfg.mask.enabled else "halftone puro"]
    if cfg.landscape.enabled:
        out.append("paisagem")
    if cfg.accent.enabled:
        out.append("accent")
    return out


def main() -> int:
    ART_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    works = []
    for slug in ORDER:
        pngs = sorted((ROOT / "projects" / slug / "output").glob("*150dpi.png"))
        if not pngs:
            print(f"  ! {slug}: sem export de 150 dpi, pulando")
            continue
        project = load_project(slug)
        cfg = project.config()

        with Image.open(pngs[0]) as raw:
            page = raw.convert("RGB")
            x0, y0, x1, y1 = art_bbox_px(cfg)
            art = page.crop((x0, y0, x1, y1))

        art_w_px, art_h_px = art.size
        fit(art, FULL_PX).save(ART_DIR / f"{slug}-full.webp", quality=84, method=6)
        fit(art, THUMB_PX).save(ART_DIR / f"{slug}-thumb.webp", quality=80, method=6)

        side = min(DETAIL_PX, art_w_px, art_h_px)
        dx, dy = find_densest_window(art, side)
        art.crop((dx, dy, dx + side, dy + side)).save(
            ART_DIR / f"{slug}-detail.webp", quality=88, method=6
        )

        if slug == COMPARE_SLUG:
            before = open_source(cfg.source.image_path, cfg.source.crop).convert("RGB")
            before = before.resize((art_w_px, art_h_px), Image.LANCZOS)
            fit(before, FULL_PX).save(ART_DIR / f"{slug}-before.webp", quality=86, method=6)
            print(f"  ok {slug}-before.webp  (par de comparacao)")

        w_cm, h_cm = cfg.page_cm(*cfg.art_size(*crop_size(cfg.source.image_path, cfg.source.crop), EXPORT_DPI), EXPORT_DPI)
        works.append(
            {
                "slug": slug,
                "title": cfg.text_blocks.title or project.name.replace("-", " ").upper(),
                "subtitle": cfg.text_blocks.subtitle,
                "blurb": BLURB.get(slug, ""),
                "family": STYLE_FAMILY.get(slug, "retrato"),
                "font": cfg.font.family,
                "bodyMm": round(cfg.font.base_line_mm, 1),
                "layers": layers_of(cfg),
                "widthCm": round(w_cm, 1),
                "heightCm": round(h_cm, 1),
                "px": [art_w_px, art_h_px],
                "aspect": round(art_w_px / art_h_px, 4),
                "glyphs": GLYPHS.get(slug),
            }
        )
        print(f"  ok {slug:<20} arte {art_w_px}x{art_h_px}px  pagina {w_cm:.0f}x{h_cm:.0f}cm")

    (DATA_DIR / "works.json").write_text(
        json.dumps(works, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"\n{len(works)} obras -> {DATA_DIR / 'works.json'}")
    print(f"imagens -> {ART_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
