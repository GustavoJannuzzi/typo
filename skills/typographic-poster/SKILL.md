---
name: typographic-poster
description: Como afinar o motor typo para uma referência nova — escolher o crop, ligar/afinar a máscara, decidir a camada de paisagem, definir a região de accent e ajustar a tipografia. Use ao criar um poster novo em projects/, ao diagnosticar uma máscara ruim, ou quando o resultado sair chapado/vazado/ilegível.
---

# Afinando o motor para uma referência nova

O motor não "entende" a imagem: ele mede **luminância local** e desenha letras.
Quase todo problema de resultado é problema de **máscara** ou de **crop**, não
de tipografia. Afine nesta ordem — cada passo depende do anterior.

Antes de qualquer coisa, leia `CLAUDE.md`. A regra de ouro vale aqui: os
defaults reproduzem o `print_v4.py` bit a bit; ajuste por `style_overrides`,
nunca mexendo no motor.

---

## 0. Escolha da referência

O que funciona:

- **Silhuetas legíveis** contra fundo claro. As figuras viram blocos de texto;
  se a silhueta não se lê em miniatura, o poster não vai se ler.
- **Contraste alto entre figura e fundo.** A máscara é um simples corte por
  luminância — degradê suave entre figura e fundo é o pior caso.
- **Poucos elementos.** 1 a 4 figuras. Detalhe fino (dedos, cabelo solto,
  grades) desaparece: o menor glifo tem ~1,5 mm.

O que não funciona: fundo escuro (a máscara pega o fundo inteiro), figuras
encostando na borda (a janela de borda corta), imagens de baixo contraste.

---

## 1. Crop — antes de tudo

O crop define o aspecto da arte e, no modo `from_art`, o **tamanho da página**:
a altura vem de `page.art_height_cm` e a largura sai do aspecto do crop.

```yaml
source:
  image: refs/foto.png
  crop: [600, 55, 1420, 782]   # [left, top, right, bottom] em px da original
```

- Enquadre **justo** nas figuras, com uma folga de ~3% de cada lado — a máscara
  aplica uma janela de borda (`mask.border_frac = 0.03`) que apaga o que
  encostar na beirada.
- Deixe **acima** das figuras o céu/paisagem que você quiser na camada de
  contorno (a faixa default vai de 6% a 66% da altura).
- Confira com **Ver crop** na UI (ou `app.ui.crop_overlay(cfg)`), que desenha o
  retângulo sobre a imagem inteira.
- `crop: null` usa a imagem inteira.

Mudou o crop? O tamanho da página muda junto. Confira o resultado no resumo do
render (`página W x H cm`).

---

## 2. Máscara — o passo que decide tudo

A máscara é o que dá **fundo branco de verdade**: só se desenha letra onde ela
é verdadeira. Use **Ver máscara** na UI: cinza = figura, vermelho = contorno,
azul = faixa da paisagem, cor = região de accent.

```yaml
mask:
  enabled: true
  lum_threshold: 0.56
```

`lum_threshold` é o corte: pixel com `lum < threshold` é figura.

| Sintoma na overlay | Ajuste |
|---|---|
| Figuras com buracos, partes claras faltando | **suba** `lum_threshold` (0.6, 0.65) |
| O fundo/sombra entrou na máscara | **desça** (0.5, 0.45) |
| Manchas soltas espalhadas | suba `mask.min_component_frac` (0.0009 → 0.003) |
| Contorno serrilhado, buraquinhos | suba `mask.close_iters` (2 → 3–4) |
| Figura quase toda preta e chapada | não é máscara: veja § 4 (densidade/gamma) |

`mask.min_component_frac` é fração da área da arte: `0.0009` = componentes
menores que 0,09% da arte são descartados.

**Máscara desligada** (`enabled: false`) = halftone puro: a imagem inteira vira
texto, sem fundo branco. Use para retratos em close ou texturas. Nesse modo a
paisagem some (a máscara dilatada cobre tudo) — desligue as duas juntas, é o
que o preset `halftone` faz.

---

## 3. Paisagem — contorno fino ao fundo

Camada opcional de letras pequenas cinza-claras que segue **só o contorno**
(edge-dominado) numa faixa vertical, do lado de fora da máscara dilatada.

```yaml
landscape:
  enabled: true
  edge_gain: 6.5
  band: [0.06, 0.66]     # fração da altura da arte
```

Use quando a referência tem **horizonte, montanha, arquitetura** — algo com
linha. Não use quando o fundo é liso (não há contorno: sai nada, ou pior, sai
ruído) nem quando o fundo é ocupado demais (compete com as figuras).

| Sintoma | Ajuste |
|---|---|
| Contorno quase invisível | suba `edge_gain` (8–12) ou desça `floor` (0.14 → 0.10) |
| Fundo virou sujeira/ruído | desça `edge_gain` (4–5) ou suba `floor` (0.20) |
| Traço grosso demais | aproxime `shade_dark` de `shade_light` (ex. 175/210) |
| Paisagem no lugar errado | ajuste `band` — é a faixa vertical em fração da altura |
| Paisagem encostando na figura | suba `mask.dilate_frac` (0.006 → 0.01) |

---

## 4. Accent — a cor de destaque

Hoje só existe a regra `red`: pixels vermelhos da imagem **fonte**, dentro da
máscara e dentro de uma faixa horizontal.

```yaml
accent:
  enabled: true
  color: "#963A2A"       # a cor da TINTA (independe da cor na foto)
  source_rule: red       # única regra implementada
  central_x: [0.30, 0.70]
```

- `central_x` é o filtro que restringe a região à figura do meio — ajuste se o
  elemento colorido estiver noutra posição (ex. `[0.0, 0.4]` para a da esquerda).
- Se a região na foto não for avermelhada, mexa em `accent.red_min` (105) e
  `accent.red_delta` (30). Vermelho apagado pede `red_delta` menor (15–20).
- `accent.hit_threshold` (0.25) é quanto da sonda precisa ser accent para o
  glifo sair colorido. Suba para deixar só o miolo colorido.
- Nada apareceu? Confira na overlay de máscara — a região de accent aparece
  pintada. Se está fora da máscara, ela é descartada.

Outras regras (matiz/HSV, polígono desenhado) **não existem**: qualquer valor
diferente de `red` levanta `NotImplementedError`.

### 4b. Paleta — quando a arte tem várias cores

O accent dá **uma** cor. Para referência colorida (arte vetorial chapada, capa,
cartaz) use `palette`: uma tabela `(cor_na_fonte -> cor_da_tinta)`. Cada glifo
pega a tinta do stop mais próximo do pixel no centro da sua sonda.

```yaml
accent:
  enabled: false          # a paleta substitui o accent, não soma
palette:
  enabled: true
  blur_sigma: 1.2         # achata ruído de JPEG antes de quantizar
  stops:
    - ["#020202", "#141414"]   # traço      -> tinta
    - ["#EFE6C7", "#D6CBA6"]   # papel      -> creme claro
    - ["#E2748F", "#FF2D78"]   # rosa medido -> rosa forte
```

Roteiro:

1. **Meça as cores da referência**, não chute. Quantize a imagem e liste as
   dominantes por área — as `from` têm que ser as cores que existem no arquivo.
2. **Declare os neutros também** (traço, papel, branco). Não há limiar de
   saturação: o que não estiver na tabela vai para o stop mais próximo, e um
   neutro faltando vira cor aleatória no traço do desenho.
3. **Escolha as `to`** — é aqui que está o projeto gráfico. Saturar as cores
   medidas dá destaque; mandar os neutros para tons claros (não para a tinta)
   preserva o papel como papel.

| Sintoma | Ajuste |
|---|---|
| Cor certa, mas pastel/lavada | é densidade, não paleta: veja § 5 |
| Cores pulando entre glifos vizinhos | suba `palette.blur_sigma` (1.5–2.5) |
| Cor aleatória nas bordas do desenho | desça `palette.value_weight` (0.15) ou declare o neutro que falta |
| Um bloco saiu com a cor do vizinho | os dois `from` estão perto demais; meça de novo |
| Campo de ruído cinza onde era papel | mande o neutro para um tom claro, não para `colors.ink` |

Os quadradinhos do cabeçalho passam a mostrar as cores cromáticas da paleta,
na ordem dos stops — os neutros são omitidos.

---

## 5. Tipografia — só depois que máscara e crop estão bons

| Parâmetro | Default | Efeito | Suba quando |
|---|---|---|---|
| `font.base_line_mm` | 3.5 | altura de linha; escala tudo | quiser letra legível de perto / menos densidade |
| `font.size_min_mm` | 1.5 | piso do tamanho | as áreas claras sumirem |
| `font.size_max_ratio` | 1.7 | teto = linha × ratio | quiser mais peso nas sombras |
| `font.size_gamma` | 1.5 | contraste claro/escuro | a figura estiver chapada (2.0–2.5) |
| `font.bold_threshold` | 0.5 | acima disso o glifo sai bold | ↓ para engrossar o conjunto |
| `mask.interior_fill_min` | 0.30 | ponto de preto do mapeamento (ver abaixo) | ↓ para corpo mais sólido, ↑ para mais vazado |
| `flow.flex` | 1.0 | multiplica ondulação + rotação | ↓ 0.3 para linhas quase retas |
| `layout.advance_factor` | 0.98 | espaçamento horizontal | ↑ para texto mais arejado |
| `layout.row_step_ratio` | 0.9 | passo entre linhas | ↓ para linhas mais coladas |
| `layout.jitter_px` | 0.0 | deslocamento aleatório | 1–2 para textura menos regular |

Diagnóstico rápido:

- **O export saiu mais chapado que o preview** → alargue a faixa tonal
  (`size_max_ratio` 2.0), não suba `size_min_mm`. Em DPI alto as linhas se
  sobrepõem muito mais, então um piso alto de tamanho preenche tudo. Aconteceu
  no `projects/jotape`.
- **Com paleta, o export sai mais CLARO que o preview** — o oposto do de cima.
  Arte de cor chapada não tem textura fina para as linhas somarem em cima, e o
  preview a ~40 dpi mostra a cor bem mais forte do que ela sai. Se a arte é
  colorida, meça densidade **no export**, não no preview. Ver
  `projects/turnstile`.
- **Cor pastel quando devia ser forte** → o problema é cobertura de tinta, e
  os blocos de cor são quase todos meio-tom. `size_gamma` **abaixo de 1**
  (0.7–0.85), `size_max_ratio` 2.2, `interior_fill_min` 0.20+, e cole as letras
  (`advance_factor` 0.84, `row_step_ratio` 0.74). Piso de preenchimento é piso
  de saturação. Ver `projects/turnstile`.
- **Retrato onde o rosto some** (rosto mais claro que o cabelo/chapéu) →
  `size_gamma` **abaixo de 1** (0.9–1.0). Gamma alto joga o meio-tom para a
  menor letra e apaga o rosto. Ver `projects/ouro-marrom`.
- **Figura chapada, sem volume** → `size_gamma` 2.0–2.5 e `interior_fill_min` 0.20.
- **Figura vazada, parece rendinha** → `interior_fill_min` 0.15, `bold_threshold` 0.4.

**Cuidado com o nome de `mask.interior_fill_min`.** Não é um piso de
preenchimento: é o **ponto de preto** do mapeamento tom → tamanho
(`fs = size_min + span * (dark - fill_min) / (1 - fill_min)`). Subir esse valor
**encolhe** o glifo em toda a faixa tonal — só o preto puro (`dark = 1`) fica
igual —, porque comprime o resto contra o mínimo. Verificado numericamente com
`size_min=8, size_max=34`: para `dark=0.5`, `fill_min` 0.05 dá fs 20.3, e 0.40
dá fs 12.3.

Consequência prática: **para mais corpo, DESÇA** `interior_fill_min` (é por isso
que todos os projetos de halftone puro usam 0.05–0.15). Quem levanta as áreas
claras é `font.size_min_mm`, não este parâmetro — são knobs diferentes e
empurram para lados diferentes.
- **Ilegível de perto** → `base_line_mm` 4.5–5.0 (menos letras, maiores).
- **Muito rígido/geométrico** → `flow.flex` 1.2 + `jitter_px` 1.0.

O texto entra fragmentado como textura. `text.mode`: `phrases` mantém as frases
inteiras (dá para ler pedaços), `words` embaralha mais, `chars` vira textura
pura sem espaços. `text.repeat` só precisa ser grande o bastante para cobrir a
arte — o stream é consumido ciclicamente.

---

## 6. Página e export

```yaml
page:
  mode: from_art            # altura da arte + margens definem a página
  art_height_cm: 88
  margins_cm: { top: 13, bottom: 10.5, side: 7 }
  dpi_export: 150
```

- `from_art`: a página nasce da arte. É o modo do magalenha (113 × 111 cm).
- `fixed`: você dá `width_cm` e `height_cm`, e a arte é encaixada dentro das
  margens (encolhe se não couber na largura).
- A margem superior grande existe para o bloco de título. Se mudar
  `margin_top_cm`, confira que o título não colide com a arte.
- Sempre confira o **mediabox em cm** que o `scripts/render.py` imprime.

---

## 6b. Layout `display` — letras gigantes em cima da arte

A ficha de espécime (`text_blocks`) põe título, quadradinhos e rodapé em faixas
que nunca cruzam a arte. O layout `display` é o oposto: corpo de dezenas de cm
atravessando a imagem, sangrando pela borda, com rótulo invertido no lugar do
cabeçalho. Mesma informação, geometria de cartaz suíço.

```yaml
titles:
  title: "TUPI OR NOT TUPI"          # continua valendo como METADADO (o site lê)
  draw: false                        # mas a página não desenha a ficha

display:
  enabled: true
  family: Bahnschrift                # '' = usa a mesma fonte da malha
  marks:
    - text: "T"
      size_cm: 30
      anchor: lt                     # borda de referência: l|c|r + t|c|b
      x_cm: 3.5
      y_cm: 4.5                      # NEGATIVO sangra pra fora do papel
      variation: Bold Condensed      # instância de fonte variável
      layer: over                    # over = chapada | under = atrás da malha
    - text: "OBRA\nAUTOR"
      size_mm: 9
      anchor: ct
      x_cm: 4
      y_cm: 20
      box: true                      # rótulo invertido: caixa de tinta, texto no fundo
      pad_mm: 5
    - text: "EXPERIMENTO TIPOGRÁFICO"
      size_mm: 6
      anchor: rt
      x_cm: 1.5
      y_cm: 2.2
      rotate_deg: -90                # a linha vertical da lateral
```

Uma primitiva só, a `mark`: letra gigante, rótulo e linha vertical são todos a
mesma coisa com valores diferentes. O que vale saber ao afinar:

- **`x_cm`/`y_cm` é onde a TINTA começa**, não a caixa em do glifo — o motor
  posiciona pelo bbox de tinta. Dá pra conferir com régua no papel.
- **Não sangre pelo topo uma letra que precisa ser lida.** Um `T` com a barra
  cortada lê como `I` e a palavra se desmancha. Sangre pelas laterais e por
  baixo.
- **`layer: under` só aparece se houver arte por cima.** A letra é desenhada
  antes da passada de letras e a malha atravessa ela; onde a arte é branca, o
  efeito é idêntico a `over` (e onde a tinta é a mesma, também). Escolha `under`
  quando quiser que a letra pareça impressa por baixo da imagem.
- **Fonte variável não vale pra malha**, só pra `display` (ver os Gotchas do
  CLAUDE.md). Se quiser a mesma fonte nos dois corpos, use uma família com
  regular e bold em arquivos separados.
- Ajuste as posições sempre no **preview**: o corpo em cm não depende de dpi,
  mas a largura da página depende do aspecto do crop.

---

## 7. Roteiro para um poster novo

1. `python scripts/new_project.py <nome>`; imagem em `refs/`, texto em `text/`.
2. Ajuste `source.crop`, confira com **Ver crop**.
3. Afine `mask.lum_threshold` olhando **Ver máscara**. Só siga quando a
   silhueta estiver limpa.
4. Decida a paisagem (liga/desliga; ajuste `band` e `edge_gain`).
5. Defina o accent (`central_x`, `red_delta`) e confirme na overlay.
6. Só então mexa na tipografia, com **Preview** (~1,5 s por iteração).
7. Congele o que ficou bom em `style_overrides` no `project.yaml`.
8. Export final: `python scripts/render.py projects/<nome>/project.yaml`.

Escreva em `notes:` o que você decidiu e por quê — é o que faz a próxima sessão
entender o projeto sem redescobrir tudo.
