# Onde Moram as Palavras — landing page

Página de divulgação e captação de encomendas para a coleção de artes
tipográficas do `typo`. Vanilla JS + Vite, mobile-first, **sem backend** —
o pedido é montado como mensagem de WhatsApp, sem carrinho/checkout.

## Antes de publicar

Preencha [`src/config.js`](src/config.js):

```js
export const CONFIG = {
  WHATSAPP: "5511987654321",       // DDI+DDD+numero, so digitos
  EMAIL: "contato@seudominio.com",
  SITE_URL: "https://seudominio.com", // dominio publicado, sem barra no fim
  LAUNCH_SLOTS_TAKEN: 0,           // atualize conforme forem vendendo
  // ...
};
```

Sem `WHATSAPP` preenchido, o botão "Enviar pelo WhatsApp" ainda funciona mas
abre `wa.me/` sem número de destino — **não esqueça de preencher antes do
deploy**.

Sem `SITE_URL`, as páginas saem sem `canonical`/`hreflang` (a build avisa em
amarelo): o Google indexa os quatro idiomas, mas não sabe que são a mesma
página em línguas diferentes. Na Vercel dá pra deixar vazio — o build lê
`VERCEL_PROJECT_PRODUCTION_URL` sozinho.

## Rodar local

```bash
npm install
npm run dev       # http://127.0.0.1:5173
```

```bash
npm run build      # gera dist/
npm run preview    # serve dist/ para conferir o build de producao
```

## Quatro idiomas (pt · en · es · it)

Cada idioma é uma **página de verdade**, gerada na build: `/`, `/en/`, `/es/`,
`/it/`. Não é troca de dicionário no cliente. O motivo é a divulgação lá fora:
quem chega da Itália ou dos EUA chega pela busca, e com uma URL só o Google
indexa uma versão só — justo a que aquela pessoa não procura. De quebra sai
mais leve, porque nenhum dicionário viaja no bundle.

Como funciona (`build/i18n.js`):

- `index.html` **em português é a fonte da estrutura**. O que se traduz está
  marcado com `data-i18n="chave"` (troca o conteúdo do elemento) ou
  `data-i18n-attr="alt:chave,aria-label:chave"` (troca atributos).
- Os textos ficam em `src/i18n/<code>.json`. Português não tem seção `html`:
  o texto do `index.html` já é o original.
- Três marcadores no HTML geram o que depende da lista de idiomas:
  `<!--i18n:head-->` (hreflang, canonical, og:locale e o script de detecção),
  `<!--i18n:langswitch-->` e `<!--i18n:langswitch:footer-->` (o seletor).
- As strings que o JS monta (galeria, construtor de pedido) não cabem no HTML:
  vão num `<script type="application/json">` no fim do body — **só as do
  idioma daquela página** — e são lidas por `src/i18n/runtime.js` (`t()`).

Mexer em texto:

| o que | onde |
| --- | --- |
| texto em português | direto no `index.html` |
| tradução de um texto da página | `src/i18n/<code>.json` → `html` |
| string que o JS monta | os **quatro** arquivos → `js` |
| blurb/título de obra traduzido | `src/i18n/<code>.json` → `works` |
| idioma novo | uma entrada em `src/i18n/locales.js` + um `<code>.json` |

A build **quebra** se faltar chave em en/es/it, ou se uma tradução perder um
gancho `data-*` que o JS procura (o `<strong data-slots-total>` do contador de
vagas, por exemplo). Página publicada pela metade é pior que build vermelha.

**Título e subtítulo das obras não se traduzem.** Estão impressos no pôster,
em português: são parte da arte. "O Glorioso Retorno" traduzido na galeria
descreveria uma peça que não existe. O que se traduz é o texto de apoio — e a
tradução do título entra *ao lado* (campo `gloss`), em itálico e apagada, como
legenda. `works.json` é gerado por script e não se edita à mão; por isso as
traduções dos blurbs vivem nos catálogos, não lá.

O idioma é detectado por `navigator.language` (script inline, só na raiz, antes
da primeira pintura) — mas a escolha manual manda: clicar no seletor grava
`omp-lang` no `localStorage` e a detecção nunca mais redireciona. Quem está no
exterior e quer ler em português não fica preso.

## Assets da galeria

As imagens em `public/art/*.webp` e os metadados em `src/data/works.json`
**são gerados**, não editados à mão. Para regenerar depois de criar um
pôster novo em `projects/<nome>/` (ver README da raiz):

```bash
cd ..
.venv/Scripts/python.exe scripts/build_site_assets.py
```

O script (`scripts/build_site_assets.py`, na raiz do repo) lê os exports de
150 dpi e cada `project.yaml`, recorta a **arte pura** (sem título/margem/
moldura do poster — usa a mesma geometria de `engine.py`) e escreve:

- `<slug>-full.webp` / `-thumb.webp` / `-detail.webp` (recorte 1:1 em alta
  densidade de tinta — é o "zoom" que mostra as letras)
- `works.json` com fonte, corpo em mm, camadas ligadas, dimensão de
  impressão e contagem de glifos

Para adicionar uma obra nova à vitrine: edite as listas `ORDER`, `GLYPHS` e
`BLURB` no topo do script.

## Estrutura

```
site/
├── index.html             pt — fonte da estrutura, marcada com data-i18n
├── build/i18n.js          plugin Vite: gera /en/, /es/ e /it/ na build
├── src/
│   ├── config.js         contatos, preços e domínio (editar antes do deploy)
│   ├── main.js            orquestra os módulos abaixo
│   ├── data/works.json    gerado por scripts/build_site_assets.py
│   ├── i18n/
│   │   ├── locales.js     lista de idiomas (fonte única)
│   │   ├── runtime.js     t() — strings que o JS monta
│   │   └── pt|en|es|it.json
│   ├── styles/
│   └── modules/
│       ├── splitText.js       divide texto em <span> por caractere
│       ├── assemble.js        entrada por scroll (letras se montam)
│       ├── wobble.js          balanço contínuo — homenagem à ondulação de typography.py
│       ├── intro.js           tela de abertura (marca se monta), pulável
│       ├── halftoneCanvas.js  hero vivo em <canvas> — porta conceitual do motor
│       ├── probeCursor.js     leitura tipo instrumento de laboratório (desktop)
│       ├── wipeCompare.js     comparador antes/depois (arrasta pra revelar)
│       ├── gallery.js         cartões da coleção + detalhe em zoom
│       └── briefBuilder.js    monta a mensagem do pedido (link wa.me)
└── public/
    ├── art/    gerado — não editar a mão
    └── fonts/  Archivo Variable + JetBrains Mono (self-hosted, SIL OFL)
```

## Deploy (Vercel)

- **Root Directory:** `site`
- **Framework Preset:** Other
- **Build Command:** `npm run build`
- **Output Directory:** `dist`

Nada a configurar para os idiomas: `/en/`, `/es/` e `/it/` saem como pastas com
`index.html` dentro, igual ao `/admin/` — estático puro, sem regra de rewrite.

## Notas de design

Todo comportamento animado deriva da matemática do próprio motor
(`src/typo/typography.py`): a ondulação da baseline, a rotação por posição,
o mapeamento escuridão→tamanho. Não é decoração solta — é o mesmo laboratório,
rodando no navegador. Ver comentários no topo de `wobble.js` e
`halftoneCanvas.js` para a correspondência exata com as fórmulas do motor.

`prefers-reduced-motion` desliga a entrada, o balanço contínuo e a animação
do hero (fica um frame estático); a montagem por scroll também é pulada
(o texto aparece direto no lugar final).
