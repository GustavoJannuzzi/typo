/**
 * A CENA DA OBRA — animacao conceitual, nao demonstracao de processo.
 *
 * A `cena/processo.html` responde "como isto foi feito": refaz os nove passos
 * do motor num canvas. Esta responde outra pergunta, a que a pessoa faz quando
 * ve a peca pendurada: **"o que e' isso?"**. Nao ha grade, nao ha sonda, nao ha
 * formula. Ha' a frase, a malha, o retrato e a contagem — nesta ordem, que e' a
 * ordem em que a peca se explica sozinha.
 *
 * O argumento e' o do e-mail de entrega (`emails/entrega-emicida.html`):
 *
 *     De longe, e' o Emicida. De perto, e' a musica inteira.
 *
 * Entao a cena faz o olho andar essa distancia duas vezes: uma pra fora (a
 * frase vira malha vira retrato) e uma pra dentro (o retrato vira malha vira
 * palavra contada).
 *
 * ## O contrato com a captura
 *
 *   window.__cena.pronto        Promise que resolve quando tudo carregou
 *   window.__cena.atos          ["abertura", "enxame", ...] na ordem
 *   window.__cena.seek(ato, u)  desenha o ato no progresso u ∈ [0,1]
 *
 * `seek` e' FUNCAO PURA de (ato, u): nao le relogio, nao usa requestAnimationFrame
 * e nao guarda estado entre chamadas. Toda camada tem o seu estilo reescrito a
 * cada chamada, inclusive as que o ato nao usa (e' o que `zerar()` faz) — sem
 * isso um `--de 4 --ate 4` herdaria opacidade de um ato que nao rodou, e o
 * pedaco renderizado sozinho sairia diferente do mesmo pedaco no video inteiro.
 *
 * ## De onde vem cada coisa
 *
 * Medida, titulo, subtitulo e contagem de glifos saem de `works.json` — os
 * mesmos numeros do site, entao nao ha como divergir. O texto editorial (a
 * frase de abertura, as duas glosas e a contagem de palavra) e' de `COPIA`,
 * embaixo: e' redacao, nao dado derivavel, e o lugar honesto dela e' um lugar
 * onde o Gustavo edita sem ler codigo.
 */

import { construir, desenhar } from "./malha.mjs";

const params = new URLSearchParams(location.search);
const SLUG = params.get("obra") || "emicida";

/**
 * Redacao por obra. Os numeros do `emicida` sao os do e-mail de entrega
 * (emails/entrega-emicida.html), contados sobre o mesmo texto que virou a peca.
 *
 * Obra sem entrada aqui ainda roda: cai no `padrao()`, que monta tudo do
 * works.json. So' perde a contagem de palavra, que ninguem consegue adivinhar.
 */
const COPIA = {
  /**
   * `512×` sai de conta, não de chute: a peça tem 188.125 glifos e o trecho do
   * manifesto tem 735 caracteres, o que dá ~256 voltas do texto dentro da
   * gravura; "tupi" aparece 2× por volta. As datas são as das duas obras — a
   * gravura do Debret é de 1834 e o manifesto do Oswald é de 1928 —, e é esse
   * o assunto da peça: o texto de 1928 comendo a imagem de 1834.
   */
  "debret-antropofagia": {
    frase: ["Tupi,", "or not", "tupi"],
    glosas: ["De longe,<br>uma gravura de <em>1834</em>.",
             "De perto,<br>um manifesto de <em>1928</em>."],
    numero: "512×",
    contada: "tupi",
    nota: "é quantas vezes a palavra aparece dentro da gravura. "
        + "O manifesto dá 256 voltas na imagem até fechá-la.",
  },

  /**
   * Aqui o número não é de glifos: o `magalenha` é a única obra da fila cujo
   * motor não roda mais (a foto de referência se perdeu), então não há
   * contagem de glifos confiável pra citar. O que dá pra afirmar com o arquivo
   * na mão é o tamanho do texto — e ele é o dado mais forte da peça de
   * qualquer jeito: o baile inteiro sai de sete frases.
   */
  magalenha: {
    frase: ["Vem,", "Magalenha", "Rojão"],
    glosas: ["De longe,<br>é um <em>baile</em>.", "De perto,<br>é o <em>refrão</em>."],
    numero: "114",
    contada: "letras",
    nota: "é a letra inteira da música — sete frases. "
        + "A imagem toda é isso, repetido até a página fechar.",
  },

  emicida: {
    frase: ["Então", "levanta", "e anda"],
    glosas: ["De longe,<br>é o <em>Emicida</em>.", "De perto,<br>é a <em>música inteira</em>."],
    numero: "357×",
    contada: "levanta",
    nota: "é quantas vezes esta palavra aparece dentro do retrato. "
        + "A letra inteira dá 25 voltas e meia na imagem.",
  },
};

function padrao(meta) {
  return {
    frase: (meta.title || SLUG).split(" ").slice(0, 3),
    glosas: ["De longe,<br>é a <em>imagem</em>.", "De perto,<br>é o <em>texto inteiro</em>."],
    numero: null,
    contada: null,
    nota: "",
  };
}

// --------------------------------------------------------------------------
// curvas — as mesmas de lib/easing.mjs, reescritas aqui porque a cena roda
// dentro do navegador e lib/ nao e' servido
// --------------------------------------------------------------------------

const trava = (v, a = 0, b = 1) => (v < a ? a : v > b ? b : v);
const mistura = (a, b, t) => a + (b - a) * t;
/** o progresso de uma sub-faixa [a,b] dentro do ato, ja' preso em 0..1 */
const janela = (u, a, b) => trava((u - a) / Math.max(1e-6, b - a));
const saida = (t) => 1 - Math.pow(1 - t, 3);
const suave = (t) => t * t * (3 - 2 * t);
const entrada = (t) => t * t * t;

/** ruido estavel por indice — mesma semente, mesmo deslocamento, sempre */
function ruido(i, s) {
  const x = Math.sin(i * 127.1 + s * 311.7) * 43758.5453;
  return x - Math.floor(x);
}

// --------------------------------------------------------------------------
// montagem do DOM — feita uma vez; o seek so' reescreve estilo
// --------------------------------------------------------------------------

const el = {
  quadro: document.querySelector(".obra__quadro"),
  macro: document.querySelector('[data-camada="macro"]'),
  macroImg: document.querySelector("[data-macro]"),
  macro2Img: document.querySelector("[data-macro2]"),
  peca: document.querySelector('[data-camada="peca"]'),
  pecaImg: document.querySelector("[data-peca]"),
  malha: document.querySelector(".obra__malha"),
  malhaCanvas: document.querySelector("[data-malha]"),
  enxame: document.querySelector("[data-enxame]"),
  palavra: document.querySelector("[data-palavra]"),
  ficha: document.querySelector("[data-ficha]"),
  fichaTitulo: document.querySelector("[data-ficha-titulo]"),
  fichaSub: document.querySelector("[data-ficha-sub]"),
  glosa: document.querySelector("[data-glosa]"),
  contagem: document.querySelector("[data-contagem]"),
  numero: document.querySelector("[data-numero]"),
  contada: document.querySelector("[data-contada]"),
  nota: document.querySelector("[data-nota]"),
  assinatura: document.querySelector("[data-assinatura]"),
  arroba: document.querySelector("[data-arroba]"),
};

/**
 * Quantas linhas o enxame tem. Impar, pra existir uma linha do meio: e' nela
 * que a frase do ato anterior continua, e e' o que costura os dois atos.
 *
 * O numero e' dimensionado pelo corpo FINAL (`CORPO_FIM`), nao pelo inicial:
 * no comeco a frase e' enorme e cabem ~12 linhas no quadro, no fim ela e'
 * malha e precisam de ~60 pra encher. Com poucas linhas o enxame termina como
 * uma faixa no meio do branco — que foi exatamente como saiu na primeira
 * versao. O excesso do comeco e' cortado pelo `overflow: hidden` do quadro.
 */
const CORPO_INICIO = 15;   // cqw
const CORPO_FIM = 3.1;     // cqw
const LINHAS = 61;
const MEIO = (LINHAS - 1) / 2;

/**
 * Quantas vezes a frase se repete dentro de UMA linha, e o recuo maximo de
 * cada linha.
 *
 * O recuo e' em `em`, nao em `%`: porcentagem e' da largura do ELEMENTO, que
 * aqui tem dezenas de vezes a largura do quadro — 10% dela jogaria a linha
 * inteira pra fora e abriria um rombo branco na esquerda. Em `em` o
 * deslocamento vale o mesmo tanto de letra em qualquer corpo, e como a linha e'
 * muito mais larga que o quadro mais o recuo, nunca aparece o fim da string.
 */
const REPETE = 14;
const RECUO_MAX = 8;  // em

let letras = [];   // spans da frase, na ordem de leitura
let linhas = [];   // <b> do enxame
let glosas = [];   // <p> das duas leituras

function montar(copia, meta) {
  // --- a frase, letra a letra ---
  el.palavra.innerHTML = "";
  letras = [];
  for (const linha of copia.frase) {
    const p = document.createElement("p");
    for (const ch of linha) {
      const s = document.createElement("span");
      s.textContent = ch === " " ? " " : ch;
      p.appendChild(s);
      letras.push(s);
    }
    el.palavra.appendChild(p);
  }

  // --- o enxame: a mesma frase repetida ate' encher a linha ---
  const corrida = copia.frase.join(" ");
  el.enxame.innerHTML = "";
  linhas = [];
  for (let i = 0; i < LINHAS; i++) {
    const b = document.createElement("b");
    b.textContent = (corrida + " ").repeat(REPETE);
    el.enxame.appendChild(b);
    linhas.push(b);
  }

  // --- as duas glosas ---
  el.glosa.innerHTML = "";
  glosas = copia.glosas.map((texto) => {
    const p = document.createElement("p");
    p.innerHTML = texto;
    el.glosa.appendChild(p);
    return p;
  });

  el.fichaTitulo.textContent = meta.title || SLUG.replace(/-/g, " ");
  el.fichaSub.textContent = meta.subtitle || "";
  el.numero.textContent = copia.numero || "";
  el.contada.textContent = copia.contada || "";

  const glifos = meta.glyphs ? meta.glyphs.toLocaleString("pt-BR") : null;
  const medida = meta.widthCm
    ? `${Math.round(meta.widthCm)} × ${Math.round(meta.heightCm)} cm`
    : null;
  el.nota.innerHTML = [
    copia.nota,
    [glifos && `${glifos} letras desenhadas uma a uma`, medida, meta.font]
      .filter(Boolean).join(" · "),
  ].filter(Boolean).join("<br>");
}

// --------------------------------------------------------------------------
// os atos
// --------------------------------------------------------------------------

const ATOS = ["abertura", "enxame", "montagem", "revelacao", "titulo",
              "mergulho", "contagem", "fecho"];

/** a malha em glifos, construída uma vez no carregamento (ver malha.mjs) */
let MALHA = null;

/**
 * De quanto o ato da montagem começa mais perto.
 *
 * Estas peças são largas e o quadro é 9:16: encaixada inteira, a arte ocupa
 * pouco mais da metade da altura e sobra papel em cima e embaixo. Montar nesse
 * tamanho desperdiça o quadro e deixa a letra pequena demais pra se ler que é
 * letra — que é justamente o que o ato existe pra mostrar. Então a montagem
 * acontece de perto e a câmera recua até o enquadramento da peça, chegando
 * exatamente em `scale(1)`, que é onde a imagem real assume.
 */
const ZOOM_MONTAGEM = 1.9;

/**
 * Supersample do canvas da malha.
 *
 * O canvas é desenhado maior que a tela e reduzido pelo CSS. Sem isso, o zoom
 * de 1,9× do começo da montagem ampliaria o bitmap e as letras chegariam
 * borradas justamente no momento em que estão grandes o suficiente pra alguém
 * reparar nelas.
 */
const SUPER = 1.6;

/**
 * Onde a peca fica quando a placa de especime esta' na tela.
 *
 * Com a peca centrada e a placa no pe, a placa tapa o terco de baixo da arte —
 * e o terco de baixo desta peca sao as maos. Entao a peca **abre espaco pra
 * propria etiqueta**: encolhe e sobe ate' a placa encostar embaixo dela, e
 * nada se cruza. E' a regra da ficha de especime do poster, so' que animada.
 */
/**
 * Os dois foram constantes (0,62 e -21,5cqh) afinadas na mão pro `emicida`, e
 * quebraram na primeira obra de outro formato: a arte do `magalenha` é larga,
 * encaixada no quadro ela já é baixa, e encolher mais 38% deixava um buraco
 * entre ela e a placa. Agora saem de medida — a altura livre acima da placa e a
 * altura que a arte tem quando encaixada — e valem pra qualquer proporção.
 */
let FICHA_ESCALA = 0.62;
let FICHA_SOBE = -21.5;  // cqh

function medirFicha() {
  const fw = el.quadro.clientWidth;
  const fh = el.quadro.clientHeight;
  const aw = el.pecaImg.naturalWidth;
  const ah = el.pecaImg.naturalHeight;
  const placa = document.querySelector(".obra__placa");
  if (!fw || !fh || !aw || !ah || !placa) return;

  // a placa é medida com o layout já montado: a altura dela depende de em
  // quantas linhas o título quebrou, e isso muda de obra pra obra
  const livre = placa.getBoundingClientRect().top;
  const contida = ah * Math.min(fw / aw, fh / ah);

  // 0,94 deixa uma folga entre a arte e o fio da placa; sem ela as duas
  // encostam e a peça parece apoiada na etiqueta
  FICHA_ESCALA = Math.min(1, (livre * 0.94) / contida);
  FICHA_SOBE = ((livre / 2 - fh / 2) / fh) * 100;
}

const pecaEm = (escala, sobeCqh) => {
  el.pecaImg.style.transform =
    `translateY(${sobeCqh.toFixed(2)}cqh) scale(${escala.toFixed(4)})`;
};

/** apaga TODA camada. Todo ato comeca daqui — ver a nota de pureza no topo. */
function zerar() {
  for (const n of [el.macro, el.peca, el.malha, el.enxame, el.palavra, el.ficha,
                   el.glosa, el.contagem]) {
    n.style.opacity = "0";
  }
  el.assinatura.style.opacity = "0";
  el.macroImg.style.transform = "scale(1)";
  el.macro2Img.style.transform = "scale(1)";
  el.malhaCanvas.style.transform = "scale(1)";
  el.ficha.style.transform = "translateY(0)";
  pecaEm(1, 0);
  el.macroImg.style.opacity = "1";
  el.macro2Img.style.opacity = "0";
  el.quadro.style.background = "var(--paper)";
}

/** escala do macro visivel. `qual` escolhe o recorte: 1 = ato 02, 2 = ato 05. */
function macroEscala(escala, qual = 1) {
  const alvo = qual === 2 ? el.macro2Img : el.macroImg;
  const outro = qual === 2 ? el.macroImg : el.macro2Img;
  alvo.style.opacity = "1";
  outro.style.opacity = "0";
  alvo.style.transform = `scale(${escala.toFixed(4)})`;
}

/**
 * 01 — a frase se monta letra a letra.
 *
 * E' o gesto do motor invertido: la' as letras sao colocadas uma a uma ate'
 * virar imagem; aqui elas sao colocadas uma a uma ate' virar frase. As duas
 * pontas do mesmo movimento, e o video inteiro e' a viagem entre elas.
 */
function abertura(u) {
  el.palavra.style.opacity = "1";
  const n = letras.length;
  for (let i = 0; i < n; i++) {
    // cada letra tem a sua janela; a ultima ainda tem 45% do ato pra assentar
    const p = suave(janela(u, 0.55 * (i / Math.max(1, n - 1)), 0.55 * (i / Math.max(1, n - 1)) + 0.45));
    const dx = (ruido(i, 3) * 2 - 1) * 26 * (1 - p);
    const dy = (ruido(i, 7) * 2 - 1) * 22 * (1 - p);
    const rot = (ruido(i, 11) * 2 - 1) * 24 * (1 - p);
    letras[i].style.opacity = p.toFixed(3);
    letras[i].style.transform =
      `translate(${dx.toFixed(2)}px,${dy.toFixed(2)}px) rotate(${rot.toFixed(2)}deg)`;
  }
}

/**
 * 02 — a frase vira malha.
 *
 * A linha do meio encolhe e se repete pros lados; as outras dezesseis entram
 * de dentro pra fora. No fim, o macro real da peca assume por cima — e' o
 * momento em que a simulacao passa o bastao pro arquivo de impressao.
 */
function enxame(u) {
  el.palavra.style.opacity = String(1 - suave(janela(u, 0, 0.22)));
  for (const s of letras) { s.style.opacity = "1"; s.style.transform = "none"; }

  el.enxame.style.opacity = String(suave(janela(u, 0.05, 0.3)));
  const corpo = mistura(CORPO_INICIO, CORPO_FIM, saida(janela(u, 0, 0.72)));
  for (let i = 0; i < LINHAS; i++) {
    const dist = Math.abs(i - MEIO) / MEIO;
    // as linhas de fora so' entram depois das de dentro
    const p = suave(janela(u, 0.06 + dist * 0.42, 0.06 + dist * 0.42 + 0.34));
    linhas[i].style.opacity = (i === MEIO ? 1 : p * mistura(1, 0.62, dist)).toFixed(3);
    linhas[i].style.fontSize = `${corpo.toFixed(3)}cqw`;
    // recuo fixo por linha: alinhadas, as repeticoes viram tabela, e a peca
    // real nao tem coluna nenhuma
    linhas[i].style.transform = `translateX(${(-RECUO_MAX * ruido(i, 17)).toFixed(2)}em)`;
  }

  el.macro.style.opacity = String(suave(janela(u, 0.68, 1)));
  macroEscala(mistura(1.22, 1.0, saida(janela(u, 0.6, 1))), 1);
}

/**
 * As letras chegam de fora e assentam até formarem a peça.
 *
 * É o ato que o vídeo existe pra mostrar, e o único que não é corte nem
 * transição: é a peça sendo *escrita*. Cada glifo tem posição, corpo, peso e
 * tinta calculados pela mesma conta do motor (ver malha.mjs) — a imagem que se
 * fecha no fim é a arte de verdade, não uma nuvem de partículas que lembra
 * ela.
 *
 * No último quinto a peça REAL entra por cima e substitui a malha da cena. A
 * malha aqui é mais grossa que a impressa (52 linhas contra as centenas do
 * arquivo) porque glifo de 1,5 mm num vídeo vertical não se lê; a troca no fim
 * é o que devolve a densidade verdadeira sem que o corte apareça.
 */
function montagem(u) {
  el.palavra.style.opacity = String(1 - suave(janela(u, 0, 0.16)));
  for (const s of letras) { s.style.opacity = "1"; s.style.transform = "none"; }

  el.malha.style.opacity = String(suave(janela(u, 0.02, 0.12)));
  // a câmera recua de ZOOM_MONTAGEM até 1: em 1 a malha cobre exatamente o
  // mesmo retângulo que a imagem real, e por isso a troca no fim não desliza
  // `suave`, e não `saida`: com ease-out o recuo acaba no primeiro terço do
  // ato e as letras passam quase todo o tempo já no tamanho final — o zoom
  // existe justamente pra elas serem grandes ENQUANTO se montam
  const z = mistura(ZOOM_MONTAGEM, 1, suave(janela(u, 0.1, 0.96)));
  el.malhaCanvas.style.transform = `scale(${z.toFixed(4)})`;
  if (MALHA) {
    const ctx = el.malhaCanvas.getContext("2d");
    ctx.clearRect(0, 0, el.malhaCanvas.width, el.malhaCanvas.height);
    desenhar(ctx, MALHA, janela(u, 0, 0.86), "monta");
  }

  // a peça real assume no fim — a malha da cena é grossa demais pra terminar nela
  el.peca.style.opacity = String(suave(janela(u, 0.84, 1)));
  pecaEm(1, 0);
}

/**
 * 03 — o macro recua e o retrato aparece.
 *
 * O zoom sai em escala LOG (o `Math.pow` embaixo), pela mesma razao que a
 * camera do lib/camera.mjs: o olho le velocidade de aproximacao como taxa
 * relativa, e interpolar linear parece que acelera no fim.
 */
function revelacao(u) {
  const t = saida(u);
  el.macro.style.opacity = String(1 - suave(janela(u, 0.42, 0.86)));
  macroEscala(Math.pow(6.2, 1 - t), 1);
  el.peca.style.opacity = String(suave(janela(u, 0.38, 0.9)));
  pecaEm(mistura(1.5, 1.0, saida(janela(u, 0.3, 1))), 0);
}

/** 04 — a peca sobe pra abrir espaco e o bloco de especime entra por baixo. */
function titulo(u) {
  el.peca.style.opacity = "1";
  const p = saida(janela(u, 0.08, 0.7));
  pecaEm(mistura(1, FICHA_ESCALA, p), mistura(0, FICHA_SOBE, p));
  el.ficha.style.opacity = String(p);
  el.ficha.style.transform = `translateY(${((1 - p) * 6).toFixed(2)}cqh)`;
  el.assinatura.style.opacity = "0";
}

/**
 * 05 — o mergulho de volta, com as duas leituras.
 *
 * A peca cresce e entrega pro segundo macro (outro recorte, nao o mesmo do ato
 * 02 — repetir a mesma regiao faria o video parecer que voltou pro comeco). As
 * duas glosas entram uma depois da outra, em placa de papel de corte reto.
 */
function mergulho(u) {
  // parte de onde o ato 04 deixou (encolhida e pra cima) e volta ao centro
  // enquanto mergulha — senao a emenda entre os dois atos e' um salto
  el.peca.style.opacity = String(1 - suave(janela(u, 0.3, 0.62)));
  pecaEm(FICHA_ESCALA * Math.pow(4.4, entrada(janela(u, 0, 0.7))),
         mistura(FICHA_SOBE, 0, saida(janela(u, 0, 0.45))));
  el.ficha.style.opacity = String(1 - suave(janela(u, 0, 0.16)));
  el.assinatura.style.opacity = "0";
  el.macro.style.opacity = String(suave(janela(u, 0.34, 0.66)));
  macroEscala(mistura(2.4, 1.0, saida(janela(u, 0.3, 1))), 2);

  // as duas ficam empilhadas no fim: e' uma frase so' partida em dois tempos,
  // e trocar a primeira pela segunda faria perder a comparacao que ela faz
  glosas.forEach((p, i) => {
    const inicio = 0.2 + i * 0.32;
    const dentro = saida(janela(u, inicio, inicio + 0.22));
    p.style.opacity = String(dentro);
    p.style.transform = `translateX(${((1 - dentro) * -6).toFixed(2)}cqw)`;
  });
  el.glosa.style.opacity = "1";
}

/**
 * 06 — a contagem.
 *
 * O pagamento do video: o numero que so' existe porque a imagem e' feita de
 * texto. Fundo de papel chapado, sem imagem atras — depois de dois mergulhos,
 * o silencio e' o que faz o numero soar.
 */
function contagem(u) {
  el.contagem.style.opacity = String(suave(janela(u, 0, 0.14)));
  const p = saida(janela(u, 0.05, 0.42));
  el.numero.style.transform = `scale(${mistura(0.86, 1, p).toFixed(4)})`;
  el.numero.style.opacity = String(p);
  el.contada.style.opacity = String(saida(janela(u, 0.24, 0.5)));
  el.contada.style.transform = `translateY(${((1 - saida(janela(u, 0.24, 0.5))) * 3).toFixed(2)}cqh)`;
  el.nota.style.opacity = String(saida(janela(u, 0.46, 0.78)));
}

/** 07 — de volta pra peca inteira, com a ficha e a assinatura. */
function fecho(u) {
  el.contagem.style.opacity = String(1 - suave(janela(u, 0, 0.18)));
  el.numero.style.opacity = "1";
  el.numero.style.transform = "scale(1)";
  el.contada.style.opacity = "1";
  el.contada.style.transform = "none";
  el.nota.style.opacity = "1";

  el.peca.style.opacity = String(suave(janela(u, 0.1, 0.4)));
  const p = saida(janela(u, 0.08, 0.8));
  pecaEm(mistura(FICHA_ESCALA * 1.16, FICHA_ESCALA, p), FICHA_SOBE);
  el.ficha.style.opacity = String(suave(janela(u, 0.3, 0.6)));
  el.assinatura.style.opacity = String(suave(janela(u, 0.55, 0.85)));
}

const DESENHO = { abertura, enxame, montagem, revelacao, titulo, mergulho,
                  contagem, fecho };

function seek(ato, u) {
  zerar();
  (DESENHO[ato] || DESENHO[ATOS[0]])(trava(Number(u) || 0));
}

// --------------------------------------------------------------------------
// carga
// --------------------------------------------------------------------------

/**
 * As imagens. O macro sai das avulsas do `build_instagram.py`, que sao recortes
 * **1:1 do export de 150 dpi** — o `-detail.webp` do site tem 1100 px e amolece
 * antes de 3x, e o PNG de 27 MP inteiro nao cabe confortavelmente no navegador.
 * Se as avulsas nao existirem, cai no detail e o mergulho sai mais mole.
 */
function fontes() {
  return {
    macro: [`/social/${SLUG}/avulsas/malha-01.png`, `/art/${SLUG}-detail.webp`],
    macro2: [`/social/${SLUG}/avulsas/malha-03.png`,
             `/social/${SLUG}/avulsas/malha-02.png`,
             `/art/${SLUG}-detail.webp`],
    // `peca.png` das avulsas vem primeiro porque existe pra TODA obra: o
    // `-full.webp` depende do build_site_assets.py, que precisa da imagem de
    // referência — e a do `magalenha` se perdeu, então ele não tem asset de
    // site nenhum.
    peca: [`/social/${SLUG}/avulsas/peca.png`, `/art/${SLUG}-full.webp`],
  };
}

/** tenta os caminhos em ordem e devolve o primeiro que carregou */
function carregar(img, caminhos) {
  return new Promise((ok) => {
    let i = 0;
    const tenta = () => {
      if (i >= caminhos.length) return ok(false);
      const alvo = caminhos[i++];
      img.onload = () => ok(true);
      img.onerror = () => tenta();
      img.src = alvo;
    };
    tenta();
  });
}

const pronto = (async () => {
  const meta = await fetch("/dados/works.json")
    .then((r) => r.json())
    .then((lista) => lista.find((e) => e.slug === SLUG) || {})
    .catch(() => ({}));

  // obra fora do works.json (é o caso do `magalenha`): título, subtítulo e
  // fonte saem do project.yaml, que é a fonte da verdade deles de qualquer
  // jeito. O que não dá pra recuperar é a contagem de glifos, e a ficha já
  // sabe sair sem ela.
  if (!meta.title) {
    const proj = await fetch("/dados/projetos.json")
      .then((r) => r.json()).then((t) => t[SLUG] || {}).catch(() => ({}));
    if (proj.title) meta.title = proj.title;
    if (proj.subtitle) meta.subtitle = proj.subtitle;
    if (proj.fonte) meta.font = proj.fonte;
  }

  const copia = { ...padrao(meta), ...(COPIA[SLUG] || {}) };
  montar(copia, meta);

  const marca = await fetch("/src/config.js").then((r) => r.text()).catch(() => "");
  const arroba = (marca.match(/INSTAGRAM:\s*"([^"]*)"/) || [])[1] || "@ondemoramaspalavras";
  el.arroba.textContent = arroba.startsWith("@") ? arroba : "@" + arroba;

  const src = fontes();
  const [ok1, ok2] = await Promise.all([
    carregar(el.macroImg, src.macro),
    carregar(el.macro2Img, src.macro2),
    carregar(el.pecaImg, src.peca),
    document.fonts ? document.fonts.ready : null,
  ]);
  // sem as avulsas o mergulho ainda roda (o fallback e' o -detail.webp), mas
  // sai mole a partir de ~3x. Avisar em voz alta, como o build_instagram faz.
  if (!ok1 || !ok2) {
    console.warn(`[cena] sem recorte 1:1 pra ${SLUG} — o macro vai sair mole.`
      + ` Rode: python scripts/build_instagram.py ${SLUG}`);
  }

  // --- a malha em glifos ---------------------------------------------------
  // o canvas é dimensionado em pixels de DISPOSITIVO: a captura renderiza num
  // layout de 430 px e entrega 1080, então desenhar em px de CSS sairia com um
  // terço da resolução e as letras da malha viram borrão.
  const dpr = window.devicePixelRatio || 1;
  const cw = Math.round(el.malhaCanvas.clientWidth * dpr * SUPER);
  const chh = Math.round(el.malhaCanvas.clientHeight * dpr * SUPER);
  el.malhaCanvas.width = cw;
  el.malhaCanvas.height = chh;

  const texto = await fetch(`/texto/${SLUG}`)
    .then((r) => (r.ok ? r.text() : ""))
    .then((t) => t.split("\n").filter((l) => !l.trim().startsWith("#")).join(" "))
    .catch(() => "");

  medirFicha();

  if (el.pecaImg.naturalWidth) {
    MALHA = construir(el.pecaImg, texto, [0, 0, cw, chh], {
      fonte: `"${meta.font || "Arial Narrow"}", "Archivo Variable", Georgia, serif`,
    });
    console.info(`[cena] malha: ${MALHA.celulas.length} glifos`);
  } else {
    console.warn("[cena] sem a peça carregada — o ato `montagem` sai vazio");
  }

  seek(ATOS[0], 0);
  document.documentElement.dataset.cenaPronta = "1";
  return true;
})();

window.__cena = { pronto, atos: ATOS, seek };
