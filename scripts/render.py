#!/usr/bin/env python3
"""Render headless a partir de um project.yaml (sem UI).

    python scripts/render.py projects/magalenha/project.yaml
    python scripts/render.py magalenha --dpi 72 --no-pdf
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from typo.cli import render_main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(render_main())
