"""Smoke tests do motor + regressao de geometria contra o print_v4.py."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fixtures import make_reference_image, make_text_file  # noqa: E402

from typo import engine, export as export_mod, presets  # noqa: E402
from typo.config import RenderConfig, hex_to_rgb  # noqa: E402
from typo.project import Project, list_projects, load_project  # noqa: E402

REPO = Path(__file__).resolve().parents[1]

#: numeros de ouro: sao os do PDF de referencia (MAGALENHA_Gustavo_113x111cm.pdf,
#: imagem 6686x6584 px @150dpi) e os do print_v4.py com CROP=(600,55,1420,782).
GOLDEN_CROP = (820, 727)
GOLDEN_ART = (5860, 5196)
GOLDEN_PAGE = (6686, 6584)


@pytest.fixture(scope="session")
def synthetic(tmp_path_factory) -> dict:
    d = tmp_path_factory.mktemp("ref")
    return {
        "image": str(make_reference_image(d / "ref.png")),
        "text": str(make_text_file(d / "text.txt")),
    }


def config_for(synthetic: dict, **overrides) -> RenderConfig:
    base = {
        "source": {"image_path": synthetic["image"], "crop": None},
        "text": {"text_path": synthetic["text"]},
    }
    return RenderConfig().merge(base).merge(overrides)


# --------------------------------------------------------------------------- #
# geometria (regressao contra o print_v4.py / PDF de referencia)
# --------------------------------------------------------------------------- #
def test_page_geometry_matches_reference_pdf():
    cfg = RenderConfig()
    art = cfg.art_size(*GOLDEN_CROP, 150)
    page = cfg.page_size(*art, 150)
    assert art == GOLDEN_ART
    assert page == GOLDEN_PAGE
    w_cm, h_cm = cfg.page_cm(*art, 150)
    assert (round(w_cm), round(h_cm)) == (113, 111)


def test_typography_metrics_match_print_v4():
    """LINE_H / FS_MIN / FS_MAX a 150 dpi tem que dar 20 / 8 / 34."""
    from typo.config import Scale

    cfg = RenderConfig()
    s = Scale(150)
    line_h = max(int(s.px(cfg.font.min_line_px)), int(s.mm(cfg.font.base_line_mm)))
    size_min = max(int(s.px(cfg.font.min_size_px)), int(s.mm(cfg.font.size_min_mm)))
    size_max = int(line_h * cfg.font.size_max_ratio)
    assert (line_h, size_min, size_max) == (20, 8, 34)


# --------------------------------------------------------------------------- #
# render
# --------------------------------------------------------------------------- #
def test_preview_renders_and_is_not_blank(synthetic):
    result = engine.render_result(config_for(synthetic), "preview")
    img = result.image
    assert max(img.size) <= RenderConfig().page.preview_max_px

    arr = np.asarray(img.convert("RGB"))
    # fundo branco de verdade
    white = (arr == 255).all(axis=2)
    assert white.mean() > 0.3, "a arte cobriu a pagina inteira — fundo nao ficou branco"
    # tinta de verdade
    dark = arr.max(axis=2) < 120
    assert dark.mean() > 0.02, "quase nao ha tinta — a imagem saiu (quase) branca"
    # accent presente
    r, g, b = arr[:, :, 0].astype(int), arr[:, :, 1].astype(int), arr[:, :, 2].astype(int)
    assert ((r - g > 25) & (r - b > 25) & (r > 90)).sum() > 200, "accent nao apareceu"
    # camadas contabilizadas
    assert result.stats["glyphs"] > 1000
    assert result.stats["landscape_glyphs"] > 0


def test_preview_reacts_to_typography_sliders(synthetic):
    base = config_for(synthetic)
    a = engine.render_result(base, "preview")
    b = engine.render_result(base.merge({"font": {"base_line_mm": 6.0}}), "preview")
    assert a.stats["glyphs"] != b.stats["glyphs"]

    c = engine.render_result(base.merge({"flow": {"flex": 0.0}}), "preview")
    assert not np.array_equal(np.asarray(a.image), np.asarray(c.image))


def test_layers_are_independently_switchable(synthetic):
    no_land = engine.render_result(
        config_for(synthetic, landscape={"enabled": False}), "preview"
    )
    assert no_land.stats["landscape_glyphs"] == 0

    no_mask = engine.render_result(
        config_for(synthetic, mask={"enabled": False}, landscape={"enabled": False}),
        "preview",
    )
    # sem mascara a arte inteira vira halftone -> muito mais glifos
    with_mask = engine.render_result(config_for(synthetic), "preview")
    assert no_mask.stats["glyphs"] > with_mask.stats["glyphs"]

    no_accent = engine.render_result(
        config_for(synthetic, accent={"enabled": False}), "preview"
    )
    arr = np.asarray(no_accent.image)
    r, g, b = arr[:, :, 0].astype(int), arr[:, :, 1].astype(int), arr[:, :, 2].astype(int)
    accent_rgb = hex_to_rgb(RenderConfig().accent.color)
    del accent_rgb
    assert ((r - g > 25) & (r - b > 25) & (r > 90)).sum() < 200


def test_export_writes_png_and_pdf_with_physical_size(synthetic, tmp_path):
    cfg = config_for(synthetic, page={"dpi_export": 30})
    result = engine.render_result(cfg, "export")
    paths = export_mod.save(result, tmp_path, name="teste")
    assert paths.png.is_file() and paths.pdf.is_file()

    with Image.open(paths.png) as png:
        assert png.size == result.image.size
        assert png.info.get("dpi", (0, 0))[0] == pytest.approx(30, abs=1)

    w_cm, h_cm = export_mod.pdf_page_cm(paths.pdf)
    assert w_cm == pytest.approx(result.page_cm[0], abs=0.05)
    assert h_cm == pytest.approx(result.page_cm[1], abs=0.05)


def test_export_refuses_preview_result(synthetic):
    result = engine.render_result(config_for(synthetic), "preview")
    with pytest.raises(ValueError, match="mode='export'"):
        export_mod.save(result, Path("."), name="nope")


# --------------------------------------------------------------------------- #
# paleta (cor por glifo)
# --------------------------------------------------------------------------- #
#: (fonte -> tinta). A fixture sintetica e figura escura sobre fundo claro com
#: um vestido vermelho; mandamos o escuro para verde puro e o vermelho para
#: azul puro, cores que NAO existem em lugar nenhum do caminho normal.
_STOPS = (
    ("#202020", "#00FF00"),
    ("#F0F0F0", "#00FF00"),
    ("#B03028", "#0000FF"),
)


def _pure(arr: np.ndarray, channel: int) -> int:
    """Pixels saturados so no canal dado (a tinta da paleta, sem mistura)."""
    other = [c for c in (0, 1, 2) if c != channel]
    return int(
        (
            (arr[:, :, channel] > 200)
            & (arr[:, :, other[0]] < 80)
            & (arr[:, :, other[1]] < 80)
        ).sum()
    )


def test_palette_paints_glyphs_from_the_source(synthetic):
    cfg = config_for(
        synthetic,
        accent={"enabled": False},
        palette={"enabled": True, "stops": _STOPS},
    )
    arr = np.asarray(engine.render_result(cfg, "preview").image.convert("RGB"))
    assert _pure(arr, 1) > 200, "a tinta da paleta (verde) nao apareceu"
    assert _pure(arr, 2) > 50, "o stop do vestido (azul) nao apareceu"

    # desligada, nenhuma das duas cores existe
    off = np.asarray(
        engine.render_result(
            config_for(synthetic, palette={"enabled": False, "stops": _STOPS}),
            "preview",
        ).image.convert("RGB")
    )
    assert _pure(off, 1) == 0 and _pure(off, 2) == 0


def test_palette_wins_over_accent(synthetic):
    """Com a paleta ligada, o accent nao pinta nada — ela cobre o caso geral."""
    cfg = config_for(
        synthetic,
        accent={"enabled": True, "color": "#FF00FF"},
        palette={"enabled": True, "stops": _STOPS},
    )
    arr = np.asarray(engine.render_result(cfg, "preview").image.convert("RGB"))
    magenta = (
        (arr[:, :, 0] > 200) & (arr[:, :, 1] < 80) & (arr[:, :, 2] > 200)
    ).sum()
    assert magenta == 0, "o accent vazou por cima da paleta"


def test_palette_matching_keeps_edges_neutral():
    """O motivo de `value_weight`: cinza-medio nao pode virar verde-oliva.

    Um pixel de anti-aliasing entre traco preto e papel creme cai em ~(120,116,
    100). Em RGB puro (value_weight=1) ele resolve como o verde-oliva do cartaz
    do turnstile; com o default (0.25) ele resolve como neutro.
    """
    from typo import palette as palette_mod

    stops = np.array([(2, 2, 2), (239, 230, 199), (132, 178, 85)], dtype=float)
    edge = np.array([[120.0, 116.0, 100.0]])

    def nearest(weight: float) -> int:
        f = palette_mod.features(edge, weight)
        s = palette_mod.features(stops, weight)
        return int(((f[:, None, :] - s[None, :, :]) ** 2).sum(axis=2).argmin())

    assert nearest(1.0) == 2, "premissa do teste mudou: em RGB puro dava verde"
    assert nearest(0.25) in (0, 1), "o default deixou a borda sortear cor"


def test_palette_enabled_without_stops_is_an_error(synthetic):
    with pytest.raises(ValueError, match="palette.stops"):
        config_for(synthetic, palette={"enabled": True}).validate()


def test_palette_chips_show_only_the_colours(synthetic):
    """A fileira do cabecalho mostra as cores, nao os neutros da tabela."""
    scene_palette = engine.palette_mod.build(
        engine.prepare(synthetic["image"], None, 60, 60, 30),
        RenderConfig().merge({"palette": {"enabled": True, "stops": _STOPS}}).palette,
    )
    chips = engine._chip_colors(scene_palette)
    assert chips == [(0, 255, 0), (0, 0, 255)], chips
    assert engine._chip_colors(None) is None


# --------------------------------------------------------------------------- #
# display (letras gigantes / rotulo invertido)
# --------------------------------------------------------------------------- #
_DISPLAY_DPI = 30


def _mark(**over) -> dict:
    base = {"text": "T", "size_cm": 3, "x_cm": 2, "y_cm": 2, "color": "#000000"}
    base.update(over)
    return base


def _display_cfg(synthetic: dict, *marks: dict) -> RenderConfig:
    return config_for(
        synthetic,
        page={"dpi_export": _DISPLAY_DPI},
        display={"enabled": True, "marks": list(marks)},
    )


def _dark(arr: np.ndarray) -> np.ndarray:
    return arr.min(axis=2) < 128


def test_display_positions_by_ink_bbox(synthetic):
    """x_cm/y_cm e onde a TINTA comeca, medido da borda do `anchor`."""
    from typo.config import Scale

    s = Scale(_DISPLAY_DPI)
    res = engine.render_result(_display_cfg(synthetic, _mark()), "export")
    assert res.stats["display_marks"] == 1
    dark = _dark(np.asarray(res.image))
    # a marca vive na margem branca do topo (arte comeca a 7cm da esquerda,
    # 13cm do topo), entao o canto superior esquerdo tem so ela
    corner = dark[: int(s.cm(10)), : int(s.cm(6))]
    ys, xs = np.nonzero(corner)
    assert len(xs), "a marca nao desenhou nada"
    assert abs(int(xs.min()) - round(s.cm(2))) <= 2, int(xs.min())
    assert abs(int(ys.min()) - round(s.cm(2))) <= 2, int(ys.min())


def test_display_negative_inset_bleeds_off_the_page(synthetic):
    """anchor 'rb' + recuo negativo sangra pela borda direita/inferior."""
    res = engine.render_result(
        _display_cfg(synthetic, _mark(anchor="rb", x_cm=-3, y_cm=-3, size_cm=8)),
        "export",
    )
    dark = _dark(np.asarray(res.image))
    assert dark[:, -1].any(), "nada tocou a ultima coluna"
    assert dark[-1, :].any(), "nada tocou a ultima linha"


def test_display_layers_differ_and_are_counted(synthetic):
    """A mesma marca antes e depois da passada de letras nao da a mesma pagina.

    Com tinta clara a diferenca e mensuravel: `over` chapa a letra por cima e
    apaga a malha embaixo dela; `under` deixa os glifos por cima da letra.
    """
    light = _mark(text="O", size_cm=25, anchor="cc", x_cm=0, y_cm=0, color="#CCCCCC")
    over = engine.render_result(
        _display_cfg(synthetic, {**light, "layer": "over"}), "export"
    )
    under = engine.render_result(
        _display_cfg(synthetic, {**light, "layer": "under"}), "export"
    )
    assert over.stats["display_marks"] == under.stats["display_marks"] == 1
    assert not np.array_equal(np.asarray(over.image), np.asarray(under.image))
    assert _dark(np.asarray(under.image)).sum() > _dark(np.asarray(over.image)).sum()


def test_display_disabled_changes_nothing(synthetic):
    res = engine.render_result(
        config_for(
            synthetic,
            page={"dpi_export": _DISPLAY_DPI},
            display={"marks": [_mark()]},  # enabled fica false
        ),
        "export",
    )
    plain = engine.render_result(
        config_for(synthetic, page={"dpi_export": _DISPLAY_DPI}), "export"
    )
    assert res.stats["display_marks"] == 0
    assert np.array_equal(np.asarray(res.image), np.asarray(plain.image))


def test_display_box_paints_a_reversed_label(synthetic):
    """Com `box`, o texto sai na cor do fundo dentro de um retangulo de tinta."""
    res = engine.render_result(
        _display_cfg(
            synthetic,
            {"text": "OBRA\nAUTOR", "size_mm": 20, "x_cm": 1, "y_cm": 1, "box": True},
        ),
        "export",
    )
    arr = np.asarray(res.image)
    from typo.config import Scale

    s = Scale(_DISPLAY_DPI)
    label = arr[: int(s.cm(8)), : int(s.cm(6))]
    assert _dark(label).any(), "a caixa nao pintou"
    # dentro da mancha da caixa tem que haver papel (as letras vazadas)
    ys, xs = np.nonzero(_dark(label))
    inside = label[ys.min() : ys.max() + 1, xs.min() : xs.max() + 1]
    assert (inside.min(axis=2) > 200).any(), "a caixa saiu chapada, sem texto vazado"


@pytest.mark.parametrize(
    "mark, message",
    [
        ({"text": "T", "size_cm": 3, "tamanho": 9}, "desconhecidas"),
        ({"text": "T"}, "size_cm"),
        ({"text": "T", "size_cm": 3, "size_mm": 30}, "size_cm"),
        ({"text": "", "size_cm": 3}, "vazio"),
        ({"text": "T", "size_cm": 3, "anchor": "xx"}, "anchor"),
        ({"text": "T", "size_cm": 3, "layer": "meio"}, "layer"),
        ({"text": "T", "size_cm": 3, "weight": "gordo"}, "weight"),
        ({"text": "T", "size_cm": 3, "color": "#ZZZ"}, "hex"),
    ],
)
def test_display_marks_reject_bad_input(synthetic, mark, message):
    with pytest.raises(ValueError, match=message):
        _display_cfg(synthetic, mark).validate()


def test_display_variation_error_is_explicit():
    """Instancia inexistente falha dizendo o que a fonte tem (ou que e estatica)."""
    from typo import display as display_mod
    from typo.fonts import resolve_family

    dejavu = resolve_family("DejaVu Sans").regular
    with pytest.raises(ValueError, match="variation"):
        display_mod.load_font(dejavu, 20, "Ultra Wide")


# --------------------------------------------------------------------------- #
# config / projetos
# --------------------------------------------------------------------------- #
def test_merge_is_deep_and_rejects_unknown_fields():
    cfg = RenderConfig()
    merged = cfg.merge({"font": {"base_line_mm": 4.0}})
    assert merged.font.base_line_mm == 4.0
    assert merged.font.size_gamma == cfg.font.size_gamma
    assert cfg.font.base_line_mm == 3.5, "merge nao pode mutar o original"
    with pytest.raises(ValueError, match="desconhecidos"):
        cfg.merge({"font": {"tamanho": 4.0}})


def test_text_modes(synthetic):
    from typo.config import TextCfg
    from typo.text_source import build_stream, tokenize

    lines = ["Vem, Magalenha Rojão", "Traz a lenha"]
    assert tokenize(lines, "phrases") == lines
    assert tokenize(lines, "words")[:3] == ["Vem,", "Magalenha", "Rojão"]
    assert " " not in tokenize(lines, "chars")

    chars = build_stream(TextCfg(text_path=synthetic["text"], mode="chars", repeat=2))
    assert " " not in chars
    words = build_stream(TextCfg(text_path=synthetic["text"], mode="words", repeat=2))
    assert " " in words


def test_from_project_shortcut():
    cfg = RenderConfig.from_project(str(REPO / "projects" / "demo" / "project.yaml"))
    assert cfg.name == "demo"
    assert Path(cfg.source.image_path).is_file()
    assert cfg.page.dpi_export == 96


def test_validate_reports_missing_paths():
    with pytest.raises(ValueError, match="image_path"):
        RenderConfig().validate()


def test_presets_available():
    assert "magalenha" in presets.names()
    assert presets.get("magalenha").font.base_line_mm == 3.5
    assert presets.get("halftone").mask.enabled is False


def test_scaffold_and_load_project(tmp_path, synthetic):
    Project.scaffold("teste", root=tmp_path)
    assert list_projects(tmp_path) == ["teste"]
    yaml_path = tmp_path / "teste" / "project.yaml"
    text = yaml_path.read_text(encoding="utf-8").replace(
        "refs/COLOQUE_A_IMAGEM_AQUI.png", synthetic["image"]
    ).replace("text/teste.txt", synthetic["text"])
    yaml_path.write_text(text, encoding="utf-8")

    cfg = load_project("teste", root=tmp_path).config()
    assert cfg.name == "teste"
    assert cfg.source.crop is None
    assert cfg.page.art_height_cm == 88


def test_turnstile_project_yaml_is_coherent():
    """A releitura do cartaz do Lucas Pereira: paleta ligada, accent fora."""
    project = load_project(str(REPO / "projects" / "turnstile"))
    cfg = project.config()
    assert Path(cfg.source.image_path).is_file()
    assert Path(cfg.text.text_path).is_file()
    assert cfg.palette.enabled and not cfg.accent.enabled
    assert len(cfg.palette.stops) == 12
    # os stops tem que estar congelados como tuplas, senao a chave de cache
    # da cena muda de repr entre um load e outro
    assert all(isinstance(s, tuple) and len(s) == 2 for s in cfg.palette.stops)
    assert cfg.font.size_gamma < 1.0, "gamma abaixo de 1 e proposital, ver notes"


def test_magalenha_project_yaml_is_coherent():
    project = load_project(str(REPO / "projects" / "magalenha"))
    data = project.data
    assert data["source"]["crop"] == [600, 55, 1420, 782]
    assert data["page"]["dpi_export"] == 150
    assert Path(project.resolve(data["text"]["file"])).is_file()
    assert data["style_preset"] == "magalenha"


# --------------------------------------------------------------------------- #
# regressao pesada (opt-in)
# --------------------------------------------------------------------------- #
@pytest.mark.skipif(
    os.environ.get("TYPO_PARITY") != "1",
    reason="regressao pesada (~50s): rode com TYPO_PARITY=1",
)
def test_bit_parity_with_print_v4(tmp_path):
    """Roda o print_v4.py original e o motor lado a lado a 150 dpi.

    Tem que dar diferenca ZERO. E o teste que garante que o refactor nao
    mexeu no algoritmo.
    """
    script = REPO / "print_v4.py"
    if not script.is_file():
        pytest.skip("print_v4.py nao esta no repo")

    inner = Image.open(make_reference_image(tmp_path / "inner.png"))
    full = Image.new("RGB", (1420, 782), (255, 255, 255))
    full.paste(inner, (600, 55))
    full.save(tmp_path / "ref_full.png")

    fonts_dir = REPO / "fonts"
    src = script.read_text(encoding="utf-8")
    for old, new in (
        ('SRC="/mnt/user-data/uploads/A5613A3C-E617-4518-9A6A-F1AE698EFB70.png"',
         f'SRC=r"{tmp_path / "ref_full.png"}"'),
        ('FB="/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf"',
         f'FB=r"{fonts_dir / "DejaVuSans-Bold.ttf"}"'),
        ('FR="/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed.ttf"',
         f'FR=r"{fonts_dir / "DejaVuSans.ttf"}"'),
        ('png=f"/home/claude/quadro/magalenha_v3_{TAG}.png"; '
         'pdf=f"/home/claude/quadro/magalenha_v3_{TAG}.pdf"',
         f'png=r"{tmp_path / "orig.png"}"; pdf=r"{tmp_path / "orig.pdf"}"'),
    ):
        assert old in src, f"print_v4.py mudou; nao achei: {old[:50]}"
        src = src.replace(old, new)
    patched = tmp_path / "print_v4_ref.py"
    patched.write_text(src, encoding="utf-8")

    import subprocess

    subprocess.run([sys.executable, str(patched), "150"], check=True)

    cfg = RenderConfig().merge(
        {
            "source": {
                "image_path": str(tmp_path / "ref_full.png"),
                "crop": (600, 55, 1420, 782),
            },
            "text": {"text_path": str(REPO / "projects/magalenha/text/magalenha.txt")},
            "font": {"family": "DejaVu Sans"},
        }
    )
    mine = engine.render_result(cfg, "export").image
    original = np.asarray(Image.open(tmp_path / "orig.png").convert("RGB"))
    assert np.array_equal(np.asarray(mine), original), "o refactor divergiu do print_v4.py"
