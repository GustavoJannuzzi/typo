/**
 * MAGALENHA — 20 s, 9:16.
 *
 * Mesma cena do `emicida-9x16.mjs` (video/cena/obra.html), outro arranjo. A
 * diferenca esta' no centro: aqui o ato que carrega o video e' a **montagem**,
 * em que as letras chegam de fora e assentam ate' formarem a peca — a mesma
 * conta do motor, refeita em canvas (ver cena/malha.mjs). Os atos `enxame` e
 * `revelacao`, que no emicida faziam esse trabalho por metafora, saem: com a
 * montagem no meio eles contariam a mesma coisa duas vezes.
 *
 * Em 20 s cada corte tem que pagar mais rapido, entao so' a montagem passa dos
 * 5 s. As transicoes sao curtas de proposito — o ritmo e' o da musica, que e'
 * um baile.
 *
 * O `magalenha` e' a unica obra da fila cujo motor nao roda mais: a foto de
 * referencia se perdeu (ver "Estado" no CLAUDE.md). A cena nao usa o motor —
 * usa o PNG exportado, via `social/magalenha/avulsas/`. Se as avulsas nao
 * existirem, rode antes:
 *
 *     python scripts/build_instagram.py magalenha
 *
 * Pra afinar so' a montagem:
 *     node video/render.mjs video/roteiros/magalenha-9x16.mjs --de 1 --ate 1 --rascunho
 */
export default {
  nome: "magalenha-9x16",

  saida: {
    largura: 1080,
    altura: 1920,
    fps: 60,
    ssaa: 1,
    crf: 20,
    preset: "slow",
  },

  pagina: {
    url: "/cena/obra.html?obra=magalenha",
    largura: 430,
    altura: 764,
    esperar: `document.documentElement.dataset.cenaPronta === "1"`,
  },

  planos: [
    // "Vem, Magalenha Rojão" se monta letra a letra
    { nome: "01-frase", ato: "abertura", dur: 2.4, ease: "saidaCubica" },

    // O ATO: as letras chegam de fora e viram a peca
    { nome: "02-montagem", ato: "montagem", dur: 6.8, ease: "linear" },

    // a peca em repouso, com o bloco de especime
    { nome: "03-especime", ato: "titulo", dur: 2.4, ease: "pouso" },

    // mergulha na malha, com as duas leituras
    { nome: "04-de-perto", ato: "mergulho", dur: 4.2, ease: "suaveCubica" },

    // 114 letras — a letra inteira da musica
    { nome: "05-contagem", ato: "contagem", dur: 2.2, ease: "linear" },

    // plano geral com a ficha e a assinatura
    { nome: "06-fecho", ato: "fecho", dur: 2.0, ease: "pouso" },
  ],
};
