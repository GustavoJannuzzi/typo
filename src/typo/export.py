"""Export: PNG com dpi embutido + PDF no tamanho fisico exato (img2pdf).

Ultimas linhas do print_v4.py:

    canvas.save(png, dpi=(DPI, DPI))
    layout = img2pdf.get_layout_fun((img2pdf.mm_to_pt(PW_CM*10), img2pdf.mm_to_pt(PH_CM*10)))
    open(pdf,"wb").write(img2pdf.convert(png, layout_fun=layout))
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import img2pdf

from typo.engine import RenderResult

PT_PER_CM = 72.0 / 2.54


@dataclass(frozen=True)
class ExportPaths:
    png: Path
    pdf: Path


def slugify(name: str) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_")
    return s or "typo"


def default_basename(result: RenderResult, name: str) -> str:
    w, h = result.page_cm
    return f"{slugify(name)}_{w:.0f}x{h:.0f}cm_{result.dpi:.0f}dpi"


def save(
    result: RenderResult,
    out_dir: str | Path,
    name: str = "typo",
    basename: str | None = None,
    write_pdf: bool = True,
) -> ExportPaths:
    """Salva PNG (+PDF) em `out_dir`. Devolve os caminhos."""
    if result.mode != "export":
        raise ValueError(
            "export.save espera um RenderResult em mode='export'; "
            f"recebi mode={result.mode!r} (o preview e reduzido e nao serve "
            "para impressao)."
        )
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    stem = basename or default_basename(result, name)
    png = out / f"{stem}.png"
    pdf = out / f"{stem}.pdf"

    dpi = int(round(result.dpi))
    result.image.save(png, dpi=(dpi, dpi))

    if write_pdf:
        pw_cm, ph_cm = result.page_cm
        layout = img2pdf.get_layout_fun(
            (img2pdf.mm_to_pt(pw_cm * 10), img2pdf.mm_to_pt(ph_cm * 10))
        )
        pdf.write_bytes(img2pdf.convert(str(png), layout_fun=layout))
    return ExportPaths(png=png, pdf=pdf if write_pdf else Path())


def pdf_page_cm(path: str | Path) -> tuple[float, float]:
    """Le o MediaBox da primeira pagina e devolve (largura_cm, altura_cm).

    Suficiente para conferir o tamanho fisico do PDF gerado sem depender de
    outra biblioteca.
    """
    data = Path(path).read_bytes()
    m = re.search(
        rb"/MediaBox\s*\[\s*([\d.+-]+)\s+([\d.+-]+)\s+([\d.+-]+)\s+([\d.+-]+)\s*\]", data
    )
    if not m:
        raise ValueError(f"nao achei /MediaBox em {path}")
    x0, y0, x1, y1 = (float(v) for v in m.groups())
    return (x1 - x0) / PT_PER_CM, (y1 - y0) / PT_PER_CM


__all__ = ["ExportPaths", "PT_PER_CM", "default_basename", "pdf_page_cm", "save", "slugify"]
