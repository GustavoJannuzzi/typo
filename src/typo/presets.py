"""Presets nomeados de estilo.

`magalenha` e o preset de referencia: os defaults da `RenderConfig` sao,
literalmente, os parametros do `print_v4.py`. Qualquer preset novo deve
ser uma *derivacao* declarada aqui, nunca um fork do motor.
"""
from __future__ import annotations

from typing import Any

from typo.config import RenderConfig

#: nome -> overrides aplicados por cima dos defaults
PRESETS: dict[str, dict[str, Any]] = {
    # os defaults da RenderConfig ja sao o magalenha
    "magalenha": {},
    # halftone puro: sem mascara e sem paisagem, a imagem inteira vira texto
    "halftone": {
        "mask": {"enabled": False},
        "landscape": {"enabled": False},
        "accent": {"enabled": False},
    },
}


def names() -> list[str]:
    return sorted(PRESETS)


def get(name: str) -> RenderConfig:
    """Config base de um preset."""
    if name not in PRESETS:
        raise KeyError(
            f"preset desconhecido: {name!r} (disponiveis: {', '.join(names())})"
        )
    return RenderConfig().merge(PRESETS[name])


def register(name: str, overrides: dict[str, Any]) -> None:
    PRESETS[name] = overrides


__all__ = ["PRESETS", "get", "names", "register"]
