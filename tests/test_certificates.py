"""A contagem do certificado, contra o gabarito real: o e-mail de entrega.

`emails/entrega-emicida.html` afirma numeros especificos ("357x levanta",
"25 e meia voltas", "40.413 letras"). Se `compute_contagem` nao reproduzir
esses numeros a partir do `.txt` da obra, a formula esta errada — este e' o
teste de aceite, nao uma comparacao de snapshot.
"""
from __future__ import annotations

import sys
from pathlib import Path
from textwrap import dedent

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from typo.project import load_project  # noqa: E402

import build_certificates as bc  # noqa: E402

GABARITO = {
    "levanta": 357,
    "anda": 357,
    "vai": 357,
    "sonho": 102,
    "quem": 102,
    "sei": 102,
    "onde": 102,
    "somos": 77,
    "seguir": 77,
    "nossa": 77,
}
EMICIDA_GLYPHS = 40413  # site/src/data/works.json, slug emicida


@pytest.fixture(scope="module")
def emicida_cfg():
    return load_project("emicida").config()


@pytest.fixture(scope="module")
def contagem(emicida_cfg):
    return bc.compute_contagem(emicida_cfg, EMICIDA_GLYPHS, list(GABARITO))


def test_frases_e_voltas_batem_com_o_email(contagem):
    assert contagem["frases"] == 62
    assert round(contagem["voltas"], 1) == 25.5


def test_letras_bate_com_works_json(contagem):
    assert contagem["letras"] == EMICIDA_GLYPHS


def test_todas_as_dez_ocorrencias_batem_exatas(contagem):
    vezes = {r["palavra"]: r["vezes"] for r in contagem["ranking"]}
    for palavra, esperado in GABARITO.items():
        assert vezes[palavra] == esperado, f"{palavra}: calculado {vezes[palavra]}, gabarito {esperado}"


def test_heroi_e_a_primeira_palavra_declarada(contagem):
    assert contagem["heroi"] == {"palavra": "levanta", "vezes": 357}


def test_total_de_palavras_fica_proximo_do_email(contagem):
    """9.516 calculado vs 9.542 do e-mail — 0,27%, diferenca de definicao de
    'palavra' na borda da volta, nao erro de formula. Nao persiga os 26."""
    assert contagem["palavras"] == pytest.approx(9542, rel=0.01)


def test_contagem_e_deterministica(emicida_cfg):
    a = bc.compute_contagem(emicida_cfg, EMICIDA_GLYPHS, list(GABARITO))
    b = bc.compute_contagem(emicida_cfg, EMICIDA_GLYPHS, list(GABARITO))
    assert a == b


def test_palavra_ausente_do_texto_da_erro(emicida_cfg):
    with pytest.raises(bc.CertificateError, match="nao aparece no texto"):
        bc.compute_contagem(emicida_cfg, EMICIDA_GLYPHS, ["palavraqueninguemescreveu"])


class _FakeCfg:
    """Um RenderConfig minimo, so' com o que `compute_contagem` le, para
    exercitar o guard de `text.regions` sem depender de um project.yaml real
    com regioes configuradas."""

    def __init__(self, regions):
        self.text = type("T", (), {"regions": regions, "text_path": "", "mode": "phrases", "separator": "   "})()
        self.name = "fake"


def test_regions_da_erro_claro_em_vez_de_numero_errado():
    cfg = _FakeCfg(regions=({"name": "a"},))
    with pytest.raises(bc.CertificateError, match="text.regions"):
        bc.compute_contagem(cfg, 1000, ["qualquer"])


# --------------------------------------------------------------------------- #
# certificado.md — frontmatter + markdown minimo
# --------------------------------------------------------------------------- #
def test_certificado_md_exige_frontmatter(tmp_path):
    p = tmp_path / "certificado.md"
    p.write_text("so' um paragrafo, sem frontmatter", encoding="utf-8")
    with pytest.raises(bc.CertificateError, match="frontmatter"):
        bc.parse_certificado_md(p)


def test_certificado_md_aceita_frontmatter_vazio(tmp_path):
    """'---\\n---\\n' colado, sem chave nenhuma — o caso das obras sem
    contagem (magalenha, debret-antropofagia). Regressao: uma primeira versao
    deste parser (regex de bloco) nao casava esse caso."""
    p = tmp_path / "certificado.md"
    p.write_text("---\n---\n\nUm parágrafo qualquer.\n", encoding="utf-8")
    front, body = bc.parse_certificado_md(p)
    assert front == {}
    assert "Um parágrafo qualquer." in body


def test_certificado_md_parseia_frontmatter_e_corpo(tmp_path):
    p = tmp_path / "certificado.md"
    p.write_text(
        dedent(
            """\
            ---
            titulo: Teste
            palavras: [um, dois]
            ---

            Primeiro paragrafo com *itálico*.

            Segundo paragrafo.
            """
        ),
        encoding="utf-8",
    )
    front, body = bc.parse_certificado_md(p)
    assert front == {"titulo": "Teste", "palavras": ["um", "dois"]}
    assert "Primeiro paragrafo" in body


def test_md_to_html_escapa_e_converte_italico():
    html = bc.md_to_html("Isto tem <script> e *ênfase*.\n\nSegundo parágrafo.")
    assert "<script>" not in html  # escapado
    assert "&lt;script&gt;" in html
    assert "<em>ênfase</em>" in html
    assert html.count("<p>") == 2


def test_md_to_html_rejects_nothing_but_escapes_everything():
    html = bc.md_to_html("5 > 3 & 2 < 4")
    assert "&gt;" in html and "&amp;" in html and "&lt;" in html


# --------------------------------------------------------------------------- #
# build_one — obra sem certificado.md e' pulada, nao e' erro
# --------------------------------------------------------------------------- #
def test_obra_sem_certificado_md_e_pulada(monkeypatch, tmp_path):
    monkeypatch.setattr(bc, "PROJECTS_DIR", tmp_path)
    (tmp_path / "sem-carta").mkdir()
    assert bc.build_one("sem-carta", works={}) is None


def test_palavras_declaradas_sem_glyphs_da_erro_claro(monkeypatch, tmp_path):
    """A guarda que protege o caso magalenha: obra sem entrada em works.json
    (sem `glyphs`) mas cujo certificado.md pede uma secao de contagem tem que
    falhar alto — nao inventar um numero, nao ficar muda sobre o motivo."""
    monkeypatch.setattr(bc, "PROJECTS_DIR", tmp_path)
    work_dir = tmp_path / "obra-sem-works-json"
    work_dir.mkdir()
    (work_dir / "certificado.md").write_text(
        "---\npalavras: [teste]\n---\n\nUm parágrafo qualquer.\n", encoding="utf-8"
    )

    class _FakeProject:
        name = "obra-sem-works-json"

        def config(self):
            # o erro de glyphs ausente e' levantado ANTES de qualquer leitura
            # de cfg.text_blocks/art — None aqui prova que o caminho de fato
            # nao depende de uma config valida pra falhar
            return None

    monkeypatch.setattr(bc, "load_project", lambda slug: _FakeProject())
    with pytest.raises(bc.CertificateError, match="glyphs"):
        bc.build_one("obra-sem-works-json", works={})


def test_normalize_word_tira_acento_maiuscula_e_pontuacao():
    assert bc.normalize_word("É,") == "e"
    assert bc.normalize_word("Não!") == "nao"
    assert bc.normalize_word('"Sonho"') == "sonho"
