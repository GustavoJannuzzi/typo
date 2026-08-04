#!/usr/bin/env python3
"""Gera o selo tipografico de uma peca vendida: um QR feito das letras da obra.

    python scripts/make_seal.py ouro-marrom                              # sorteia o codigo
    python scripts/make_seal.py ouro-marrom --code 7QK4M2                # codigo dado
    python scripts/make_seal.py emicida --owner Geovana --code 7QK4M2
    python scripts/make_seal.py debret-antropofagia --edition 3/5

Le o `project.yaml` da obra para pegar a familia de fonte e o .txt — o selo e'
feito das letras daquela peca, nao de um texto generico. Escreve PNG (com dpi
embutido) + PDF no tamanho fisico exato em `projects/<slug>/output/selos/`, e
registra o selo em `site/src/data/seals.json` — e' dali que
`scripts/build_certificates.py` e o plugin `site/build/certificates.js` leem
para gerar a pagina publica do certificado.

**Roda offline.** O `CLAUDE.md` diz que nada chama rede para gerar, e isto
inclui o selo: o codigo entra por argumento (ou e' sorteado aqui) e o registro
sai como um arquivo local pra versionar — quem publica e' o `git push`.

**`seals.json` vai pro git, ao contrario de `projects/*/output/`.** E' o unico
registro do que foi vendido: se ficasse so no CSV antigo (gitignored dentro de
`projects/*/output/`), sumiria num clone limpo. PNG e PDF continuam em
`projects/<slug>/output/selos/` porque sao reproduziveis a partir do codigo +
payload — o registro e' a unica coisa que NAO e'.

**Nao escreve arquivo que nao le.** Antes de salvar, o proprio script manda um
decodificador independente (`zxing-cpp`) ler o PNG que acabou de desenhar, em
resolucao nativa e reduzido. Se nao ler, sai com erro e nao gera nada — um selo
bonito que nao escaneia e' pior que nenhum selo, porque so' se descobre no papel.

Isso NAO substitui o teste do celular. E' a condicao necessaria; a suficiente e'
imprimir e escanear de longe e de perto.
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
import secrets
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import img2pdf  # noqa: E402
from PIL import Image  # noqa: E402

from typo import seal as seal_mod  # noqa: E402
from typo.project import ProjectError, list_projects, load_project  # noqa: E402

SEALS_JSON = ROOT / "site" / "src" / "data" / "seals.json"
CONFIG_JS = ROOT / "site" / "src" / "config.js"

#: dominio publicado hoje: o app da Vercel, aprovado pelo Gustavo em 2026-08-03
#: sabendo que e' um subdominio que ele nao possui (se um dominio proprio vier
#: depois, ele reemite os selos e avisa quem comprou — risco assumido, nao
#: nosso). Espelha CONFIG.SITE_URL em site/src/config.js quando preenchido;
#: ver `_site_url_from_config()`.
DEFAULT_BASE_URL = "https://typo-jet.vercel.app"

#: caminho legivel — custa 0 modulos a mais que "/S/": medido com segno,
#: ambos fecham em V4/33 modulos pra uma URL deste tamanho de dominio.
CERT_PATH = "certificado"

#: Crockford base32: sem I, L, O e U — nao ha o que confundir lendo em voz alta
#: nem digitando o codigo a mao se o QR estiver arranhado.
ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
CODE_LEN = 6

#: reducoes em que o selo tem que continuar legivel antes de virar arquivo.
#: 400px num selo de 7cm e' mais ou menos um celular a um braco de distancia.
VERIFY_SIZES = (800, 400)


def new_code() -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(CODE_LEN))


def build_payload(base_url: str, code: str) -> str:
    """A URL do selo, EM MAIUSCULA.

    Maiuscula nao e' estetica: joga o QR para o modo alfanumerico, que cabe em
    menos modulos que o modo byte — modulo maior no mesmo papel, de graca.
    Dominio e' case-insensitive por definicao; o path o site resolve sem
    diferenciar caixa.
    """
    return f"{base_url.rstrip('/')}/{CERT_PATH}/{code}".upper()


def _site_url_from_config() -> str:
    """Le CONFIG.SITE_URL de site/src/config.js sem precisar de um parser JS.

    So' usado pra AVISAR se `--base-url` diverge do que o site publicado diz
    de si mesmo — nunca pra decidir o payload sozinho. Regex tosco de proposito:
    o arquivo e' um objeto literal simples, escrito a mao, nao um bundle.
    """
    if not CONFIG_JS.is_file():
        return ""
    m = re.search(r'SITE_URL:\s*"([^"]*)"', CONFIG_JS.read_text(encoding="utf-8"))
    return (m.group(1) if m else "").rstrip("/")


def verify(image: Image.Image, payload: str) -> list[str]:
    """Decodifica o que foi desenhado. Devolve a lista de falhas (vazia = ok)."""
    try:
        import zxingcpp
    except ImportError:
        raise SystemExit(
            "erro: o selo so' e' gravado depois de ser lido de volta, e o "
            "decodificador nao esta' instalado.\n"
            '    .venv/Scripts/python.exe -m pip install -e ".[dev]"\n'
            "    (ou --skip-verify, sob sua responsabilidade)"
        )

    falhas = []
    for label, img in [("nativo", image)] + [
        (f"{px}px", image.resize((px, px), Image.LANCZOS)) for px in VERIFY_SIZES
    ]:
        result = zxingcpp.read_barcode(img.convert("L"))
        lido = result.text if result is not None and result.valid else None
        if lido != payload:
            falhas.append(f"{label}: leu {lido!r}")
    return falhas


# --------------------------------------------------------------------------- #
# registro — site/src/data/seals.json, versionado de proposito (ver docstring)
# --------------------------------------------------------------------------- #
def load_seals() -> list[dict]:
    if not SEALS_JSON.is_file():
        return []
    raw = json.loads(SEALS_JSON.read_text(encoding="utf-8") or "[]")
    if not isinstance(raw, list):
        raise SystemExit(f"erro: {SEALS_JSON} nao e' uma lista JSON")
    return raw


def save_seals(seals: list[dict]) -> None:
    ordered = sorted(seals, key=lambda s: (s["issuedOn"], s["code"]))
    SEALS_JSON.parent.mkdir(parents=True, exist_ok=True)
    SEALS_JSON.write_text(
        json.dumps(ordered, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="make_seal.py",
        description="Gera o selo tipografico (QR de letras) de uma peca vendida.",
    )
    ap.add_argument("work", help="nome do projeto (ex: ouro-marrom)")
    ap.add_argument("--code", default=None, help=f"codigo do selo ({CODE_LEN} chars); default sorteia")
    ap.add_argument("--base-url", default=DEFAULT_BASE_URL, help=f"default: {DEFAULT_BASE_URL}")
    ap.add_argument("--size-cm", type=float, default=7.0, help="lado do selo (default 7)")
    ap.add_argument("--dpi", type=int, default=600, help="default 600")
    ap.add_argument("--edition", default="", help='edicao, ex "3/5"')
    ap.add_argument(
        "--owner",
        default="",
        help=(
            "nome de quem fica com a peca, so' o primeiro nome (aparece no "
            "certificado). Vazio = coleção interna, sem dono — nao um "
            "placeholder, uma peca da casa mesmo."
        ),
    )
    ap.add_argument("--font", default=None, help="sobrescreve a familia do project.yaml")
    ap.add_argument("--core-ratio", type=float, default=0.18, help="nucleo solido, x modulo")
    ap.add_argument("--fill-frac", type=float, default=0.82, help="quanto do modulo a letra ocupa")
    ap.add_argument("--no-protect-format", action="store_true", help="libera o format info para letra")
    ap.add_argument("--no-bold", action="store_true")
    ap.add_argument("--out", default=None, help="pasta de saida")
    ap.add_argument("--skip-verify", action="store_true", help="grava sem ler de volta")
    args = ap.parse_args(argv)

    if args.owner and len(args.owner.split()) > 1:
        print(
            f"aviso: --owner {args.owner!r} tem mais de uma palavra. O certificado "
            "e' publico e sem senha — o combinado e' so' o primeiro nome, pra nao "
            "colocar sobrenome numa URL que qualquer um que escanear ve'.",
            file=sys.stderr,
        )

    try:
        project = load_project(args.work)
        cfg = project.config()
    except ProjectError as exc:
        print(f"erro: {exc}", file=sys.stderr)
        if available := list_projects():
            print(f"projetos disponiveis: {', '.join(available)}", file=sys.stderr)
        return 2

    seals = load_seals()
    emitidos = {s["code"] for s in seals}  # unicidade GLOBAL: todo projeto compartilha o alfabeto

    code = (args.code or "").strip().upper()
    if code:
        if invalidos := sorted(set(code) - set(ALPHABET)):
            print(
                f"erro: codigo {code!r} tem caractere fora do alfabeto: {invalidos}\n"
                f"      valido: {ALPHABET} (Crockford base32, sem I L O U)",
                file=sys.stderr,
            )
            return 2
        if len(code) != CODE_LEN:
            print(f"erro: codigo precisa ter {CODE_LEN} caracteres, {code!r} tem {len(code)}", file=sys.stderr)
            return 2
        if code in emitidos:
            print(f"erro: o codigo {code} ja' foi emitido (ver {SEALS_JSON})", file=sys.stderr)
            return 2
    else:
        while (code := new_code()) in emitidos:
            pass

    base_url = args.base_url.rstrip("/")
    site_url = _site_url_from_config()
    if site_url and site_url.upper() != base_url.upper():
        print(
            f"aviso: --base-url e' {base_url!r} mas CONFIG.SITE_URL em "
            f"site/src/config.js e' {site_url!r} — divergem. Confirme antes de "
            "imprimir; o payload usa --base-url.",
            file=sys.stderr,
        )

    payload = build_payload(base_url, code)
    print(f"payload: {payload}")

    edition = None
    if args.edition:
        try:
            n_str, total_str = args.edition.split("/", 1)
            edition = {"n": int(n_str), "total": int(total_str)}
            if not (1 <= edition["n"] <= edition["total"]):
                raise ValueError
        except ValueError:
            print(f"erro: --edition precisa ser \"N/TOTAL\" (ex: 3/5), recebi {args.edition!r}", file=sys.stderr)
            return 2

    spec = seal_mod.SealSpec(
        payload=payload,
        text_path=cfg.text.text_path,
        family=args.font or cfg.font.family,
        size_cm=args.size_cm,
        dpi=args.dpi,
        ink=cfg.colors.ink,
        background=cfg.colors.background,
        bold=not args.no_bold,
        fill_frac=args.fill_frac,
        core_ratio=args.core_ratio,
        protect_format=not args.no_protect_format,
    )

    try:
        result = seal_mod.render(spec)
    except seal_mod.SealError as exc:
        print(f"erro: {exc}", file=sys.stderr)
        return 2

    print(result.summary())
    for w in result.warnings:
        print(f"  aviso: {w}", file=sys.stderr)

    # --- le de volta ANTES de gravar -------------------------------------
    if args.skip_verify:
        print("  aviso: --skip-verify, ninguem conferiu se este selo escaneia", file=sys.stderr)
    else:
        if falhas := verify(result.image, payload):
            print(
                "erro: o selo NAO foi lido de volta — nada foi gravado.\n  "
                + "\n  ".join(falhas)
                + "\n\nafrouxe a estilizacao: --core-ratio 0.25, --fill-frac 0.75, "
                "ou aumente --size-cm/--dpi.",
                file=sys.stderr,
            )
            return 1
        print(f"  lido de volta: nativo + {' + '.join(f'{p}px' for p in VERIFY_SIZES)}")

    # --- grava -----------------------------------------------------------
    out_dir = Path(args.out) if args.out else project.output_dir / "selos"
    out_dir.mkdir(parents=True, exist_ok=True)
    png = out_dir / f"{code}.png"
    pdf = out_dir / f"{code}.pdf"
    result.image.save(png, dpi=(args.dpi, args.dpi))
    layout = img2pdf.get_layout_fun(
        (img2pdf.mm_to_pt(result.size_cm * 10), img2pdf.mm_to_pt(result.size_cm * 10))
    )
    pdf.write_bytes(img2pdf.convert(str(png), layout_fun=layout))

    seals.append(
        {
            "code": code,
            "work": project.name,
            "payload": payload,
            "owner": args.owner.strip() or None,
            "edition": edition,
            "issuedOn": datetime.date.today().isoformat(),
            "sizeCm": round(result.size_cm, 2),
            "dpi": args.dpi,
        }
    )
    save_seals(seals)

    print(png)
    print(f"{pdf}  ({result.size_cm:.2f}x{result.size_cm:.2f} cm)")
    print(f"registrado em {SEALS_JSON}")
    print(
        "\npara publicar a pagina do certificado:\n"
        "  .venv/Scripts/python.exe scripts/build_certificates.py\n"
        "  git add -A && git commit -m \"selo " + code + " — " + project.name + "\" && git push"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
