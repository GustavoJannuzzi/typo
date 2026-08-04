#!/usr/bin/env python3
"""Calcula o conteudo da pagina de certificado a partir do .txt de cada obra.

    python scripts/build_certificates.py

Le `site/src/data/seals.json` (quais obras tem selo emitido),
`site/src/data/works.json` (glifos, titulo, subtitulo), cada
`project.yaml` + `text/*.txt`, e `projects/<slug>/certificado.md` (a carta,
escrita a mao), e escreve `site/src/data/certificates.json` — de onde o plugin
`site/build/certificates.js` monta uma pagina por selo.

**Nao toca no motor.** Tudo aqui e' aritmetica em cima do .txt e do
`works.json` ja gerados; nenhuma linha de `src/typo/` e' importada para
renderizar nada.

A CONTAGEM
----------
O conteudo mais forte do e-mail de entrega (`emails/entrega-emicida.html`) —
"357x levanta", "40.413 letras" — e' CALCULAVEL, nao escrito a mao. A formula:

    volta          = uma passagem inteira pelo texto, no MODO de tokenizacao
                      real do motor (`text_source.build_stream`, repeat=1)
    nao_espacos    = caracteres de `volta` que nao sao espaco
    voltas         = works.json[slug].glyphs / nao_espacos
    ocorrencias(p) = round(quantas vezes `p` aparece em uma volta * voltas)

Por que `nao_espacos` e nao `len(volta)`: em `typography.py` o cursor do
stream ANDA no espaco mas `stats.glyphs` NAO conta espaco (ver o `continue`
antes do `stats.glyphs += 1`). Cada volta completa contribui exatamente
`nao_espacos` glifos ao total — dividir por `len(volta)` daria voltas a menos
e a contagem inteira sairia errada.

Validado contra o e-mail do Emicida como gabarito: 62 frases, "25 e meia"
voltas, e as 10 ocorrencias de palavra batem exatas (ver `tests/test_
certificates.py`). A unica divergencia e' o total de palavras (9.516 vs 9.542
do e-mail, 0.27%) — diferenca de definicao de "palavra" na borda da volta, nao
erro de formula.

A RANKING NAO E' AUTOMATICO, DE PROPOSITO. A primeira versao deste script
tentava "top 10 por frequencia" — e nao bate com o e-mail. "sou" (3x) fica de
fora enquanto "somos" (3x) entra: sao duas conjugacoes do MESMO verbo, e
nenhuma lista de stopword despersonaliza uma da outra. O Gustavo escolheu as
dez palavras a mao quando escreveu o e-mail — e' curadoria, nao algoritmo.
Entao `certificado.md` declara a LISTA (frontmatter `palavras:`), e o script
so' faz a conta pra cada uma. A palavra que aparece primeiro na lista e' o
numero-heroi da pagina.
"""
from __future__ import annotations

import html
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(SCRIPTS_DIR))

from typo.config import RenderConfig, Scale, TextCfg  # noqa: E402
from typo.image_prep import ImagePrepError, crop_size  # noqa: E402
from typo.project import ProjectError, load_project  # noqa: E402
from typo.text_source import TextSourceError, build_stream, read_lines  # noqa: E402

# reaproveita o recorte "arte pura" ja escrito em build_site_assets.py em vez
# de reimplementar — mesma geometria, um so lugar sabendo dela
from build_site_assets import (  # noqa: E402
    DETAIL_PX,
    FULL_PX,
    find_densest_window,
    fit,
)

DATA_DIR = ROOT / "site" / "src" / "data"
ART_DIR = ROOT / "site" / "public" / "art"
PROJECTS_DIR = ROOT / "projects"

SEALS_JSON = DATA_DIR / "seals.json"
WORKS_JSON = DATA_DIR / "works.json"
CERTIFICATES_JSON = DATA_DIR / "certificates.json"

from PIL import Image  # noqa: E402

Image.MAX_IMAGE_PIXELS = None


class CertificateError(RuntimeError):
    pass


# --------------------------------------------------------------------------- #
# fontes de dados
# --------------------------------------------------------------------------- #
def load_json(path: Path, default: Any) -> Any:
    if not path.is_file():
        return default
    return json.loads(path.read_text(encoding="utf-8") or "null") or default


def slugs_with_seals() -> list[str]:
    seals = load_json(SEALS_JSON, [])
    return sorted({s["work"] for s in seals})


def works_by_slug() -> dict[str, dict]:
    return {w["slug"]: w for w in load_json(WORKS_JSON, [])}


# --------------------------------------------------------------------------- #
# certificado.md — frontmatter YAML + corpo em markdown minimo
# --------------------------------------------------------------------------- #
def parse_certificado_md(path: Path) -> tuple[dict, str]:
    """Frontmatter YAML entre linhas '---' (pode vir vazio, so' '---'/'---')
    + corpo em markdown minimo. Parseado por linha, nao por regex de bloco:
    um regex `(.*?)\\n---` nao caça o caso de frontmatter vazio (as duas
    marcações '---' ficam coladas, sem `\\n` sobrando entre elas pra casar)."""
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        raise CertificateError(
            f"{path}: precisa comecar com frontmatter YAML entre linhas '---'"
        )
    try:
        close = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        raise CertificateError(f"{path}: frontmatter aberto com '---' nunca fecha")

    front = yaml.safe_load("\n".join(lines[1:close])) or {}
    if not isinstance(front, dict):
        raise CertificateError(f"{path}: o frontmatter precisa ser um mapa")
    body = "\n".join(lines[close + 1 :]).strip()
    if not body:
        raise CertificateError(f"{path}: corpo da carta vazio")
    return front, body


def md_to_html(body: str) -> str:
    """Paragrafo por linha em branco, `*texto*` -> <em>. Escapa HTML antes."""
    out = []
    for para in re.split(r"\n\s*\n", body.strip()):
        text = html.escape(" ".join(line.strip() for line in para.splitlines()))
        text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
        out.append(f"<p>{text}</p>")
    return "".join(out)


# --------------------------------------------------------------------------- #
# a contagem
# --------------------------------------------------------------------------- #
def normalize_word(w: str) -> str:
    """minuscula, sem acento, sem pontuacao nas pontas — a MESMA normalizacao
    usada pra validar contra o gabarito do e-mail (10/10 ocorrencias)."""
    w = unicodedata.normalize("NFD", w.lower())
    w = "".join(c for c in w if unicodedata.category(c) != "Mn")
    return w.strip(".,!?;:()\"'‘’“”…")


def compute_contagem(cfg: RenderConfig, glyphs: int, palavras: list[str]) -> dict:
    """A contagem de uma obra. `palavras` e' a lista curada (certificado.md)."""
    if cfg.text.regions:
        raise CertificateError(
            "text.regions nao e' suportado pela contagem: o cursor e' um por "
            "regiao, entao 'voltas' nao tem um valor unico para a obra. "
            "Remova a secao 'contagem' do certificado.md desta obra, ou peca "
            "pro Gustavo decidir contagem por regiao."
        )

    lines = read_lines(cfg.text.text_path)
    try:
        volta = "".join(
            build_stream(
                TextCfg(
                    text_path=cfg.text.text_path,
                    mode=cfg.text.mode,
                    separator=cfg.text.separator,
                    repeat=1,
                )
            )
        )
    except TextSourceError as exc:
        raise CertificateError(str(exc)) from exc

    nao_espacos = sum(1 for c in volta if c != " ")
    if nao_espacos == 0:
        raise CertificateError(f"{cfg.text.text_path}: stream sem nenhum caractere nao-espaco")
    voltas = glyphs / nao_espacos

    # contagem de PALAVRA e' sobre o texto-fonte (frases coladas com espaco),
    # independente do modo de tokenizacao do motor (phrases/words/chars) — o
    # motor decide como DESENHAR, isso aqui decide quantas vezes uma palavra
    # aparece no texto que cicla `voltas` vezes dentro da arte
    tokens = [normalize_word(w) for w in " ".join(lines).split()]
    tokens = [t for t in tokens if t]
    total_palavras = round(len(tokens) * voltas)

    from collections import Counter

    counts = Counter(tokens)
    ranking = []
    for p in palavras:
        n = counts[normalize_word(p)]
        if n == 0:
            raise CertificateError(
                f"a palavra {p!r} declarada em certificado.md nao aparece no "
                f"texto de {cfg.name} — confira a grafia"
            )
        ranking.append({"palavra": p, "vezes": round(n * voltas)})

    return {
        "frases": len(lines) if cfg.text.mode == "phrases" else None,
        "voltas": round(voltas, 2),
        "letras": glyphs,
        "palavras": total_palavras,
        "heroi": ranking[0] if ranking else None,
        "ranking": ranking,
    }


# --------------------------------------------------------------------------- #
# imagem da obra — reusa public/art/*.webp; gera se faltar e o export existir
# --------------------------------------------------------------------------- #
def _art_bbox_from_crop_dims(cfg: RenderConfig, crop_w: int, crop_h: int, dpi: float = 150) -> tuple[int, int, int, int]:
    """Mesma geometria de `build_site_assets.art_bbox_px`, mas recebendo
    crop_w/crop_h prontos em vez de abrir a imagem de referencia — para obras
    cuja referencia se perdeu mas cujo `source.crop` (e portanto o tamanho do
    recorte) continua escrito no project.yaml. Ver CLAUDE.md, secao Estado,
    sobre o magalenha."""
    scale = Scale(dpi)
    art_w, art_h = cfg.art_size(crop_w, crop_h, dpi)
    pw, ph = cfg.page_size(art_w, art_h, dpi)
    ox = (pw - art_w) // 2
    oy = int(scale.cm(cfg.page.margin_top_cm))
    return ox, oy, ox + art_w, oy + art_h


def ensure_art_assets(slug: str, cfg: RenderConfig) -> dict | None:
    full = ART_DIR / f"{slug}-full.webp"
    detail = ART_DIR / f"{slug}-detail.webp"
    if full.is_file() and detail.is_file():
        return {"full": f"/art/{slug}-full.webp", "detail": f"/art/{slug}-detail.webp"}

    pngs = sorted((PROJECTS_DIR / slug / "output").glob("*150dpi.png"))
    if not pngs:
        return None  # sem export nenhum: certificado sai sem secao de imagem

    if cfg.source.crop is not None:
        l, t, r, b = cfg.source.crop
        crop_w, crop_h = r - l, b - t
    else:
        try:
            crop_w, crop_h = crop_size(cfg.source.image_path, cfg.source.crop)
        except ImagePrepError:
            return None  # sem crop fixo e sem a imagem de referencia: bbox desconhecido

    bbox = _art_bbox_from_crop_dims(cfg, crop_w, crop_h)
    with Image.open(pngs[0]) as raw:
        page = raw.convert("RGB")
        art = page.copy() if cfg.display.enabled else page.crop(bbox)
        halftone = page.crop(bbox)

    ART_DIR.mkdir(parents=True, exist_ok=True)
    fit(art, FULL_PX).save(full, quality=84, method=6)
    side = min(DETAIL_PX, *halftone.size)
    dx, dy = find_densest_window(halftone, side)
    halftone.crop((dx, dy, dx + side, dy + side)).save(detail, quality=88, method=6)
    print(f"  gerado {slug}-full.webp + {slug}-detail.webp a partir do export checked-in")
    return {"full": f"/art/{slug}-full.webp", "detail": f"/art/{slug}-detail.webp"}


# --------------------------------------------------------------------------- #
# uma obra
# --------------------------------------------------------------------------- #
def build_one(slug: str, works: dict[str, dict]) -> dict | None:
    md_path = PROJECTS_DIR / slug / "certificado.md"
    if not md_path.is_file():
        print(f"  ! {slug}: sem certificado.md, pulando (obra sem certificado)")
        return None

    try:
        project = load_project(slug)
        cfg = project.config()
    except ProjectError as exc:
        raise CertificateError(f"{slug}: {exc}") from exc

    front, body = parse_certificado_md(md_path)
    carta_html = md_to_html(body)

    entry = works.get(slug)
    glyphs = entry.get("glyphs") if entry else None
    palavras = front.get("palavras") or []
    if not isinstance(palavras, list):
        raise CertificateError(f"{md_path}: 'palavras' precisa ser uma lista")

    contagem = None
    if palavras and glyphs is None:
        raise CertificateError(
            f"{md_path}: declara 'palavras' mas {slug} nao tem 'glyphs' em "
            f"works.json (obra sem export processado por build_site_assets.py — "
            "ver 'Estado' no CLAUDE.md). Remova 'palavras' do certificado.md ou "
            "gere o works.json pra esta obra primeiro."
        )
    if palavras:
        contagem = compute_contagem(cfg, glyphs, [str(p) for p in palavras])
    elif glyphs is None:
        print(f"  aviso {slug}: sem 'glyphs' em works.json — certificado sem secao de contagem")

    return {
        "title": str(front.get("titulo") or cfg.text_blocks.title or project.name.upper()),
        "subtitle": cfg.text_blocks.subtitle,
        "carta": carta_html,
        "contagem": contagem,
        "art": ensure_art_assets(slug, cfg),
    }


def main() -> int:
    works = works_by_slug()
    slugs = slugs_with_seals()
    if not slugs:
        print(f"nenhum selo em {SEALS_JSON} — nada a fazer")
        return 0

    certificates: dict[str, dict] = {}
    for slug in slugs:
        print(f"{slug}:")
        cert = build_one(slug, works)
        if cert is not None:
            certificates[slug] = cert
            contagem = cert["contagem"]
            resumo = (
                f"{contagem['heroi']['vezes']}x {contagem['heroi']['palavra']}, "
                f"{contagem['letras']} letras"
                if contagem
                else "sem contagem"
            )
            print(f"  ok  {resumo}")

    missing = [s for s in slugs if s not in certificates]
    if missing:
        # selo emitido sem certificado.md e' um QR que aponta pra pagina que
        # nao existe — isso e' erro de publicacao, nao aviso
        raise CertificateError(
            "as obras a seguir tem selo emitido em seals.json mas NAO tem "
            f"certificado.md: {missing}. Escreva a carta antes de publicar, "
            "ou a URL impressa no selo cai em 404."
        )

    CERTIFICATES_JSON.write_text(
        json.dumps(certificates, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"\n{len(certificates)} certificado(s) -> {CERTIFICATES_JSON}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CertificateError as exc:
        print(f"erro: {exc}", file=sys.stderr)
        raise SystemExit(2) from None
