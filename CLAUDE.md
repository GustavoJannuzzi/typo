# CLAUDE.md — projeto **typo**

## O que é

App local que desenha uma imagem inteira usando **letras** (halftone tipográfico).
A partir de uma imagem de referência e de um texto (letra de música, trecho de
livro), o motor mede a escuridão local e desenha os caracteres em tamanho/peso
proporcionais, com as letras seguindo um fluxo curvado. Exporta PDF no tamanho
físico de impressão.

Roda 100% offline em runtime. Não há chamada de rede para gerar nada.

## Regra de ouro

`print_v4.py` (na raiz) é a **fonte da verdade do algoritmo**. Este repo é uma
**refatoração** dele, não uma reescrita.

- O preset `magalenha` (= os defaults da `RenderConfig`) reproduz o
  `print_v4.py` **bit a bit** a 150 dpi. Isso é verificado por
  `tests/test_smoke.py::test_bit_parity_with_print_v4`.
- Não "melhore" a matemática do halftone sem o Gustavo pedir. Refino de estilo
  se faz pelos sliders / `style_overrides`, não mexendo no motor.
- Qualquer mudança que altere a saída do preset `magalenha` é um **bug**, não
  um refino. Rode a paridade antes de dar qualquer PR como pronto:

```bash
TYPO_PARITY=1 .venv/Scripts/python.exe -m pytest tests/test_smoke.py -k parity -q
```

O `MAGALENHA_Gustavo_113x111cm.pdf` na raiz é a referência visual (página
113,2 × 111,5 cm, imagem 6686 × 6584 px @150 dpi).

## Arquitetura

```
src/typo/
  config.py       RenderConfig (dataclasses aninhadas) + Scale (mm/cm/px por DPI)
  fonts.py        family -> (regular.ttf, bold.ttf) por SO + GlyphCache
  text_source.py  .txt -> stream de caracteres (phrases | words | chars)
  image_prep.py   load + crop + resize + luminância + Field (sondagem O(1))
  mask.py         máscara das figuras + região de accent
  palette.py      mapa de cor por glifo (tabela fonte -> tinta)
  landscape.py    campos (edge/janela) + passada da paisagem
  typography.py   passada principal de letras
  compose.py      título / subtítulo / quadradinhos / rodapé / moldura
  display.py      letras gigantes + rótulo invertido (layout `display`)
  engine.py       Scene (precompute cacheado) + render(config, mode)
  export.py       PNG com dpi + PDF via img2pdf no tamanho físico
  project.py      project.yaml -> RenderConfig + scaffold
  presets.py      presets nomeados (magalenha, halftone)
  cli.py          entry points typo-render / typo-new-project
app/ui.py         interface Gradio
```

### Pipeline — `engine.render(config, mode)`

1. **image_prep** — abre, aplica `source.crop`, calcula a resolução alvo
   (preview: `page.preview_max_px × preview_supersample`; export: `page.dpi_export`)
   e redimensiona com LANCZOS. Calcula `lum = 0.299r + 0.587g + 0.114b`.
2. **mask** — `lum < lum_threshold` → `binary_fill_holes` → `binary_closing` →
   mantém componentes com área > `min_component_frac` → `fill_holes` → janela de
   borda. Desligada, a arte inteira vira "figura" (halftone puro).
   Produz também `dilated` (usada pela paisagem) e `accent`.
3. **landscape** — `gaussian_filter` + `sobel`, restrito à `band` vertical e a
   **fora** da máscara dilatada; desenha letras pequenas cinza-claras só onde há
   contorno (traço fino).
4. **typography** — varredura por linhas com baseline ondulada; em cada posição
   sonda a escuridão local dentro da máscara, mapeia para o tamanho da fonte
   (`size_min..size_max` via `size_gamma`), aplica bold acima de
   `bold_threshold`, rotaciona o glifo pelo fluxo, pinta com a paleta, o accent
   ou a tinta.
5. **compose** — título, subtítulo, quadradinhos, rodapé, moldura. Com
   `text_blocks.draw: false` não desenha nada (os textos seguem valendo como
   metadado: é de lá que o site lê título/subtítulo).
6. **export** (só no modo export) — PNG com dpi + PDF com `img2pdf` no tamanho
   físico exato.

A camada **display** entra fora dessa ordem: as marcas `layer: under` antes do
passo 3 e as `layer: over` depois do passo 5.

### Duas famílias de layout

- **ficha de espécime** (`text_blocks`, default) — título em cima, arte com
  moldura, rodapé centralizado. Nada se cruza. É o `print_v4.py`.
- **display** (`display`, desligada por default) — a linha de espécime *solta*
  em cima da arte: glifos em corpo de dezenas de cm sangrando pela borda,
  rótulo invertido nomeando a obra, linha vertical na lateral. Uma primitiva
  só, a `mark` (letra gigante, rótulo e linha vertical são todos marks), com
  posição em cm a partir da borda que o `anchor` nomeia — **negativo sangra
  pra fora do papel**. Posiciona pelo **bbox de tinta**, não pelas métricas da
  fonte: num corpo de 40 cm o vazio de ascender passa de 10 cm e toda medida
  pareceria errada. Ver `typo/display.py` e `projects/debret-antropofagia`.

### Config

`RenderConfig` é a **única** fonte de parâmetros — UI e CLI montam a mesma
dataclass. Grupos: `source, mask, text, font, flow, layout, accent, palette,
landscape, colors, page, text_blocks, display`.

```python
cfg = RenderConfig.from_project("projects/magalenha/project.yaml")
cfg = cfg.merge({"font": {"base_line_mm": 4.0}, "flow": {"flex": 0.6}})  # deep merge
cfg.validate()
```

`merge()` rejeita campos desconhecidos (erro em vez de silêncio) e nunca muta o
original. Cores em hex viram RGB via `hex_to_rgb`.

### Cache

`engine.Scene` guarda o resultado do trabalho pesado (imagem preparada, máscara,
accent, campos da paisagem, tabelas de soma acumulada), chaveado por
`(imagem, crop, resolução, params de mask/accent/landscape)`. Sliders de
**tipografia** não invalidam a cena: só a passada 4 re-roda.

Por isso `page.preview_supersample` é uma constante e **não** pode voltar a
depender de `font.base_line_mm` — se depender, arrastar o slider de tamanho
recalcula o `ndimage` inteiro a cada movimento.

## Como rodar

```bash
python -m venv .venv
.venv/Scripts/python.exe -m pip install -e ".[dev]"    # Windows
# .venv/bin/pip install -e ".[dev]"                    # macOS / Linux
```

```bash
.venv/Scripts/python.exe -m app.ui                     # UI em http://127.0.0.1:7860
.venv/Scripts/python.exe scripts/render.py magalenha   # render headless -> PNG + PDF
.venv/Scripts/python.exe scripts/new_project.py meu-poster
.venv/Scripts/python.exe -m pytest -q
```

Também existem os entry points `typo-ui`, `typo-render` e `typo-new-project`,
e os wrappers `scripts/run_ui.sh` / `scripts/run_ui.ps1`.

## Convenção de projetos

```
projects/<nome>/
  project.yaml   conceito + caminhos + overrides de estilo
  refs/          imagens de referência
  text/          .txt com a letra/trecho (uma frase por linha; # = comentário)
  output/        PNG/PDF gerados
```

O `project.yaml` monta a config nesta ordem: **preset** (`style_preset`) →
seções explícitas (`source`, `text`, `page`, `titles`, `accent`, `mask`,
`landscape`) → **`style_overrides`** (deep merge, ganha de tudo).

Para um projeto novo: `python scripts/new_project.py <nome>`, jogue a imagem em
`refs/` e o texto em `text/`, ajuste `source.image` / `source.crop`. O guia de
afinação está em `skills/typographic-poster/SKILL.md`.

## Gotchas

- **Preview ≠ export.** O preview renderiza a página inteira num DPI baixo e
  reduz por LANCZOS. As letras ficam com 4–8 px: dá pra julgar densidade,
  contraste, máscara e accent — não a forma da letra. Só o export usa
  `page.dpi_export`.
- **Tudo em mm, nunca em px.** O motor converte via `Scale(dpi)`. As poucas
  constantes que no `print_v4.py` eram px (o `+1` do avanço, o `+2` da paisagem,
  os pisos `max(9,…)`/`max(7,…)`, a espessura da moldura) estão anotadas com
  `_px` e escalam por `dpi / REFERENCE_DPI` — a 150 dpi dão exatamente o valor
  original. **Não troque isso por px cru**, senão o preview desalinha do export.
- **Fontes.** `font.family` é resolvido varrendo `fonts/` (empacotado) + os
  diretórios do SO (macOS: `~/Library/Fonts`, `/Library/Fonts`,
  `/System/Library/Fonts`; Windows: `%WINDIR%\Fonts` e o dir do usuário; Linux:
  `/usr/share/fonts`, `~/.fonts`, …). Fallback garantido: DejaVu Sans
  empacotado em `fonts/`. A primeira resolução varre o SO inteiro (~2–3 s) e
  fica em `lru_cache`.
  **A DejaVu Sans *Condensed* não vem no Windows** — o preset pede
  `"DejaVu Sans Condensed"` e cai na DejaVu Sans normal, que é um pouco mais
  larga. Se quiser a condensed de verdade, jogue os `.ttf` em `fonts/`.
- **Fonte variável só serve pro `display`.** A Bahnschrift (a DIN 1451 do
  Windows) é um arquivo único com 15 instâncias, de `Light` a `Bold Condensed`.
  O `display.load_font` sabe pedir a instância (`variation:` na mark); o
  `GlyphCache` da malha **não** — e como `resolve_family` devolve
  `regular == bold` para ela, usar Bahnschrift na malha zera o efeito do
  `bold_threshold`, que é uma das alavancas de densidade. Por isso o
  `debret-antropofagia` tem duas fontes: Bahnschrift nas letras gigantes e
  Arial Narrow (com bold de verdade) na malha.
- **Custo do export.** 150 dpi = 44 MP e ~15 s. As tabelas de soma acumulada
  (`Field`) só são construídas abaixo de `SAT_MAX_PX` (8 MP) — acima disso a
  sondagem volta ao `numpy.mean` direto, para não estourar memória.
- **`accent.source_rule`** só implementa `"red"`. Qualquer outro valor levanta
  `NotImplementedError` com um TODO — não existe stub que finge funcionar.
- **Uma cor ou muitas.** `accent` pinta *uma* cor onde uma regra booleana bate.
  Para arte de várias cores use `palette`: tabela `(cor_na_fonte, cor_da_tinta)`
  e vizinho mais próximo, amostrado no **centro** da sonda de cada glifo (não a
  média — média entre dois blocos vizinhos inventaria uma terceira cor). Com a
  paleta ligada o accent não pinta nada: ela já cobre o caso geral, inclusive os
  neutros. O casamento **não** é euclidiano em RGB — `palette.value_weight`
  (0.25) comprime o eixo de brilho, senão as bordas de anti-aliasing do desenho
  sorteiam cor. O porquê está na docstring de `palette.py`; o uso real em
  `projects/turnstile`.

## Estado

- `projects/magalenha/refs/` está **vazio**: a foto original vivia no sandbox
  onde o `print_v4.py` rodou (`/mnt/user-data/uploads/A5613A3C-…png`) e não veio
  junto. O `project.yaml` aponta para `refs/brasileiro.png`. Sem esse arquivo o
  projeto magalenha não renderiza (erro claro, não silencioso).
- `projects/demo/` usa uma referência **sintética** (gerada por
  `tests/fixtures.py`) só para a UI ter algo renderável e para smoke test.
  Pode apagar.
