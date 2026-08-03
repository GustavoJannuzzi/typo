/**
 * A MALHA — a arte redesenhada como glifos, e a animacao de montagem.
 *
 * Isto nao e' um efeito de particula por cima de uma foto. E' a mesma conta que
 * o motor faz em `src/typo/typography.py`, refeita em canvas: varre a peca por
 * linhas, mede a escuridao local em cada parada, mapeia a escuridao pro corpo
 * da letra, e avanca pela largura do glifo que acabou de desenhar. Por isso as
 * letras que se juntam no fim formam a arte de verdade, e nao uma aproximacao
 * que so' parece com ela de longe.
 *
 * Tres decisoes herdadas do motor, e cada uma se ve quando falta:
 *
 * 1. **O avanco e' variavel.** A proxima posicao fica a `largura_do_glifo *
 *    avanco` da atual, nao num passo de coluna fixo. Com passo fixo as letras
 *    grandes das areas escuras se atropelam — coisa que a peca impressa nao
 *    faz.
 * 2. **A tinta sai da propria arte**, amostrada no ponto onde o glifo cai. E'
 *    de graca, e e' o que faz o accent terracota do `magalenha` aparecer sem
 *    ninguem escrever cor nenhuma aqui.
 * 3. **A baseline ondula** e o glifo gira junto. Reta, a malha vira tabela.
 *
 * ## A montagem
 *
 * Cada glifo tem um instante de chegada proprio e entra vindo de FORA do
 * quadro, girando e crescendo ate' o lugar exato. O instante nao e' aleatorio
 * puro: e' ordenado por uma onda diagonal com ruido por cima, entao a imagem se
 * fecha como uma varredura desfocada em vez de piscar em pontos soltos.
 *
 * `desenhar()` e' funcao pura de `u` — nao le relogio e nao guarda estado entre
 * chamadas. E' o que deixa a captura frame a frame ser reproduzivel.
 */

/** proporcoes herdadas do motor (ver P em processo.mjs e typography.py) */
export const PADRAO = {
  linhas: 52,
  razaoLinha: 0.95,
  razaoColuna: 0.62,
  avanco: 1.02,
  corpoMin: 0.34,
  corpoMax: 1.6,
  gamma: 1.35,
  negritoEm: 0.58,
  ondulacao: 0.4,
  ondaFrac: 0.5,
  rotGrausMax: 15,
  rotOndaFrac: 0.22,
  /** piso de escuridao abaixo do qual nao se desenha nada (papel) */
  piso: 0.08,
  /** resolucao horizontal da sondagem */
  amostraX: 300,
};

const trava = (v, a = 0, b = 1) => (v < a ? a : v > b ? b : v);
const suave = (t) => t * t * (3 - 2 * t);
const saida = (t) => 1 - Math.pow(1 - t, 3);

function ruido(i, s) {
  const x = Math.sin(i * 127.1 + s * 311.7) * 43758.5453;
  return x - Math.floor(x);
}

/** reduz uma imagem (ou um pedaco dela) pra uma grade w x h com suavizacao */
function amostrar(img, w, h, caixa) {
  const c = document.createElement("canvas");
  c.width = w;
  c.height = h;
  const x = c.getContext("2d", { willReadFrequently: true });
  x.imageSmoothingEnabled = true;
  x.imageSmoothingQuality = "high";
  const [sx, sy, sw, sh] = caixa;
  x.drawImage(img, sx, sy, sw, sh, 0, 0, w, h);
  return x.getImageData(0, 0, w, h);
}

/**
 * Monta a tabela de celulas — uma entrada por glifo, com tudo que nao depende
 * do tempo ja' resolvido. `desenhar()` so' le' daqui.
 *
 * `caixa` e' o retangulo do quadro (em px de canvas) onde a peca mora; a arte
 * e' encaixada nele em `contain`, que e' como a peca aparece impressa.
 */
export function construir(arte, texto, caixa, opcoes = {}) {
  const P = { ...PADRAO, ...opcoes };
  const [cx, cy, cw, ch] = caixa;

  // a peca dentro do quadro, em `contain`
  const aw = arte.naturalWidth || arte.width;
  const ah = arte.naturalHeight || arte.height;
  const escala = Math.min(cw / aw, ch / ah);
  const pw = aw * escala;
  const ph = ah * escala;
  const px = cx + (cw - pw) / 2;
  const py = cy + (ch - ph) / 2;

  const linhas = P.linhas;
  const passoLinha = ph / linhas;
  const corpoBase = passoLinha / P.razaoLinha;

  const cols = P.amostraX;
  const dados = amostrar(arte, cols, linhas, [0, 0, aw, ah]).data;
  // a tinta e' amostrada mais fino e pelo pixel mais ESCURO de cada bloco:
  // pegar o centro sortearia o branco do papel entre duas letras
  const sub = 3;
  const finos = amostrar(arte, cols * sub, linhas * sub, [0, 0, aw, ah]).data;

  const lumDe = (ix, r) => {
    const i = (ix + r * cols) * 4;
    return (0.299 * dados[i] + 0.587 * dados[i + 1] + 0.114 * dados[i + 2]) / 255;
  };
  const tintaDe = (ix, r) => {
    let melhor = 1e9;
    let rgb = [17, 17, 17];
    for (let sy = 0; sy < sub; sy++) {
      for (let sx = 0; sx < sub; sx++) {
        const p = ((ix * sub + sx) + (r * sub + sy) * cols * sub) * 4;
        const v = 0.299 * finos[p] + 0.587 * finos[p + 1] + 0.114 * finos[p + 2];
        if (v < melhor) {
          melhor = v;
          rgb = [finos[p], finos[p + 1], finos[p + 2]];
        }
      }
    }
    return `rgb(${rgb[0]},${rgb[1]},${rgb[2]})`;
  };

  const onda = Math.max(60, pw * P.ondaFrac);
  const ondaRot = Math.max(50, pw * P.rotOndaFrac);
  const amp = corpoBase * P.ondulacao;

  // medidor de largura, com cache: sao milhares de measureText e o par
  // (caractere, corpo arredondado) se repete o tempo todo
  const regua = document.createElement("canvas").getContext("2d");
  const fam = P.fonte;
  const cache = new Map();
  const largura = (ch_, px_, negrito) => {
    const k = `${ch_}|${px_.toFixed(1)}|${negrito ? 1 : 0}`;
    let v = cache.get(k);
    if (v === undefined) {
      regua.font = `${negrito ? 700 : 400} ${px_.toFixed(2)}px ${fam}`;
      v = regua.measureText(ch_).width;
      cache.set(k, v);
    }
    return v;
  };

  const limpo = (texto || "").replace(/\s+/g, " ").trim() || "onde moram as palavras ";
  let iChar = 0;
  const proximo = () => {
    const c = limpo[iChar % limpo.length];
    iChar++;
    return c === " " ? limpo[iChar++ % limpo.length] : c;
  };

  const celulas = [];
  for (let r = 0; r < linhas; r++) {
    const yBase = py + (r + 0.5) * passoLinha;
    let x = px;
    let guarda = 0;
    while (x < px + pw && guarda++ < 4000) {
      const ix = Math.min(cols - 1, Math.max(0, Math.floor(((x - px) / pw) * cols)));
      const escuro = trava(1 - lumDe(ix, r));

      if (escuro < P.piso) {
        x += corpoBase * P.razaoColuna;
        continue;
      }

      const corpo = corpoBase * (P.corpoMin + (P.corpoMax - P.corpoMin) * Math.pow(escuro, P.gamma));
      const negrito = escuro > P.negritoEm;
      const ch_ = proximo();
      const w = largura(ch_, corpo, negrito);

      celulas.push({
        x,
        y: yBase + Math.sin((x - px) / onda) * amp,
        corpo,
        ch: ch_,
        negrito,
        cor: tintaDe(ix, r),
        rot: (Math.sin((x - px) / ondaRot) * P.rotGrausMax * Math.PI) / 180,
      });

      x += Math.max(corpo * 0.22, w * P.avanco);
    }
  }

  // ordem de chegada: onda diagonal + ruido. Aleatorio puro pisca em pontos
  // soltos; diagonal pura vira cortina de loja. A soma fecha a imagem como uma
  // varredura desfocada, que e' o que deixa ler "isto esta' se montando".
  const diag = (c) => ((c.x - px) / Math.max(1, pw)) * 0.45 + ((c.y - py) / Math.max(1, ph)) * 0.55;
  celulas.forEach((c, i) => {
    c.ordem = trava(diag(c) * 0.72 + ruido(i, 5) * 0.28);
    c.semente = i;
  });

  return { celulas, caixaPeca: [px, py, pw, ph], fonte: fam, corpoBase };
}

/**
 * Desenha a malha no progresso `u`.
 *
 * `modo`:
 *   "monta"     as letras chegam de fora e assentam   (u 0 -> 1)
 *   "pronta"    tudo no lugar, sem animacao
 *   "dispersa"  o inverso de "monta"                  (u 0 -> 1)
 *
 * `alcance` e' o quao longe o glifo comeca, em fracao da diagonal do quadro.
 */
export function desenhar(ctx, malha, u, modo = "monta", opcoes = {}) {
  const { alcance = 0.55, janela = 0.42, giro = 2.6 } = opcoes;
  const [px, py, pw, ph] = malha.caixaPeca;
  const diagonal = Math.hypot(pw, ph) * alcance;
  const t = trava(u);

  ctx.save();
  ctx.textAlign = "left";
  ctx.textBaseline = "alphabetic";

  for (const c of malha.celulas) {
    let p;
    if (modo === "pronta") {
      p = 1;
    } else {
      const inicio = c.ordem * (1 - janela);
      const bruto = trava((t - inicio) / janela);
      p = modo === "dispersa" ? 1 - suave(bruto) : suave(bruto);
    }
    if (p <= 0.002) continue;

    const q = saida(p);
    let x = c.x;
    let y = c.y;
    let rot = c.rot;
    let corpo = c.corpo;
    let alfa = 1;

    if (p < 1) {
      const ang = ruido(c.semente, 13) * Math.PI * 2;
      const dist = diagonal * (1 - q);
      x += Math.cos(ang) * dist;
      y += Math.sin(ang) * dist;
      rot += (ruido(c.semente, 29) * 2 - 1) * giro * (1 - q);
      // o corpo chega junto com a posicao: letra que aparece ja' no tamanho
      // final parece colada, nao pousada
      corpo *= 0.45 + 0.55 * q;
      alfa = trava(p * 1.6);
    }

    ctx.globalAlpha = alfa;
    ctx.fillStyle = c.cor;
    ctx.font = `${c.negrito ? 700 : 400} ${corpo.toFixed(2)}px ${malha.fonte}`;
    if (rot) {
      // save/restore por glifo, e nao `setTransform(identidade)`: a identidade
      // apagaria tambem a escala que o chamador tenha posto por densidade de
      // pixel, e a malha sairia do tamanho errado em tela retina
      ctx.save();
      ctx.translate(x, y);
      ctx.rotate(rot);
      ctx.fillText(c.ch, 0, 0);
      ctx.restore();
    } else {
      ctx.fillText(c.ch, x, y);
    }
  }

  ctx.restore();
}
