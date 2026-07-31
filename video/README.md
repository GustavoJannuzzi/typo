# video — captura determinística

Vídeos do site e do processo de criação, montados frame a frame.

Nada aqui grava em tempo real. A "câmera" é um `transform` CSS que o script
move em passos fixos; cada frame é capturado só depois que a página confirmou
que aplicou o estado, e o `ffmpeg` monta a sequência no fim. **Rodar de novo
sai igual** — o tempo do vídeo é o `fps` do roteiro, não o relógio da máquina.

Fica fora de `site/` de propósito: a landing pesa ~18 KB e não pode engordar
por causa de ferramenta de estúdio.

## O que precisa estar instalado

```bash
npm --prefix video install
```

Uma dependência só, o binário do `ffmpeg` (~61 MB, dentro de
`video/node_modules`, sem tocar no PATH do Windows).

**O navegador não é dependência.** `lib/cdp.mjs` fala o protocolo do Chrome
direto com o Chrome ou o Edge que já estão na máquina — sem baixar Chromium,
sem Playwright.

O `ffmpeg` é a única coisa que sobrou porque o Chrome headless sem GPU não
encoda H.264 (medido nesta máquina: `avc1=false`, `vp8/vp9=true`). Daria pra
sair `.webm` sem instalar nada, mas o entregável é pra Instagram e WhatsApp, e
lá é mp4.

Sem o `ffmpeg`, o pipeline **não quebra**: captura os frames, escreve no disco
e imprime o comando exato pra encodar depois.

## Rodar

```bash
npm --prefix site run build
```

```bash
node video/render.mjs video/roteiros/tour-9x16.mjs
```

```bash
node video/render.mjs video/roteiros/processo-9x16.mjs
```

O tour renderiza `site/dist`, não o dev server — HMR e transform sob demanda
não são determinísticos. Se `dist/` estiver mais velho que `site/src`, o
`render.mjs` avisa.

## Afinar

Toda a superfície de ajuste está nos arquivos de `roteiros/`. Eles são
**dados**: duração, easing, ponto de zoom, tempo de cada plano, texto por
cima. Mexer no ritmo do vídeo nunca exige mexer no motor de captura.

```js
{
  nome: "mergulho",
  de:   { alvo: "[data-gallery-detail-img]", zoom: "altura", margem: 0 },
  para: { alvo: "[data-gallery-detail-img]", zoom: 3.0, foco: [0.44, 0.46] },
  dur: 3.4,
  ease: "saidaExpo",
  titulo: { texto: "de perto", sub: "35.880 glifos", posicao: "baixo" },
}
```

| campo | o que é |
|---|---|
| `alvo` | qualquer seletor CSS da página |
| `foco` | `[x, y]` normalizado **dentro do alvo**. `[0.5, 0.3]` = um pouco acima do meio |
| `zoom` | número (`1` = tamanho real) ou `"largura"` / `"altura"` / `"conter"` |
| `margem` | folga em volta quando o zoom é por enquadramento |
| `dur` | segundos |
| `ease` | nome da tabela em `lib/easing.mjs`, ou `cubic-bezier(a,b,c,d)` |
| `titulo.fundo` | `"placa"` (etiqueta em papel), `"brilho"` (halo) ou `"nenhum"` |

Sem `de`, o plano começa onde o anterior terminou.

### O ciclo curto

`--de N --ate M` renderiza **só** aqueles planos. Como cada frame é função pura
do roteiro, o pedaço renderizado sozinho é idêntico ao mesmo pedaço dentro do
vídeo inteiro — e as ações anteriores (abrir a obra, arrastar o comparador)
são reexecutadas antes, sem capturar, pra página estar no estado certo.

```bash
node video/render.mjs video/roteiros/tour-9x16.mjs --de 6 --ate 6 --rascunho
```

### Chapas paradas

```bash
node video/lib/chapa.mjs cena --obra ouro-marrom
```

Dois PNGs por ato em `out/chapas/`. É o jeito de ver a composição sem esperar
um encode — e o único jeito de eu conferir alguma coisa, já que eu não assisto
a vídeo.

## Opções

| flag | efeito |
|---|---|
| `--rascunho` | 30 fps, sem supersample, jpeg 82, crf 26, preset rápido |
| `--de N --ate M` | só os planos N..M (0-based, inclusive) |
| `--fps N` | sobrescreve o fps do roteiro |
| `--ssaa N` | captura N× maior e reduz no ffmpeg (2 = texto sem serrilha) |
| `--png` | frames intermediários sem perda (~2× mais lento, ver abaixo) |
| `--q N` | qualidade do jpeg intermediário (padrão 96) |
| `--crf N` | qualidade do H.264 (17 ótimo · 20 leve · 23 padrão) |
| `--so-frames` | captura e para |
| `--so-encode` | pula a captura, encoda o que já está no disco |
| `--saida <arq>` | caminho do mp4 |

## Custo real, medido nesta máquina

A 1080×1920, por frame capturado:

| configuração | s/frame | disco/frame |
|---|---|---|
| **`--ssaa 1` + jpeg 96 (padrão)** | **~0,43 s** | ~0,3 MB |
| `--ssaa 2` + jpeg 96 | ~0,96 s | ~0,8 MB |
| `--ssaa 2 --png` | ~1,86 s | ~4,8 MB |

Duas escolhas de padrão saíram daí, e as duas custam caro se invertidas:

- **jpeg 96, não png.** Comprimir 8 MP sem perda custa o dobro do tempo e seis
  vezes o disco. A perda do jpeg 96 fica abaixo da quantização do próprio
  H.264 em crf 17 — some no encode.
- **`ssaa 1`, não 2.** Com 1080 de saída e 430 de layout, a página já
  renderiza com densidade 2,51× — o texto já sai em alta densidade. Levar a
  5,02× e reduzir com lanczos ganha pouco e custa o dobro.

Um vídeo de 30 s a 60 fps = 1800 frames ≈ **13 min** de captura no padrão. É
render offline, não preview. Para julgar ritmo use `--rascunho` com
`--de/--ate` — um plano de 3 s sai em ~25 s.

O que faz cada frame custar isso é o
`--run-all-compositor-stages-before-draw`: ele obriga o Chrome a terminar toda
a rasterização antes de entregar o frame. É lento de propósito — é o que
garante que nenhum frame saia com uma camada pela metade.

## Nitidez no zoom

Nada no palco recebe `will-change: transform`. Camada promovida é rasterizada
uma vez e depois só escalada como textura — ótimo pra animação em tempo real,
péssimo aqui. Sem promover, cada frame re-rasteriza no zoom em que está, e o
mergulho sai **nítido**. É uma vantagem de qualidade que a captura quadro a
quadro ganha de graça sobre gravar em tempo real.

O limite, então, não é o método — é o arquivo:

```
<slug>-full.webp     1600 px no lado maior
<slug>-detail.webp   1100 × 1100 (recorte 1:1 do export de 150 dpi)
```

Sobre o `-detail` dá pra empurrar até ~3× antes de amolecer. Mais que isso
pede um asset maior, o que pede os exports de 150 dpi de volta em
`projects/<slug>/output/` (hoje a pasta está vazia) e um `-macro` de 2400 px
saindo do `scripts/build_site_assets.py`.

## A cena de processo

`cena/processo.html` — nove atos que refazem os passos de `engine.py`: a foto,
o plano cartesiano, a luminância, a máscara, a sonda, os pontos, a tinta, as
letras, a ficha de espécime.

As fórmulas são as do motor (as mesmas que `site/src/modules/halftoneCanvas.js`
já porta), inclusive o avanço variável por largura de glifo — com passo fixo as
letras grandes das áreas escuras se atropelam, coisa que a peça impressa não
faz. A malha da cena é mais grossa que a da peça real, pra ler num vídeo
vertical; a leitura `MALHA (CENA)` mostra as duas, então a diferença fica dita.

A cena é **função pura de `t`**:

```js
window.__cena.seek("letras", 0.5)   // mesmo frame, sempre
```

Trocar a obra é `?obra=<slug>` na url do roteiro — qualquer slug de
`site/src/data/works.json`.

A foto de referência sai do `<slug>-before.webp` quando ele existe (é o
recorte alinhado pixel a pixel com a arte, gerado pelo
`build_site_assets.py`). Hoje só `ouro-marrom` tem esse par; para as outras a
cena cai na referência crua de `projects/<slug>/refs/` e aplica o `source.crop`
do `project.yaml` — o mesmo `(left, upper, right, lower)` que o PIL usa.

## Estrutura

```
video/
├── render.mjs            CLI
├── roteiros/             <- É AQUI QUE SE AFINA
│   ├── tour-9x16.mjs
│   └── processo-9x16.mjs
├── cena/
│   ├── processo.html     a cena de "como nasce uma obra"
│   ├── processo.css
│   └── processo.mjs
├── lib/
│   ├── cdp.mjs           cliente do protocolo do Chrome (sem dependência)
│   ├── servidor.mjs      serve dist + cena + refs + textos numa origem só
│   ├── palco.mjs         o que roda dentro da página (câmera, texto, ações)
│   ├── camera.mjs        planos -> frames; zoom interpola em log
│   ├── easing.mjs        tabela de easings nomeados
│   ├── captura.mjs       o laço frame a frame
│   ├── encode.mjs        frames -> mp4
│   └── chapa.mjs         chapas paradas pra conferir composição
└── out/                  frames e mp4 (fora do git)
```

## Vocabulário de ações

O roteiro chama gestos pelo nome, nunca escreve JS. Os que existem hoje estão
em `lib/palco.mjs`, em `__typo.acoes`:

`abrirObra(slug)` · `fecharObra()` · `verDePerto()` · `comparar(pct)` ·
`abrirMenu()`

Um gesto novo é uma entrada nova nesse objeto.
