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
  seal.py         selo tipografico: QR desenhado com as letras da obra
  cli.py          entry points typo-render / typo-new-project
app/ui.py         interface Gradio
```

Fora do motor, em `scripts/`, vive a camada de **divulgação** — pós-processamento
puro do PNG exportado, sem redesenhar pixel nenhum:

```
scripts/social_kit.py           tokens do base.css + fontes da identidade + primitivas
scripts/build_brand_assets.py   avatar / lockups / capas de destaque -> social/marca/
scripts/build_instagram.py      carrossel 4:5 e 9:16 por obra      -> social/<slug>/
scripts/publish_media.py        social/ -> site/public/midia/ + SQL das tarefas
scripts/make_seal.py            selo (QR de letras) de uma peça vendida -> seals.json
scripts/build_certificates.py   contagem + carta -> site/src/data/certificates.json
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

```bash
.venv/Scripts/python.exe scripts/build_brand_assets.py          # marca do Instagram
.venv/Scripts/python.exe scripts/build_instagram.py ouro-marrom # carrossel da obra
```

```bash
.venv/Scripts/python.exe scripts/make_seal.py ouro-marrom --owner Nome --edition 3/5
.venv/Scripts/python.exe scripts/build_certificates.py          # -> site/src/data/certificates.json
```

## Divulgação — a camada de Instagram

`build_instagram.py <slug>` lê `projects/<slug>/output/*150dpi.png` e cospe
`social/<slug>/{feed,story}/` com quatro cartas que vão de longe pra perto:
a peça inteira, a malha a 2,6×, o macro 1:1 e a ficha de espécime. **Não chama
o motor** — é recorte e composição em cima do PNG que já existe. Sem export,
ele cai no `-full.webp` do site e avisa em voz alta que o macro sai borrado.

Duas decisões que valem conhecer antes de mexer:

- **Onde o macro corta.** O critério é `min(espessura da tinta, folga do
  branco)`, medido por erosão em degraus. Rejeita de uma vez a mancha preta
  chapada (tinta grossa, branco zero) e o papel vazio (branco largo, tinta
  zero) — que é o que "procure a região mais escura" (o
  `find_densest_window` do `build_site_assets.py`) erra. A cobertura entra só
  como desempate. `--debug` escreve o mapa do critério com as janelas
  escolhidas por cima da arte.
- **O título da carta 01.** Sem véu, sem degradê, sem sombra — nunca. Ou o
  título acha uma faixa silenciosa na própria arte e escreve em tinta sólida,
  ou desce pro papel embaixo da moldura, que é o que o pôster faz. `--titulo
  sobre` força por cima com placa de papel de corte reto; nas peças de hoje o
  automático quase sempre escolhe o papel, porque a figura enche a página.

A marca (`build_brand_assets.py`) prova cada avatar em **110 px circular**, que
é o tamanho real no feed — é lá que ideia bonita morre. `social/marca/` fica no
git; `social/<slug>/` não, pela mesma regra de `projects/*/output/`.

`publish_media.py` fecha o ciclo: copia `social/` pra `site/public/midia/` (que
o deploy serve como URL pública) e gera `site/supabase/seed-tarefas.sql` — uma
tarefa por obra, com anexos e responsável, pro quadro do `/admin`. **Ele não
escreve no banco**: a RLS de `public.tasks` só aceita sessão autenticada, então
o caminho é colar o `.sql` no SQL Editor do Supabase. Os ids são `uuid v5` do
slug, então rodar de novo atualiza em vez de duplicar. Detalhes de operação em
`site/README.md`.

Nenhuma cor e nenhum nome de fonte é escrito nesses scripts: `social_kit.py` lê
`site/src/styles/base.css` e `site/src/config.js` em runtime. Trocar a
terracota lá troca o Instagram junto. As fontes vêm dos mesmos `.woff2` do site,
convertidos pra `.ttf` uma vez em `scripts/.fontcache/` (precisa de `fonttools`
e `brotli`; a Archivo é variável e os eixos `wght`/`wdth` são os do CSS).

## Selo e certificado

Cada peça vendida pode ganhar um **selo**: um QR code desenhado com as letras
da própria obra (`src/typo/seal.py`), que aponta pra uma **página de
certificado** pública e estática (`/certificado/<CODE>/`) com a ficha de
autenticidade da peça. Nem toda obra tem selo — normalmente o Gustavo avisa
qual e com que dono.

```bash
.venv/Scripts/python.exe scripts/make_seal.py <obra> [--owner Nome] [--edition 3/5]
.venv/Scripts/python.exe scripts/build_certificates.py
```

**O selo NÃO é o motor.** `typography.py` desenha com baseline ondulada,
avanço proporcional ao glifo e rotação livre — nenhuma combinação de sliders
garante "esta letra não invade o módulo vizinho", e um vazamento mata a
leitura do QR. `seal.py` é uma primitiva à parte, na família do `display.py`:
geometria própria (grade rígida, clipe duro por módulo, núcleo sólido nas
contra-formas), reaproveitando `fonts`/`Scale`/`text_source`. O motor não é
tocado — `TYPO_PARITY=1 pytest -k parity` continua sendo o juiz.

`core_ratio: float = 0.18` (o diâmetro do núcleo sólido em cada módulo escuro,
ver `SealSpec`) não é chute: é o menor valor que empata com um QR **liso** de
controle numa bateria de 23 degradações (redução até 160px, blur, rotação,
JPEG, contraste lavado). Abaixo disso o selo simplesmente não escaneia; acima,
só entope a contra-forma do `o`/`e` sem ganhar nada. A medição está na
docstring de `SealSpec` — não reduza esse número sem repetir a varredura.

`make_seal.py` **não grava o que não lê de volta**: decodifica o próprio PNG
com `zxing-cpp` (nativo + 800px + 400px) antes de salvar qualquer arquivo. Isso
é a condição necessária, não a suficiente — o teste real é imprimir e escanear
de perto e de longe, que só o Gustavo pode fazer.

### O registro — `site/src/data/seals.json`

Ao contrário de `projects/*/output/`, **este arquivo vai pro git**: é o único
registro de quais selos existem, pra quem e desde quando. Cada selo emitido
vira um commit — o histórico do git é o livro de registro, sem nada construído
pra isso. `code` é Crockford base32 (sem I/L/O/U) e globalmente único entre
todas as obras. `owner`, quando presente, é **só o primeiro nome** — o
certificado é público e sem senha, então sobrenome numa URL que qualquer um
que escanear o selo vê é dado de mais. `owner: null` não é um placeholder, é
uma peça da casa (coleção interna).

### A contagem — `scripts/build_certificates.py`

A parte mais forte da ficha ("357× *levanta* aparece no retrato", como no
molde de `emails/entrega-emicida.html`) é **calculada**, não escrita à mão:

```
volta          = uma passagem inteira pelo .txt, no modo real do motor
                 (text_source.build_stream, repeat=1)
nao_espacos    = caracteres de `volta` que não são espaço
voltas         = works.json[slug].glyphs / nao_espacos
ocorrências(p) = round(quantas vezes `p` aparece numa volta × voltas)
```

`nao_espacos`, não `len(volta)`: em `typography.py` o cursor do stream **anda**
no espaço, mas `stats.glyphs` **não conta** espaço (o `continue` antes do
`stats.glyphs += 1`). Validado contra o e-mail do Emicida como gabarito — as
10 ocorrências de palavra batem exatas.

**O ranking de palavras não é automático.** A primeira versão tentava "top 10
por frequência" e não batia com o e-mail: "sou" (3×) ficava de fora enquanto
"somos" (3×) entrava — duas conjugações do mesmo verbo, sem stopword list que
separe uma da outra. Foi curadoria manual do Gustavo escrevendo o e-mail, não
algoritmo. Por isso `projects/<slug>/certificado.md` **declara** a lista
(frontmatter `palavras:`); o script só faz a conta pra cada uma. A primeira da
lista é o número-herói da página.

### `certificado.md` — o único conteúdo escrito à mão

```markdown
---
palavras: [levanta, anda, vai, sonho, quem, sei, onde, somos, seguir, nossa]
---

A carta, em markdown mínimo (parágrafos + `*itálico*`).
```

Sem esse arquivo, a obra **não gera certificado** — e isso é o comportamento
certo: obra sem carta não devia virar página pela metade. `palavras:` é
opcional; sem ela, a seção de contagem simplesmente não aparece (ver
`debret-antropofagia`, cujo `text/*.txt` está marcado como provisório pelo
próprio Gustavo — computar uma "curadoria" em cima de texto incompleto seria
inventar um número que muda quando o manifesto for colado por inteiro).

Se `palavras:` está declarada mas a obra não tem `glyphs` em `works.json`
(caso do `magalenha` — ver "Estado" mais abaixo), o script **falha alto** em
vez de inventar a contagem. E se um selo já emitido em `seals.json` não tem
`certificado.md` correspondente, `build_certificates.py` também falha a build
inteira: um selo impresso aponta pra uma URL que precisa existir.

### A página — `site/certificado/` + `site/build/certificates.js`

Mesmo esquema de `/en/`, `/es/`, `/it/` e `/admin/`: um template estático
(`certificado/index.html`), multiplicado na build em uma pasta por selo
(`/certificado/<CODE>/`), via marcadores `data-cert*` no espírito do
`data-i18n` de `build/i18n.js` — texto, HTML interno (a carta e as linhas do
ranking, já prontas em `certificates.json`), atributo, e remoção condicional
de elemento inteiro (`data-cert-if`). **Sem banco, sem `fetch`, sem
`vercel.json`**: os dados vão inline no HTML, pra carregar instantâneo e pra a
prévia de link no WhatsApp funcionar (`og:image`/`og:url` só existem com HTML
já pronto). `noindex` é obrigatório — é artefato pessoal, não vitrine de
busca. O template cru (com "TÍTULO DA OBRA" de placeholder) nunca fica
acessível: o plugin apaga `dist/certificado/index.html` depois de gerar as
pastas por código.

### A imagem — reaproveita `public/art/`, com um fallback pra obra irreproduzível

`ensure_art_assets()` usa os `.webp` que `build_site_assets.py` já gera pra
galeria. Quando faltam (o `magalenha`, cuja `refs/` sumiu — ver "Estado") e o
export de 150 dpi checked-in existe, ele recorta a arte pura DAQUELE PNG
sozinho, sem abrir a imagem de referência: `crop_w`/`crop_h` saem direto da
tupla `source.crop` do `project.yaml` (que já é exatamente o tamanho do
recorte, sem precisar medir arquivo nenhum). Mesma geometria de
`art_bbox_px()`, sem a dependência que faltou.

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
  projeto magalenha não renderiza (erro claro, não silencioso) — e por isso ele
  também não entra em `works.json` (fora do `ORDER` de `build_site_assets.py`).
  O certificado dele existe mesmo assim: `ensure_art_assets()` recorta a arte
  pura direto do PNG de 150 dpi já exportado (que está no git, ver `.gitignore`),
  sem precisar da referência — mas sem `glyphs` em `works.json`, a seção de
  contagem não pode ser calculada, então o `certificado.md` dele não declara
  `palavras:`.
- `projects/demo/` usa uma referência **sintética** (gerada por
  `tests/fixtures.py`) só para a UI ter algo renderável e para smoke test.
  Pode apagar.
