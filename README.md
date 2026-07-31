# typo

Gerador local de arte tipográfica: desenha uma imagem inteira com **letras**,
em tamanho e peso proporcionais à escuridão local, seguindo um fluxo curvado.
Exporta PDF no tamanho físico de impressão.

É a refatoração do `print_v4.py` num app reutilizável — mesmo algoritmo,
agora com sliders, projetos e export configurável.

## Instalação

```bash
python -m venv .venv
```

```bash
.venv/Scripts/python.exe -m pip install -e ".[dev]"
```

(macOS/Linux: `.venv/bin/pip install -e ".[dev]"`)

## Uso

**Interface** — sobe em `http://127.0.0.1:7860`:

```bash
.venv/Scripts/python.exe -m app.ui
```

Escolha o projeto, mexa nos sliders, clique em **Preview** (~1,5 s) e, no fim,
em **Exportar PDF**. Os botões **Ver máscara** e **Ver crop** mostram overlays
de diagnóstico — são eles que ajudam a afinar uma referência nova.

**Headless**:

```bash
.venv/Scripts/python.exe scripts/render.py projects/magalenha/project.yaml
```

**Projeto novo**:

```bash
.venv/Scripts/python.exe scripts/new_project.py meu-poster
```

Depois: jogue a imagem em `projects/meu-poster/refs/`, o texto em `text/`,
ajuste `source.image` e `source.crop` no `project.yaml`.

## Controles

| Controle | Campo | Efeito |
|---|---|---|
| Fonte | `font.family` | troca a tipografia |
| Tamanho da fonte | `font.base_line_mm` | escala geral das letras / densidade |
| Espessura | `font.bold_threshold` (invertido) | quantos glifos saem em bold |
| Flexibilidade das linhas | `flow.flex` | curvatura da ondulação + rotação |
| Posição das letras | `layout.advance_factor`, `layout.jitter_px` | espaçamento e deslocamento |
| Divergência de tamanho | `font.size_gamma` | contraste entre letras grandes e pequenas |
| Densidade *(avançado)* | `mask.interior_fill_min` | preenchimento do corpo da figura |
| Paisagem *(avançado)* | `landscape.*` | intensidade do contorno de fundo |
| Accent *(avançado)* | `accent.*` | cor de destaque e região |
| Máscara *(avançado)* | `mask.enabled`, `mask.lum_threshold` | isolar figuras vs imagem toda |

Guia de afinação para uma referência nova:
[`skills/typographic-poster/SKILL.md`](skills/typographic-poster/SKILL.md).

## Estrutura de um projeto

```
projects/<nome>/
├── project.yaml   conceito, caminhos, tamanho de página, overrides de estilo
├── refs/          imagens de referência
├── text/          .txt com a letra/trecho
└── output/        PNG/PDF gerados
```

## Testes

```bash
.venv/Scripts/python.exe -m pytest -q
```

A regressão pesada compara o motor com o `print_v4.py` original pixel a pixel
(deve dar diferença **zero**):

```bash
TYPO_PARITY=1 .venv/Scripts/python.exe -m pytest -k parity -q
```

## Notas

- Offline em runtime: nenhuma chamada de rede para gerar arte.
- Uso pessoal. Você é responsável pelos direitos das imagens e textos que
  alimentar a ferramenta.
- A pasta `projects/magalenha/refs/` está vazia — a foto original não veio junto
  com o script. Veja `CLAUDE.md` § Estado.

## Landing page (`site/`)

Página de divulgação da marca **Onde Moram as Palavras** — vanilla JS + Vite,
mobile-first, sem backend (encomenda via WhatsApp). Sai em quatro idiomas, uma
página por idioma gerada na build (`/`, `/en/`, `/es/`, `/it/`) — os títulos das
obras ficam em português, que é como estão impressos no pôster. Ver
[`site/README.md`](site/README.md) para rodar, configurar e publicar.
