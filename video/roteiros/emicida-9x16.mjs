/**
 * O GLORIOSO RETORNO — 30 s, 9:16.
 *
 * NAO e' o video de processo. O `processo-9x16.mjs` responde "como isto foi
 * feito" e refaz os nove passos do motor; este responde "o que e' isso",
 * que e' a pergunta de quem ve a peca pendurada. A cena e a
 * `cena/obra.html`.
 *
 * O argumento e' a frase do e-mail de entrega:
 *
 *     De longe, e' o Emicida. De perto, e' a musica inteira.
 *
 * Entao o video anda essa distancia duas vezes — pra fora nos atos 01..04 (a
 * frase vira malha vira retrato) e pra dentro nos atos 05..06 (o retrato vira
 * malha vira palavra contada) — e volta pro plano geral no fim.
 *
 *   ato    passo da cena/obra.mjs: abertura, enxame, revelacao, titulo,
 *          mergulho, contagem, fecho
 *   dur    segundos — a soma das sete e' 30,0
 *   ease   curva do progresso DENTRO do ato (lib/easing.mjs)
 *
 * O ritmo e' o do argumento, nao o do relogio: os dois atos que carregam o
 * sentido (o mergulho e a contagem) tem quase 40% do tempo, e os dois de
 * transicao passam rapido de proposito.
 *
 * Trocar a obra: `?obra=<slug>` na url abaixo. Qualquer slug de works.json
 * roda; a redacao especifica (a contagem de "levanta") esta' na tabela COPIA
 * da cena, e obra sem entrada la' cai num texto generico.
 *
 * Pra afinar so' a contagem:
 *     node video/render.mjs video/roteiros/emicida-9x16.mjs --de 5 --ate 5 --rascunho
 */
export default {
  nome: "emicida-9x16",

  saida: {
    largura: 1080,
    altura: 1920,
    fps: 60,
    ssaa: 1, // ver a nota de custo no video/README.md: 2 custa o dobro e ganha pouco
    crf: 17,
    preset: "slow",
  },

  pagina: {
    url: "/cena/obra.html?obra=emicida",
    largura: 430,
    altura: 764,
    esperar: `document.documentElement.dataset.cenaPronta === "1"`,
  },

  planos: [
    // a frase se monta letra a letra — o gesto do motor invertido
    { nome: "01-frase", ato: "abertura", dur: 3.4, ease: "saidaCubica" },

    // a frase se repete ate' virar malha, e o macro real assume
    { nome: "02-malha", ato: "enxame", dur: 3.6, ease: "linear" },

    // recua: a malha vira retrato. E' o "de longe, e' o Emicida"
    { nome: "03-retrato", ato: "revelacao", dur: 4.2, ease: "saidaQuinta" },

    // a peca em repouso, com o bloco de especime
    { nome: "04-especime", ato: "titulo", dur: 3.2, ease: "pouso" },

    // mergulha de volta, agora com as duas leituras escritas
    { nome: "05-de-perto", ato: "mergulho", dur: 5.8, ease: "suaveCubica" },

    // a contagem: 357x levanta. O pagamento do video
    { nome: "06-contagem", ato: "contagem", dur: 5.8, ease: "linear" },

    // plano geral com a ficha e a assinatura
    { nome: "07-fecho", ato: "fecho", dur: 4.0, ease: "pouso" },
  ],
};
