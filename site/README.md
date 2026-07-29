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
  LAUNCH_SLOTS_TAKEN: 0,           // atualize conforme forem vendendo
  // ...
};
```

Sem `WHATSAPP` preenchido, o botão "Enviar pelo WhatsApp" ainda funciona mas
abre `wa.me/` sem número de destino — **não esqueça de preencher antes do
deploy**.

## Rodar local

```bash
npm install
npm run dev       # http://127.0.0.1:5173
```

```bash
npm run build      # gera dist/
npm run preview    # serve dist/ para conferir o build de producao
```

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
├── index.html
├── src/
│   ├── config.js         contatos e preços (editar antes do deploy)
│   ├── main.js            orquestra os módulos abaixo
│   ├── data/works.json    gerado por scripts/build_site_assets.py
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

## Notas de design

Todo comportamento animado deriva da matemática do próprio motor
(`src/typo/typography.py`): a ondulação da baseline, a rotação por posição,
o mapeamento escuridão→tamanho. Não é decoração solta — é o mesmo laboratório,
rodando no navegador. Ver comentários no topo de `wobble.js` e
`halftoneCanvas.js` para a correspondência exata com as fórmulas do motor.

`prefers-reduced-motion` desliga a entrada, o balanço contínuo e a animação
do hero (fica um frame estático); a montagem por scroll também é pulada
(o texto aparece direto no lugar final).
