"""Interface Gradio — sliders de estilo, preview rapido e export em PDF.

Roda 100% local. A UI nao tem logica de render propria: ela so monta uma
`RenderConfig` (a mesma que o CLI usa) e chama `typo.engine.render`.

    python -m app.ui        # ou: typo-ui
"""
from __future__ import annotations

import os
import traceback

os.environ.setdefault("GRADIO_ANALYTICS_ENABLED", "False")

import gradio as gr  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

from typo import engine, export as export_mod, fonts  # noqa: E402
from typo.config import RenderConfig, hex_to_rgb  # noqa: E402
from typo.image_prep import crop_size, open_source, prepare  # noqa: E402
from typo.project import PROJECTS_DIR, Project, list_projects, load_project  # noqa: E402

OVERLAY_MAX_PX = 900

#: ordem canonica dos controles. Os handlers recebem *vals nesta ordem e
#: `gr.update` de volta na mesma ordem — sem isso a UI sai de sincronia.
KEYS = [
    "project",
    "font_family",
    "base_line_mm",
    "espessura",
    "flex",
    "advance_factor",
    "jitter_px",
    "size_gamma",
    "size_min_mm",
    "size_max_ratio",
    "interior_fill_min",
    "landscape_enabled",
    "edge_gain",
    "shade_dark",
    "shade_light",
    "accent_enabled",
    "accent_color",
    "mask_enabled",
    "lum_threshold",
    "text_mode",
    "repeat",
    "title",
    "subtitle",
    "footer",
    "page_mode",
    "art_height_cm",
    "width_cm",
    "height_cm",
    "margin_top_cm",
    "margin_bottom_cm",
    "margin_side_cm",
    "dpi_export",
    "preview_max_px",
]


# --------------------------------------------------------------------------- #
# config <-> controles
# --------------------------------------------------------------------------- #
def config_to_values(cfg: RenderConfig, project: str) -> dict:
    return {
        "project": project,
        "font_family": cfg.font.family,
        "base_line_mm": cfg.font.base_line_mm,
        # "Espessura" e o inverso do limiar de bold: mais espesso = limiar menor
        "espessura": round(1.0 - cfg.font.bold_threshold, 4),
        "flex": cfg.flow.flex,
        "advance_factor": cfg.layout.advance_factor,
        "jitter_px": cfg.layout.jitter_px,
        "size_gamma": cfg.font.size_gamma,
        "size_min_mm": cfg.font.size_min_mm,
        "size_max_ratio": cfg.font.size_max_ratio,
        "interior_fill_min": cfg.mask.interior_fill_min,
        "landscape_enabled": cfg.landscape.enabled,
        "edge_gain": cfg.landscape.edge_gain,
        "shade_dark": cfg.landscape.shade_dark,
        "shade_light": cfg.landscape.shade_light,
        "accent_enabled": cfg.accent.enabled,
        "accent_color": cfg.accent.color,
        "mask_enabled": cfg.mask.enabled,
        "lum_threshold": cfg.mask.lum_threshold,
        "text_mode": cfg.text.mode,
        "repeat": cfg.text.repeat,
        "title": cfg.text_blocks.title,
        "subtitle": cfg.text_blocks.subtitle,
        "footer": cfg.text_blocks.footer,
        "page_mode": cfg.page.mode,
        "art_height_cm": cfg.page.art_height_cm,
        "width_cm": cfg.page.width_cm or 0.0,
        "height_cm": cfg.page.height_cm or 0.0,
        "margin_top_cm": cfg.page.margin_top_cm,
        "margin_bottom_cm": cfg.page.margin_bottom_cm,
        "margin_side_cm": cfg.page.margin_side_cm,
        "dpi_export": cfg.page.dpi_export,
        "preview_max_px": cfg.page.preview_max_px,
    }


def values_to_config(vals: dict) -> tuple[RenderConfig, Project]:
    """Controles -> RenderConfig (partindo sempre do project.yaml selecionado)."""
    project = load_project(str(vals["project"]))
    cfg = project.config()
    overrides = {
        "font": {
            "family": vals["font_family"],
            "base_line_mm": float(vals["base_line_mm"]),
            "bold_threshold": 1.0 - float(vals["espessura"]),
            "size_gamma": float(vals["size_gamma"]),
            "size_min_mm": float(vals["size_min_mm"]),
            "size_max_ratio": float(vals["size_max_ratio"]),
        },
        "flow": {"flex": float(vals["flex"])},
        "layout": {
            "advance_factor": float(vals["advance_factor"]),
            "jitter_px": float(vals["jitter_px"]),
        },
        "mask": {
            "enabled": bool(vals["mask_enabled"]),
            "lum_threshold": float(vals["lum_threshold"]),
            "interior_fill_min": float(vals["interior_fill_min"]),
        },
        "landscape": {
            "enabled": bool(vals["landscape_enabled"]),
            "edge_gain": float(vals["edge_gain"]),
            "shade_dark": int(vals["shade_dark"]),
            "shade_light": int(vals["shade_light"]),
        },
        "accent": {
            "enabled": bool(vals["accent_enabled"]),
            "color": _as_hex(vals["accent_color"]),
        },
        "text": {"mode": vals["text_mode"], "repeat": int(vals["repeat"])},
        "text_blocks": {
            "title": vals["title"],
            "subtitle": vals["subtitle"],
            "footer": vals["footer"],
        },
        "page": {
            "mode": vals["page_mode"],
            "art_height_cm": float(vals["art_height_cm"]),
            "margin_top_cm": float(vals["margin_top_cm"]),
            "margin_bottom_cm": float(vals["margin_bottom_cm"]),
            "margin_side_cm": float(vals["margin_side_cm"]),
            "dpi_export": int(vals["dpi_export"]),
            "preview_max_px": int(vals["preview_max_px"]),
        },
    }
    if vals["page_mode"] == "fixed":
        overrides["page"]["width_cm"] = float(vals["width_cm"]) or None
        overrides["page"]["height_cm"] = float(vals["height_cm"]) or None
    return cfg.merge(overrides).validate(), project


def _as_hex(value) -> str:
    """gr.ColorPicker devolve '#rrggbb' ou 'rgba(r, g, b, a)'."""
    s = str(value).strip()
    if s.startswith("rgb"):
        nums = [float(n) for n in s[s.find("(") + 1 : s.find(")")].split(",")[:3]]
        return "#{:02X}{:02X}{:02X}".format(*(int(round(n)) for n in nums))
    return s


# --------------------------------------------------------------------------- #
# overlays de diagnostico
# --------------------------------------------------------------------------- #
def _fit(img: Image.Image, max_px: int = OVERLAY_MAX_PX) -> Image.Image:
    if max(img.size) <= max_px:
        return img
    ratio = max_px / max(img.size)
    return img.resize((max(1, int(img.width * ratio)), max(1, int(img.height * ratio))), Image.LANCZOS)


def mask_overlay(cfg: RenderConfig) -> Image.Image:
    """Figuras em cinza, contorno da mascara em vermelho, accent na cor, faixa
    da paisagem em azul claro. E o que ajuda a afinar `lum_threshold` e o crop.
    """
    crop_w, crop_h = crop_size(cfg.source.image_path, cfg.source.crop)
    dpi, _ = cfg.preview_dpi(crop_w, crop_h)
    art_w, art_h = cfg.art_size(crop_w, crop_h, dpi)
    scene = engine.build_scene(cfg, art_w, art_h, dpi)

    base = (np.asarray(scene.prep.rgb) * 0.35 + 255 * 0.65).astype(np.uint8)
    out = base.copy()
    m = scene.mask_result.mask
    out[m] = (out[m] * 0.45).astype(np.uint8)
    if scene.landscape_fields is not None:
        band = scene.landscape_fields.window.arr > 0.05
        out[band & ~m] = (
            out[band & ~m] * 0.75 + np.array([60, 110, 200]) * 0.25
        ).astype(np.uint8)
    if scene.mask_result.accent.any():
        out[scene.mask_result.accent] = np.array(hex_to_rgb(cfg.accent.color), np.uint8)
    # contorno da mascara
    edge = m ^ np.roll(m, 1, axis=0)
    edge |= m ^ np.roll(m, 1, axis=1)
    out[edge] = np.array([220, 20, 20], np.uint8)
    return _fit(Image.fromarray(out))


#: cores de diagnostico das regioes de texto, na ordem em que aparecem no YAML
_REGION_COLORS = (
    (220, 40, 40), (40, 120, 220), (40, 170, 90), (230, 150, 20),
    (170, 60, 200), (0, 170, 190), (220, 90, 140), (130, 130, 60),
)


def regions_overlay(cfg: RenderConfig) -> Image.Image:
    """Cada regiao de `text.regions` numa cor, sobre a imagem fonte.

    E o unico jeito pratico de conferir poligono escrito a mao no YAML — a
    fracao vira px so na hora do render.
    """
    from typo import regions as regions_mod

    crop_w, crop_h = crop_size(cfg.source.image_path, cfg.source.crop)
    dpi, _ = cfg.preview_dpi(crop_w, crop_h)
    art_w, art_h = cfg.art_size(crop_w, crop_h, dpi)
    prep = prepare(cfg.source.image_path, cfg.source.crop, art_w, art_h, dpi)

    out = (np.asarray(prep.rgb) * 0.45 + 255 * 0.55).astype(np.uint8)
    field = regions_mod.build_field(cfg.text, art_w, art_h)
    if field.index is not None:
        idx = np.frombuffer(field.index, dtype=np.uint8).reshape(art_h, art_w)
        for i in range(1, len(field.streams)):
            sel = idx == i
            if not sel.any():
                continue
            tint = np.array(_REGION_COLORS[(i - 1) % len(_REGION_COLORS)], float)
            out[sel] = (out[sel] * 0.55 + tint * 0.45).astype(np.uint8)
    return _fit(Image.fromarray(out))


def crop_overlay(cfg: RenderConfig) -> Image.Image:
    """Imagem inteira com o retangulo do crop desenhado."""
    full = open_source(cfg.source.image_path, None)
    img = full.convert("RGB").copy()
    if cfg.source.crop is not None:
        d = ImageDraw.Draw(img)
        width = max(2, int(min(img.size) * 0.004))
        d.rectangle(list(cfg.source.crop), outline=(220, 20, 20), width=width)
    return _fit(img)


# --------------------------------------------------------------------------- #
# handlers
# --------------------------------------------------------------------------- #
def _vals(args) -> dict:
    return dict(zip(KEYS, args))


def _error(exc: Exception) -> str:
    return f"**Erro:** {exc}\n\n```\n{traceback.format_exc(limit=3)}\n```"


def do_preview(*args):
    vals = _vals(args)
    try:
        cfg, _project = values_to_config(vals)
        result = engine.render_result(cfg, "preview")
        return result.image, result.summary()
    except Exception as exc:  # noqa: BLE001 — a UI mostra o erro em vez de morrer
        return gr.update(), _error(exc)


def do_export(*args):
    vals = _vals(args)
    try:
        cfg, project = values_to_config(vals)
        result = engine.render_result(cfg, "export")
        paths = export_mod.save(result, project.output_dir, name=project.name)
        w_cm, h_cm = export_mod.pdf_page_cm(paths.pdf)
        msg = (
            f"{result.summary()}\n\n"
            f"- PNG: `{paths.png}`\n"
            f"- PDF: `{paths.pdf}` — mediabox **{w_cm:.1f} x {h_cm:.1f} cm**"
        )
        return _fit(result.image), msg, str(paths.pdf)
    except Exception as exc:  # noqa: BLE001
        return gr.update(), _error(exc), gr.update()


def do_mask_overlay(*args):
    vals = _vals(args)
    try:
        cfg, _ = values_to_config(vals)
        return mask_overlay(cfg), "Mascara: cinza = figura, vermelho = contorno, azul = faixa da paisagem, cor = accent."
    except Exception as exc:  # noqa: BLE001
        return gr.update(), _error(exc)


def do_regions_overlay(*args):
    vals = _vals(args)
    try:
        cfg, _ = values_to_config(vals)
        names = [n for n in cfg.text.regions] if cfg.text.regions else []
        if not names:
            return regions_overlay(cfg), "Este projeto nao usa `text.regions` (um stream so na arte inteira)."
        labels = ", ".join(
            f"{i}. {r.get('name') or '?'}" for i, r in enumerate(cfg.text.regions, 1)
        )
        return regions_overlay(cfg), f"Regioes de texto (ordem de pintura): {labels}."
    except Exception as exc:  # noqa: BLE001
        return gr.update(), _error(exc)


def do_crop_overlay(*args):
    vals = _vals(args)
    try:
        cfg, _ = values_to_config(vals)
        crop = cfg.source.crop
        return crop_overlay(cfg), f"Crop atual: `{crop}` (edite em source.crop no project.yaml)."
    except Exception as exc:  # noqa: BLE001
        return gr.update(), _error(exc)


def do_load_project(project: str):
    """Troca de projeto: recarrega ref + texto + defaults do project.yaml."""
    try:
        p = load_project(str(project))
        vals = config_to_values(p.config(), p.name)
        status = f"Projeto **{p.name}** carregado.\n\n{p.notes}" if p.notes else f"Projeto **{p.name}** carregado."
    except Exception as exc:  # noqa: BLE001
        return [gr.update() for _ in KEYS] + [_error(exc)]
    return [gr.update(value=vals[k]) for k in KEYS] + [status]


# --------------------------------------------------------------------------- #
# layout
# --------------------------------------------------------------------------- #
def build_ui() -> gr.Blocks:
    projects = list_projects()
    if not projects:
        raise SystemExit(
            f"nenhum projeto em {PROJECTS_DIR}.\n"
            "Crie um com: python scripts/new_project.py <nome>"
        )
    initial_name = "magalenha" if "magalenha" in projects else projects[0]
    try:
        cfg0 = load_project(initial_name).config()
    except Exception:
        cfg0 = RenderConfig()
    v0 = config_to_values(cfg0, initial_name)

    families = fonts.available_families()
    if v0["font_family"] not in families:
        families = [v0["font_family"], *families]

    with gr.Blocks(title="typo — poster tipografico", analytics_enabled=False) as demo:
        gr.Markdown(
            "## typo — gerador de arte tipografica\n"
            "Ajuste os controles, gere um **Preview** rapido e só no fim **Exporte o PDF** "
            "em tamanho de impressao."
        )
        c: dict[str, gr.components.Component] = {}
        with gr.Row():
            with gr.Column(scale=4):
                with gr.Row():
                    c["project"] = gr.Dropdown(
                        projects, value=initial_name, label="Projeto", scale=3
                    )
                    load_btn = gr.Button("Recarregar", scale=1)

                c["font_family"] = gr.Dropdown(
                    families, value=v0["font_family"], label="Fonte", filterable=True
                )
                c["base_line_mm"] = gr.Slider(
                    2.0, 6.0, value=v0["base_line_mm"], step=0.1,
                    label="Tamanho da fonte (mm de altura de linha)",
                )
                c["espessura"] = gr.Slider(
                    0.0, 1.0, value=v0["espessura"], step=0.01,
                    label="Espessura (maior = mais glifos em bold)",
                )
                c["flex"] = gr.Slider(
                    0.0, 1.5, value=v0["flex"], step=0.01,
                    label="Flexibilidade das linhas (ondulacao + rotacao)",
                )
                with gr.Row():
                    c["advance_factor"] = gr.Slider(
                        0.80, 1.20, value=v0["advance_factor"], step=0.01,
                        label="Posicao: espacamento",
                    )
                    c["jitter_px"] = gr.Slider(
                        0.0, 3.0, value=v0["jitter_px"], step=0.1,
                        label="Posicao: deslocamento",
                    )
                c["size_gamma"] = gr.Slider(
                    0.8, 2.5, value=v0["size_gamma"], step=0.05,
                    label="Divergencia de tamanho (contraste claro/escuro)",
                )

                with gr.Accordion("Avancado", open=False):
                    with gr.Row():
                        c["size_min_mm"] = gr.Slider(
                            0.5, 4.0, value=v0["size_min_mm"], step=0.1, label="Tamanho minimo (mm)"
                        )
                        c["size_max_ratio"] = gr.Slider(
                            1.0, 3.0, value=v0["size_max_ratio"], step=0.05, label="Tamanho maximo (x linha)"
                        )
                    c["interior_fill_min"] = gr.Slider(
                        0.15, 0.6, value=v0["interior_fill_min"], step=0.01,
                        label="Densidade (preenchimento minimo dentro da figura)",
                    )
                    gr.Markdown("**Mascara**")
                    with gr.Row():
                        c["mask_enabled"] = gr.Checkbox(
                            value=v0["mask_enabled"], label="Isolar figuras"
                        )
                        c["lum_threshold"] = gr.Slider(
                            0.2, 0.9, value=v0["lum_threshold"], step=0.01, label="Limiar de luminancia"
                        )
                    gr.Markdown("**Paisagem**")
                    with gr.Row():
                        c["landscape_enabled"] = gr.Checkbox(
                            value=v0["landscape_enabled"], label="Ligada"
                        )
                        c["edge_gain"] = gr.Slider(
                            1.0, 15.0, value=v0["edge_gain"], step=0.1, label="Intensidade do contorno"
                        )
                    with gr.Row():
                        c["shade_dark"] = gr.Slider(
                            0, 255, value=v0["shade_dark"], step=1, label="Cinza forte"
                        )
                        c["shade_light"] = gr.Slider(
                            0, 255, value=v0["shade_light"], step=1, label="Cinza fraco"
                        )
                    gr.Markdown("**Accent**")
                    with gr.Row():
                        c["accent_enabled"] = gr.Checkbox(
                            value=v0["accent_enabled"], label="Ligado"
                        )
                        c["accent_color"] = gr.ColorPicker(
                            value=v0["accent_color"], label="Cor"
                        )
                    gr.Markdown("**Texto**")
                    with gr.Row():
                        c["text_mode"] = gr.Dropdown(
                            ["phrases", "words", "chars"], value=v0["text_mode"], label="Tokenizacao"
                        )
                        c["repeat"] = gr.Number(
                            value=v0["repeat"], precision=0, label="Repeticoes"
                        )

                with gr.Accordion("Textos da pagina", open=False):
                    c["title"] = gr.Textbox(value=v0["title"], label="Titulo")
                    c["subtitle"] = gr.Textbox(value=v0["subtitle"], label="Subtitulo")
                    c["footer"] = gr.Textbox(value=v0["footer"], label="Rodape")

                with gr.Accordion("Pagina e export", open=False):
                    c["page_mode"] = gr.Radio(
                        ["from_art", "fixed"], value=v0["page_mode"], label="Modo"
                    )
                    with gr.Row():
                        c["art_height_cm"] = gr.Number(
                            value=v0["art_height_cm"], label="Altura da arte (cm)"
                        )
                        c["width_cm"] = gr.Number(
                            value=v0["width_cm"], label="Largura fixa (cm)"
                        )
                        c["height_cm"] = gr.Number(
                            value=v0["height_cm"], label="Altura fixa (cm)"
                        )
                    with gr.Row():
                        c["margin_top_cm"] = gr.Number(value=v0["margin_top_cm"], label="Margem topo")
                        c["margin_bottom_cm"] = gr.Number(value=v0["margin_bottom_cm"], label="Margem base")
                        c["margin_side_cm"] = gr.Number(value=v0["margin_side_cm"], label="Margem lateral")
                    with gr.Row():
                        c["dpi_export"] = gr.Number(
                            value=v0["dpi_export"], precision=0, label="DPI de export"
                        )
                        c["preview_max_px"] = gr.Number(
                            value=v0["preview_max_px"], precision=0, label="Preview (px max)"
                        )

            with gr.Column(scale=6):
                with gr.Row():
                    preview_btn = gr.Button("Preview", variant="primary")
                    export_btn = gr.Button("Exportar PDF", variant="secondary")
                    mask_btn = gr.Button("Ver mascara")
                    regions_btn = gr.Button("Ver regioes")
                    crop_btn = gr.Button("Ver crop")
                image = gr.Image(label="Resultado", type="pil", height=680)
                pdf_file = gr.File(label="PDF gerado", interactive=False)
                status = gr.Markdown("Pronto. Clique em **Preview**.")

        inputs = [c[k] for k in KEYS]
        preview_btn.click(do_preview, inputs=inputs, outputs=[image, status])
        export_btn.click(do_export, inputs=inputs, outputs=[image, status, pdf_file])
        mask_btn.click(do_mask_overlay, inputs=inputs, outputs=[image, status])
        regions_btn.click(do_regions_overlay, inputs=inputs, outputs=[image, status])
        crop_btn.click(do_crop_overlay, inputs=inputs, outputs=[image, status])

        outs = inputs + [status]
        load_btn.click(do_load_project, inputs=[c["project"]], outputs=outs)
        c["project"].change(do_load_project, inputs=[c["project"]], outputs=outs)

    return demo


def main() -> int:
    demo = build_ui()
    demo.launch(
        server_name=os.environ.get("TYPO_HOST", "127.0.0.1"),
        server_port=int(os.environ.get("TYPO_PORT", "7860")),
        share=False,
        inbrowser=os.environ.get("TYPO_OPEN_BROWSER", "1") == "1",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
