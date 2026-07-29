"""typo — gerador local de arte tipografica (halftone com letras).

Refatoracao do `print_v4.py`: mesmo algoritmo, parametrizado por `RenderConfig`
e organizado em camadas desacopladas (mascara, paisagem, tipografia).
"""
from __future__ import annotations

__version__ = "0.1.0"

from typo.config import RenderConfig  # noqa: E402
from typo.engine import render, render_result  # noqa: E402

__all__ = ["RenderConfig", "__version__", "render", "render_result"]
