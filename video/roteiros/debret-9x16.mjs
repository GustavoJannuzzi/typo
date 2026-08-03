/**
 * TUPI OR NOT TUPI — 20 s, 9:16.
 *
 * Mesma cena e mesmo arranjo do `magalenha-9x16.mjs`: a **montagem** no centro,
 * as letras chegando de fora ate' formarem a peca (ver cena/malha.mjs).
 *
 * Aqui a montagem nao e' so' o efeito bonito do video — e' o assunto da obra.
 * A peca e' o Manifesto Antropofago de 1928 desenhando uma gravura do Debret de
 * 1834: o texto come a imagem, que e' literalmente a tese do manifesto. Ver as
 * letras chegarem e a gravura colonial aparecer feita delas e' a antropofagia
 * acontecendo. Por isso este e' o ato mais longo, e por isso as duas leituras
 * do ato 04 dizem as duas datas em vez de "de longe / de perto".
 *
 * A obra usa layout `display` (as letras gigantes de TUPI sangram pela margem),
 * entao a "arte" aqui e' a pagina inteira — e' assim que o build_site_assets e
 * o build_instagram ja' a tratam.
 *
 * Pra afinar so' a montagem:
 *     node video/render.mjs video/roteiros/debret-9x16.mjs --de 1 --ate 1 --rascunho
 */
export default {
  nome: "debret-9x16",

  saida: {
    largura: 1080,
    altura: 1920,
    fps: 60,
    ssaa: 1,
    crf: 20,
    preset: "slow",
  },

  pagina: {
    url: "/cena/obra.html?obra=debret-antropofagia",
    largura: 430,
    altura: 764,
    esperar: `document.documentElement.dataset.cenaPronta === "1"`,
  },

  planos: [
    // "Tupi, or not tupi" se monta letra a letra
    { nome: "01-frase", ato: "abertura", dur: 2.4, ease: "saidaCubica" },

    // O ATO: o manifesto de 1928 desenhando a gravura de 1834
    { nome: "02-montagem", ato: "montagem", dur: 6.8, ease: "linear" },

    // a peca em repouso, com o bloco de especime
    { nome: "03-especime", ato: "titulo", dur: 2.4, ease: "pouso" },

    // mergulha na malha: 1834 de longe, 1928 de perto
    { nome: "04-de-perto", ato: "mergulho", dur: 4.2, ease: "suaveCubica" },

    // 512x tupi
    { nome: "05-contagem", ato: "contagem", dur: 2.2, ease: "linear" },

    // plano geral com a ficha e a assinatura
    { nome: "06-fecho", ato: "fecho", dur: 2.0, ease: "pouso" },
  ],
};
