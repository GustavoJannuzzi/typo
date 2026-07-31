/**
 * TOUR DO SITE — 9:16, para stories e reels.
 *
 * =========================================================================
 *  ESTE ARQUIVO E' O PAINEL DE CONTROLE. Ele e' DADO, nao codigo: mexer aqui
 *  nunca exige mexer no motor de captura. Tudo que da' pra afinar:
 *
 *    dur      quantos segundos o plano dura
 *    ease     a curva do movimento (nomes em lib/easing.mjs)
 *    zoom     numero (1 = tamanho real) ou "largura" / "altura" / "conter"
 *    foco     [x, y] normalizado DENTRO do alvo — [0.5,0.5] e' o centro,
 *             [0.5,0.28] e' "um pouco acima do meio" (rosto, geralmente)
 *    margem   folga em volta quando o zoom e' "conter"/"largura"/"altura"
 *    titulo   texto por cima, na identidade; entra/sai em fracao do plano
 *
 *  Pra afinar SO' um plano, sem re-renderizar o resto:
 *      node video/render.mjs roteiros/tour-9x16.mjs --de 5 --ate 5 --rascunho
 * =========================================================================
 */
export default {
  nome: "tour-9x16",

  saida: {
    largura: 1080,
    altura: 1920,
    fps: 60,
    // ssaa 1 ja' captura com densidade 2,51x (1080 de saida / 430 de layout) —
    // o texto ja' sai renderizado em alta densidade e suavizado pelo navegador.
    // ssaa 2 leva a densidade a 5x e reduz com lanczos: ganho pequeno, custo
    // dobrado (0,96 s/frame contra 0,52). Deixe em 1 e suba pra 2 so' na
    // passada final, se voce vir diferenca que justifique.
    ssaa: 1,
    crf: 17,   // 17 otimo · 20 bom e leve · 23 padrao
    preset: "slow",
  },

  pagina: {
    url: "/",
    // o tamanho de LAYOUT (CSS). 430 e' largura de celular grande: a landing e'
    // mobile-first, entao e' assim que ela foi desenhada pra ser vista.
    largura: 430,
    altura: 764,
    esperar: `document.querySelectorAll(".gallery-card").length > 0`,
  },

  planos: [
    {
      nome: "abertura",
      tipo: "camera",
      de: { alvo: "#top", zoom: "largura", margem: 0, foco: [0.5, 0.42] },
      para: { alvo: "#top", zoom: "largura", margem: 0, foco: [0.5, 0.5] },
      dur: 2.6,
      ease: "linear",
      titulo: { texto: "Onde moram as palavras", sub: "laboratório tipográfico", posicao: "centro", entra: 0.3, sai: 0.22 },
    },
    {
      nome: "manifesto",
      para: { alvo: "#manifesto", zoom: "largura", margem: 0.02 },
      dur: 2.2,
      ease: "vaiEVolta",
    },
    {
      nome: "chega-na-colecao",
      para: { alvo: "#colecao", zoom: "largura", margem: 0.02, foco: [0.5, 0.3] },
      dur: 2.0,
      ease: "vaiEVolta",
      titulo: { texto: "Nove espécimes", sub: "a coleção", posicao: "baixo" },
    },
    {
      nome: "passeia-na-vitrine",
      para: { alvo: '.gallery-card[data-slug="nossa-senhora"]', zoom: 1.15, foco: [0.5, 0.4] },
      dur: 2.4,
      ease: "suaveCubica",
    },

    // --- o mergulho: e' aqui que se descobre que a imagem e' feita de letra --
    {
      nome: "escolhe-a-obra",
      para: { alvo: '.gallery-card[data-slug="ouro-marrom"] img', zoom: "largura", margem: 0.08 },
      dur: 1.8,
      ease: "pouso",
    },
    {
      nome: "abre-a-obra",
      tipo: "acao",
      faz: "abrirObra",
      args: ["ouro-marrom"],
      dur: 0.35,
    },
    {
      nome: "mergulho",
      // o `-detail.webp` e' um recorte 1:1 do export de 150 dpi: e' o unico
      // asset com resolucao pra aguentar zoom. Ver a nota sobre TETO DE ZOOM
      // no fim deste arquivo.
      // comeca com a obra JA' preenchendo o quadro. Com "conter" sobrava
      // moldura do modal em volta (barra do botao, "fechar") e o plano abria
      // mostrando o site, nao a peca.
      // "altura" e nao "largura": o recorte de detalhe e' QUADRADO e o quadro
      // e' 9:16 — enquadrando pela largura sobra pagina em cima e embaixo.
      de: { alvo: "[data-gallery-detail-img]", zoom: "altura", margem: 0 },
      para: { alvo: "[data-gallery-detail-img]", zoom: 3.0, foco: [0.44, 0.46] },
      dur: 3.4,
      ease: "saidaExpo",
      titulo: { texto: "de perto", sub: "35.880 glifos · Bookman Old Style · 3,4 mm", posicao: "baixo", entra: 0.4, sai: 0.15 },
    },
    {
      nome: "respira-no-macro",
      tipo: "espera",
      dur: 1.2,
    },
    {
      nome: "recua",
      para: { alvo: "[data-gallery-detail-img]", zoom: "conter", margem: 0.06 },
      dur: 2.0,
      ease: "suaveQuinta",
    },
    {
      nome: "fecha",
      tipo: "acao",
      faz: "fecharObra",
      dur: 0.3,
    },

    // --- o antes/depois, que conta a mesma historia por outro gesto ---------
    {
      nome: "vai-pro-comparador",
      para: { alvo: "[data-compare-frame]", zoom: "conter", margem: 0.06 },
      dur: 2.0,
      ease: "vaiEVolta",
      titulo: { texto: "da foto à obra", sub: "arraste para revelar", posicao: "alto" },
    },
    { nome: "revela-1", tipo: "acao", faz: "comparar", args: [12], dur: 0.5 },
    { nome: "revela-2", tipo: "acao", faz: "comparar", args: [50], dur: 0.5 },
    { nome: "revela-3", tipo: "acao", faz: "comparar", args: [88], dur: 0.9 },

    // --- o fecho -----------------------------------------------------------
    {
      nome: "encomenda",
      para: { alvo: "#pedido", zoom: "largura", margem: 0.03, foco: [0.5, 0.2] },
      dur: 2.4,
      ease: "vaiEVolta",
      titulo: { texto: "sua história", sub: "monte seu pedido", posicao: "baixo", entra: 0.3, sai: 0.25 },
    },
  ],
};

/*
 * TETO DE ZOOM — vale saber antes de aumentar os numeros acima.
 *
 * Os assets do site tem resolucao finita:
 *     <slug>-full.webp     1600 px no lado maior
 *     <slug>-detail.webp   1100 x 1100 (recorte 1:1 do export de 150 dpi)
 *
 * Num quadro de 1080 px de largura, a arte inteira ja ocupa ~1000 px. Logo:
 *   - sobre o `-full`, da' pra empurrar ate' ~1,5x antes de amolecer
 *   - sobre o `-detail`, 1,0x ja e' pixel a pixel; ate' ~2,6x ainda le' bem
 *     porque o detalhe foi cortado da malha mais densa da peca
 *
 * Zoom maior que isso pede asset maior, e asset maior pede os exports de
 * 150 dpi de volta em projects/<slug>/output/ (hoje a pasta esta vazia) e um
 * `scripts/build_site_assets.py` gerando um `-macro` de 2400 px. Enquanto isso
 * nao existe, os numeros acima sao o teto honesto.
 */
