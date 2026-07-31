/**
 * COMO NASCE UMA OBRA — 9:16.
 *
 * Os nove atos da cena de processo (video/cena/processo.html), cada um com sua
 * duracao e sua curva. Trocar a ordem, cortar um ato ou dobrar o tempo de um
 * so' e' mexer nesta lista — a cena nao sabe nada sobre ritmo.
 *
 *   ato    qual passo do motor: foto, grade, luminancia, mascara, sonda,
 *          pontos, cores, letras, ficha
 *   dur    segundos
 *   ease   curva do progresso DENTRO do ato (lib/easing.mjs)
 *
 * Trocar a obra: `?obra=<slug>` na url abaixo. Qualquer slug de
 * site/src/data/works.json serve.
 *
 * Pra afinar so' o ato das letras:
 *     node video/render.mjs roteiros/processo-9x16.mjs --de 7 --ate 7 --rascunho
 */
export default {
  nome: "processo-9x16",

  saida: {
    largura: 1080,
    altura: 1920,
    fps: 60,
    ssaa: 1, // ver a nota em tour-9x16.mjs: 2 custa o dobro e ganha pouco
    crf: 17,
    preset: "slow",
  },

  pagina: {
    url: "/cena/processo.html?obra=ouro-marrom",
    largura: 430,
    altura: 764,
    esperar: `document.documentElement.dataset.cenaPronta === "1"`,
  },

  planos: [
    // a foto entra e se assenta
    { nome: "01-foto", ato: "foto", dur: 2.2, ease: "saidaCubica" },

    // o plano cartesiano se desenha por cima
    { nome: "02-plano", ato: "grade", dur: 2.6, ease: "saidaQuinta" },

    // a cortina de luminancia atravessa a bancada
    { nome: "03-luz", ato: "luminancia", dur: 2.4, ease: "vaiEVolta" },

    // o limiar desce e a figura se fecha
    { nome: "04-figura", ato: "mascara", dur: 2.8, ease: "suaveCubica" },

    // a sonda anda medindo — e' o ato que explica o algoritmo
    { nome: "05-sonda", ato: "sonda", dur: 4.2, ease: "linear" },

    // os pontos brotam linha a linha: a imagem aparece sem nenhuma letra
    { nome: "06-densidade", ato: "pontos", dur: 3.6, ease: "saidaCubica" },

    // a tinta entra em cortina, da esquerda pra direita
    { nome: "07-tinta", ato: "cores", dur: 2.6, ease: "vaiEVolta" },

    // o pagamento: os pontos viram texto e no fim a peca real toma a tela.
    // Sem `titulo:` aqui de proposito — a cena ja' desenha o nome do ato no
    // rodape, e a sobreposicao do roteiro batia em cima do cabecalho. A
    // sobreposicao serve pro tour do site, onde nao ha rotulo proprio.
    { nome: "08-palavras", ato: "letras", dur: 6.0, ease: "linear" },

    // a ficha de espécime
    { nome: "09-especime", ato: "ficha", dur: 3.2, ease: "pouso" },
  ],
};
