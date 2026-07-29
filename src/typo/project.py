"""Convencao `projects/<nome>/`: ler, validar e materializar um project.yaml.

    projects/<nome>/
      project.yaml
      refs/      imagens de referencia
      text/      .txt com a letra/trecho
      output/    PNG/PDF gerados
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from typo import presets
from typo.config import RenderConfig

#: raiz do repo (…/Typo). Serve de base para `projects/` quando nada e passado.
REPO_ROOT = Path(__file__).resolve().parents[2]
PROJECTS_DIR = REPO_ROOT / "projects"

_TOP_LEVEL_KEYS = {
    "name",
    "source",
    "text",
    "page",
    "titles",
    "accent",
    "landscape",
    "mask",
    "style_preset",
    "style_overrides",
    "notes",
}


class ProjectError(RuntimeError):
    pass


@dataclass
class Project:
    path: Path  # …/projects/<nome>/project.yaml
    data: dict[str, Any]

    # ------------------------------------------------------------------ io --
    @classmethod
    def load(cls, path: str | Path) -> "Project":
        p = Path(path)
        if p.is_dir():
            p = p / "project.yaml"
        if not p.is_file():
            raise ProjectError(f"project.yaml nao encontrado: {p}")
        try:
            data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as exc:
            raise ProjectError(f"YAML invalido em {p}:\n{exc}") from exc
        if not isinstance(data, dict):
            raise ProjectError(f"{p}: o topo do project.yaml precisa ser um mapa")
        unknown = set(data) - _TOP_LEVEL_KEYS
        if unknown:
            raise ProjectError(
                f"{p}: chaves desconhecidas no topo: {sorted(unknown)} "
                f"(validas: {sorted(_TOP_LEVEL_KEYS)})"
            )
        return cls(path=p, data=data)

    @property
    def dir(self) -> Path:
        return self.path.parent

    @property
    def name(self) -> str:
        return str(self.data.get("name") or self.dir.name)

    @property
    def output_dir(self) -> Path:
        return self.dir / "output"

    @property
    def notes(self) -> str:
        return str(self.data.get("notes") or "")

    def resolve(self, relative: str) -> Path:
        """Caminho relativo ao diretorio do projeto (aceita absoluto)."""
        p = Path(relative)
        return p if p.is_absolute() else (self.dir / p)

    # -------------------------------------------------------------- config --
    def config(self) -> RenderConfig:
        """project.yaml -> RenderConfig (preset -> secoes -> style_overrides)."""
        d = self.data
        cfg = presets.get(str(d.get("style_preset") or "magalenha"))

        overrides: dict[str, Any] = {"name": self.name}

        src = d.get("source") or {}
        if not isinstance(src, dict):
            raise ProjectError(f"{self.path}: 'source' precisa ser um mapa")
        source: dict[str, Any] = {}
        if "image" in src:
            if not src["image"]:
                raise ProjectError(f"{self.path}: source.image vazio")
            source["image_path"] = str(self.resolve(str(src["image"])))
        if "crop" in src:
            crop = src["crop"]
            if crop is None:
                source["crop"] = None
            else:
                if len(crop) != 4:
                    raise ProjectError(
                        f"{self.path}: source.crop precisa ter 4 valores [l, t, r, b]"
                    )
                source["crop"] = tuple(int(v) for v in crop)
        if source:
            overrides["source"] = source

        txt = d.get("text") or {}
        if not isinstance(txt, dict):
            raise ProjectError(f"{self.path}: 'text' precisa ser um mapa")
        text: dict[str, Any] = {}
        if "file" in txt:
            text["text_path"] = str(self.resolve(str(txt["file"])))
        for key in ("mode", "separator", "repeat"):
            if key in txt:
                text[key] = txt[key]
        if text:
            overrides["text"] = text

        page_in = d.get("page") or {}
        if not isinstance(page_in, dict):
            raise ProjectError(f"{self.path}: 'page' precisa ser um mapa")
        page: dict[str, Any] = {}
        for key in (
            "mode",
            "art_height_cm",
            "width_cm",
            "height_cm",
            "dpi_export",
            "preview_max_px",
        ):
            if key in page_in:
                page[key] = page_in[key]
        margins = page_in.get("margins_cm") or {}
        for key, target in (
            ("top", "margin_top_cm"),
            ("bottom", "margin_bottom_cm"),
            ("side", "margin_side_cm"),
        ):
            if key in margins:
                page[target] = margins[key]
        if page:
            overrides["page"] = page

        titles = d.get("titles") or {}
        blocks = {k: v for k, v in titles.items() if v is not None}
        if blocks:
            overrides["text_blocks"] = blocks

        for section in ("accent", "landscape", "mask"):
            value = d.get(section)
            if value:
                overrides[section] = value

        cfg = cfg.merge(overrides)
        cfg = cfg.merge(d.get("style_overrides") or {})
        return cfg.validate()

    # ------------------------------------------------------------ scaffold --
    @staticmethod
    def scaffold(name: str, root: str | Path | None = None) -> Path:
        """Cria projects/<nome>/{refs,text,output} + project.yaml template."""
        base = Path(root) if root else PROJECTS_DIR
        target = base / name
        if (target / "project.yaml").exists():
            raise ProjectError(f"ja existe um projeto em {target}")
        for sub in ("refs", "text", "output"):
            (target / sub).mkdir(parents=True, exist_ok=True)
        (target / "text" / f"{name}.txt").write_text(
            "# uma frase por linha; linhas com # sao ignoradas\n"
            "Cole aqui a letra ou o trecho\n",
            encoding="utf-8",
        )
        (target / "project.yaml").write_text(
            _TEMPLATE.format(name=name), encoding="utf-8"
        )
        return target


def list_projects(root: str | Path | None = None) -> list[str]:
    base = Path(root) if root else PROJECTS_DIR
    if not base.is_dir():
        return []
    return sorted(p.name for p in base.iterdir() if (p / "project.yaml").is_file())


def load_project(name_or_path: str, root: str | Path | None = None) -> Project:
    """Aceita nome de projeto ou caminho para o project.yaml/pasta."""
    p = Path(name_or_path)
    if p.exists():
        return Project.load(p)
    base = Path(root) if root else PROJECTS_DIR
    return Project.load(base / name_or_path)


_TEMPLATE = """\
name: {name}

source:
  image: refs/COLOQUE_A_IMAGEM_AQUI.png
  crop: null                      # [left, top, right, bottom] ou null p/ imagem inteira

text:
  file: text/{name}.txt
  mode: phrases                   # phrases | words | chars

page:
  mode: from_art                  # from_art | fixed
  art_height_cm: 88
  margins_cm: {{ top: 13, bottom: 10.5, side: 7 }}
  dpi_export: 150

titles:
  title: "{name}"
  subtitle: ""
  footer: ""

accent:
  enabled: true
  color: "#963A2A"

style_preset: magalenha           # herda os defaults; o que vier abaixo sobrescreve
style_overrides: {{}}               # ex.: {{ font: {{ base_line_mm: 4.0 }}, flow: {{ flex: 0.6 }} }}

notes: |
  Conceito, estilo e referencias deste projeto.
"""

__all__ = [
    "PROJECTS_DIR",
    "REPO_ROOT",
    "Project",
    "ProjectError",
    "list_projects",
    "load_project",
]
