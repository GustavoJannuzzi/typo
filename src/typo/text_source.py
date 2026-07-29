"""Carrega o texto e monta o stream de caracteres consumido pela tipografia.

No print_v4.py isso era:

    LINES = [...]
    def stream(): return list((("   ".join(LINES)+"   ")*60))

Aqui as frases vem de um .txt e o modo de tokenizacao e configuravel.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from typo.config import TextCfg


class TextSourceError(RuntimeError):
    pass


def read_lines(path: str | Path) -> list[str]:
    p = Path(path)
    if not p.is_file():
        raise TextSourceError(
            f"arquivo de texto nao encontrado: {p}\n"
            "Coloque a letra/trecho em projects/<nome>/text/ e aponte "
            "text.file no project.yaml."
        )
    raw = p.read_text(encoding="utf-8")
    lines = [ln.strip() for ln in raw.splitlines()]
    lines = [ln for ln in lines if ln and not ln.startswith("#")]
    if not lines:
        raise TextSourceError(f"arquivo de texto vazio (ou so comentarios): {p}")
    return lines


def tokenize(lines: list[str], mode: str) -> list[str]:
    if mode == "phrases":
        return lines
    if mode == "words":
        return [w for ln in lines for w in ln.split()]
    if mode == "chars":
        return [c for ln in lines for c in ln if not c.isspace()]
    raise TextSourceError(
        f"text.mode invalido: {mode!r} (use 'phrases', 'words' ou 'chars')"
    )


def build_stream(cfg: TextCfg) -> list[str]:
    """Lista de caracteres, ja repetida `cfg.repeat` vezes.

    Em `chars` o separador e ignorado (o modo existe justamente para produzir
    uma textura continua, sem espacos).
    """
    lines = read_lines(cfg.text_path)
    units = tokenize(lines, cfg.mode)
    sep = "" if cfg.mode == "chars" else cfg.separator
    body = sep.join(units) + sep
    if not body:
        raise TextSourceError("stream de texto vazio apos tokenizacao")
    return list(body * max(1, int(cfg.repeat)))


@lru_cache(maxsize=8)
def _cached_stream(path: str, mtime: float, mode: str, sep: str, repeat: int):
    return tuple(build_stream(TextCfg(text_path=path, mode=mode, separator=sep, repeat=repeat)))


def build_stream_cached(cfg: TextCfg) -> tuple[str, ...]:
    """Versao memoizada por (arquivo, mtime, modo, separador, repeticoes)."""
    p = Path(cfg.text_path)
    mtime = p.stat().st_mtime if p.is_file() else 0.0
    return _cached_stream(str(p), mtime, cfg.mode, cfg.separator, int(cfg.repeat))


__all__ = ["TextSourceError", "build_stream", "build_stream_cached", "read_lines", "tokenize"]
