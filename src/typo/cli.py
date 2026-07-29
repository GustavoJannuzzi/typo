"""Entry points de linha de comando (render headless e scaffold de projeto)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from typo import export as export_mod
from typo.engine import render_result
from typo.project import Project, ProjectError, list_projects, load_project


def render_main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="typo-render",
        description="Renderiza um projeto em alta resolucao e salva PNG + PDF.",
    )
    ap.add_argument("project", help="caminho do project.yaml, da pasta, ou o nome do projeto")
    ap.add_argument("--dpi", type=int, default=None, help="sobrescreve page.dpi_export")
    ap.add_argument("--out", default=None, help="pasta de saida (default: <projeto>/output)")
    ap.add_argument("--name", default=None, help="basename dos arquivos gerados")
    ap.add_argument("--preview", action="store_true", help="renderiza em baixa resolucao (so PNG)")
    ap.add_argument("--no-pdf", action="store_true", help="nao gera o PDF")
    args = ap.parse_args(argv)

    try:
        project = load_project(args.project)
        config = project.config()
    except ProjectError as exc:
        print(f"erro: {exc}", file=sys.stderr)
        available = list_projects()
        if available:
            print(f"projetos disponiveis: {', '.join(available)}", file=sys.stderr)
        return 2

    if args.dpi:
        config = config.merge({"page": {"dpi_export": args.dpi}})

    mode = "preview" if args.preview else "export"
    result = render_result(config, mode)
    print(result.summary())

    out_dir = Path(args.out) if args.out else project.output_dir
    if mode == "preview":
        out_dir.mkdir(parents=True, exist_ok=True)
        png = out_dir / f"{export_mod.slugify(args.name or project.name)}_preview.png"
        result.image.save(png)
        print(png)
        return 0

    paths = export_mod.save(
        result,
        out_dir,
        name=args.name or project.name,
        write_pdf=not args.no_pdf,
    )
    print(paths.png)
    if not args.no_pdf:
        w, h = export_mod.pdf_page_cm(paths.pdf)
        print(f"{paths.pdf}  (mediabox {w:.1f}x{h:.1f} cm)")
    return 0


def new_project_main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="typo-new-project",
        description="Cria projects/<nome>/{refs,text,output} + project.yaml template.",
    )
    ap.add_argument("name", help="nome do projeto (vira o nome da pasta)")
    ap.add_argument("--root", default=None, help="raiz alternativa para projects/")
    args = ap.parse_args(argv)

    try:
        target = Project.scaffold(args.name, args.root)
    except ProjectError as exc:
        print(f"erro: {exc}", file=sys.stderr)
        return 2
    print(f"criado: {target}")
    print("proximos passos:")
    print(f"  1. copie a imagem de referencia para {target / 'refs'}")
    print(f"  2. escreva a letra/trecho em {target / 'text' / (args.name + '.txt')}")
    print(f"  3. ajuste source.image / source.crop em {target / 'project.yaml'}")
    print(f"  4. python scripts/render.py {target / 'project.yaml'}")
    return 0


__all__ = ["new_project_main", "render_main"]
