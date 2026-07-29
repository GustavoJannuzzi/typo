#!/usr/bin/env python3
"""Cria a estrutura de um projeto novo.

    python scripts/new_project.py meu-poster
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from typo.cli import new_project_main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(new_project_main())
