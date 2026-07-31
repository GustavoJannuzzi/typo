/**
 * "Como nasce uma obra" — a cena do processo de criacao.
 *
 * Nove atos que refazem, na tela, os passos que o motor da em
 * `src/typo/engine.py`: a foto entra, ganha um plano cartesiano, vira
 * luminancia, a mascara separa a figura do fundo, a sonda mede a escuridao
 * local, os pontos aparecem no tamanho que a escuridao pediu, a paleta pinta,
 * e por fim os pontos viram LETRAS.
 *
 * Como no `site/src/modules/halftoneCanvas.js`, isto e uma porta conceitual do
 * motor, nao uma reimplementacao dele: as formulas de mapeamento sao as
 * mesmas, a malha e' mais grossa (a peca real tem centenas de linhas; aqui a
 * malha precisa ser LEGIVEL num video vertical). Os numeros verdadeiros da
 * peca aparecem nas leituras, entao a diferenca fica dita, nao escondida.
 *
 *   lum      = (0.299r + 0.587g + 0.114b) / 255        (image_prep.py)
 *   mascara  = lum < lum_threshold                     (mask.py)
 *   dk       = escuridao^gamma                         (typography.py)
 *   corpo    = size_min + (size_max - size_min) * dk
 *   negrito  = dk > bold_threshold
 *   baseline = yb + amp*sin(2*pi*x/onda + fase_da_linha)
 *   rotacao  = rot_amp*sin(2*pi*x/onda_rot + fase), com clamp
 *
 * -------------------------------------------------------------------------
 * CONTRATO COM A CAPTURA — e o que torna o video determinístico:
 *
 *   window.__cena.pronto        Promise que resolve quando tudo carregou
 *   window.__cena.atos          ["foto", "grade", ...] na ordem
 *   window.__cena.seek(ato, u)  desenha o ato no progresso u ∈ [0,1]
 *
 * `seek` e uma FUNCAO PURA de (ato, u): nao le relogio, nao usa
 * requestAnimationFrame, nao guarda estado entre chamadas alem do que foi
 * pre-computado. Chamar seek("letras", 0.5) mil vezes desenha o mesmo frame
 * mil vezes. E por isso que o video sai igual toda vez que roda.
 * -------------------------------------------------------------------------
 */

/** parametros afinaveis — sobrescreva por query string ou por __cena.configurar() */
const P = {
  obra: "ouro-marrom",
  /** linhas da malha da CENA (a peca real tem muito mais; ver leitura "malha") */
  linhas: 44,
  /** razoes herdadas do halftoneCanvas: mesma proporcao de avanco do motor */
  razaoLinha: 0.95,
  /** passo horizontal nas areas claras, onde nao ha glifo pra medir */
  razaoColuna: 0.62,
  /** layout.advance_factor do motor: avanco = largura_do_glifo * este fator */
  avanco: 1.02,
  corpoMin: 0.34,
  corpoMax: 1.6,
  gamma: 1.35,
  negritoEm: 0.58,
  /** ondulacao da baseline e rotacao do glifo, em fracao do corpo */
  ondulacao: 0.4,
  ondaFrac: 0.5,
  rotGrausMax: 15,
  rotOndaFrac: 0.22,
  /** limiar da mascara, 0..1 em luminancia (mask.lum_threshold do motor) */
  limiar: 0.55,
  /** piso de escuridao abaixo do qual nao se desenha nada */
  piso: 0.08,
  /** sonda: quantas paradas o instrumento faz ao varrer a bancada */
  paradasSonda: 26,
};

const ATOS = [
  "foto",
  "grade",
  "luminancia",
  "mascara",
  "sonda",
  "pontos",
  "cores",
  "letras",
  "ficha",
];

const TITULO_ATO = {
  foto: "A referência",
  grade: "O plano",
  luminancia: "A luz",
  mascara: "A figura",
  sonda: "A sonda",
  pontos: "A densidade",
  cores: "A tinta",
  letras: "As palavras",
  ficha: "O espécime",
};

const GLOSA_ATO = {
  foto: "Uma imagem que já existe. Uma foto, uma capa, uma gravura.",
  grade: "A página vira medida: centímetros de papel, milímetros de letra.",
  luminancia: "A cor sai de cena. O que interessa agora é só quanto de luz há em cada ponto.",
  mascara: "Abaixo do limiar é figura, acima é fundo. A silhueta se separa sozinha.",
  sonda: "Em cada posição o motor mede a escuridão local e pergunta: de que tamanho é esta letra?",
  pontos: "Escuro pede corpo grande. Claro pede corpo pequeno. A imagem já está aqui, sem nenhuma letra.",
  cores: "A tinta vem da própria referência — cada glifo herda a cor do que estava naquele ponto.",
  letras: "Os pontos viram texto. A letra da música, em ordem, do começo ao fim.",
  ficha: "Fonte, corpo, camadas, dimensão de impressão. Cada peça catalogada.",
};

// ---------------------------------------------------------------------------
// utilidades
// ---------------------------------------------------------------------------

const clamp01 = (v) => (v < 0 ? 0 : v > 1 ? 1 : v);
const mix = (a, b, t) => a + (b - a) * t;
const suave = (t) => t * t * (3 - 2 * t);
const saidaCubica = (t) => 1 - Math.pow(1 - t, 3);

/** ruido deterministico por indice — substitui Math.random(), que quebraria a paridade */
function ruido(i, semente = 1) {
  const x = Math.sin(i * 127.1 + semente * 311.7) * 43758.5453;
  return x - Math.floor(x);
}

/** progresso escalonado: item i de n entra dentro de uma janela de largura `janela` */
function cascata(u, i, n, janela = 0.35) {
  const inicio = (1 - janela) * (n <= 1 ? 0 : i / (n - 1));
  return clamp01((u - inicio) / janela);
}

function lerCor(nome, alternativa) {
  const v = getComputedStyle(document.documentElement).getPropertyValue(nome).trim();
  return v || alternativa;
}

async function carregarImagem(src) {
  const img = new Image();
  img.crossOrigin = "anonymous";
  img.src = src;
  await img.decode();
  return img;
}

/** desenha `img` (ja recortada) reduzida para w x h e devolve o ImageData */
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

/** fechamento morfologico barato (dilata e depois erode) — tapa os furos da mascara */
function fechar(mask, w, h, raio = 1) {
  const passo = (fonte, alvo, querVizinho) => {
    for (let y = 0; y < h; y++) {
      for (let x = 0; x < w; x++) {
        let achou = false;
        for (let dy = -raio; dy <= raio && !achou; dy++) {
          for (let dx = -raio; dx <= raio; dx++) {
            const yy = y + dy, xx = x + dx;
            const v = yy < 0 || yy >= h || xx < 0 || xx >= w ? 0 : fonte[yy * w + xx];
            if (v === querVizinho) { achou = true; break; }
          }
        }
        alvo[y * w + x] = querVizinho === 1 ? (achou ? 1 : 0) : achou ? 0 : 1;
      }
    }
  };
  const a = new Uint8Array(mask.length);
  const b = new Uint8Array(mask.length);
  passo(mask, a, 1); // dilata
  passo(a, b, 0); // erode
  return b;
}

// ---------------------------------------------------------------------------
// carga e pre-computo
// ---------------------------------------------------------------------------

const el = {
  obra: document.querySelector("[data-obra]"),
  passo: document.querySelector("[data-passo]"),
  plano: document.querySelector("[data-plano]"),
  formula: document.querySelector("[data-formula]"),
  leituras: document.querySelector("[data-leituras]"),
  ato: document.querySelector("[data-ato]"),
  glosa: document.querySelector("[data-glosa]"),
};

const CORES = {
  papel: lerCor("--paper", "#ffffff"),
  tinta: lerCor("--ink", "#111111"),
  cinza: lerCor("--grey", "#696969"),
  regua: lerCor("--rule", "#bcbcbc"),
  accent: lerCor("--accent", "#963a2a"),
};

const estado = {
  obra: null,
  projeto: null,
  foto: null,
  arte: null,
  texto: "",
  celulas: [],
  cols: 0,
  linhas: 0,
  caixaFoto: null,
  /** retangulo da bancada dentro do canvas, em px de CSS */
  placa: { x: 0, y: 0, w: 0, h: 0 },
  passoCorpo: 0,
  passoLinha: 0,
  passoColuna: 0,
  dpr: 1,
};

function lerQuery() {
  const q = new URLSearchParams(location.search);
  for (const [k, v] of q) {
    if (k in P) P[k] = isNaN(Number(v)) ? v : Number(v);
  }
}

async function carregar() {
  lerQuery();

  const works = await (await fetch("/dados/works.json")).json();
  const projetos = await (await fetch("/dados/projetos.json")).json();

  estado.obra = works.find((w) => w.slug === P.obra) || works[0];
  estado.projeto = projetos[estado.obra.slug] || {};

  // A foto: usa o par pixel-a-pixel quando ele existe (`-before.webp`, gerado
  // por build_site_assets.py com o MESMO crop da arte). Sem ele, cai na
  // referencia crua e aplica o crop do project.yaml aqui — o mesmo
  // (left, upper, right, lower) que o PIL usa em image_prep.py.
  const antes = `/art/${estado.obra.slug}-before.webp`;
  const temAntes = (await fetch(antes, { method: "HEAD" })).ok;

  estado.foto = await carregarImagem(temAntes ? antes : `/refs/${estado.obra.slug}`);
  estado.arte = await carregarImagem(`/art/${estado.obra.slug}-full.webp`);

  const c = estado.projeto.crop;
  estado.caixaFoto =
    !temAntes && c && c.length === 4
      ? [c[0], c[1], c[2] - c[0], c[3] - c[1]]
      : [0, 0, estado.foto.naturalWidth, estado.foto.naturalHeight];

  const bruto = await (await fetch(`/texto/${estado.obra.slug}`)).text();
  estado.texto =
    bruto
      .split("\n")
      .filter((l) => l.trim() && !l.trim().startsWith("#"))
      .join("   ")
      .replace(/\s+/g, " ") || "ONDE MORAM AS PALAVRAS ";

  if (estado.projeto.accent) CORES.accent = estado.projeto.accent;

  el.obra.textContent = `${estado.obra.title} · PROCESSO`;
  document.documentElement.style.setProperty("--accent", CORES.accent);
}

/** resolucao horizontal da sondagem — independe de onde as letras caem */
const AMOSTRA_X = 260;

/**
 * Monta a tabela de celulas: uma entrada por glifo, com tudo que NAO depende
 * do tempo ja resolvido. Os atos so leem daqui.
 *
 * O avanco e' VARIAVEL, como em typography.py: a proxima posicao fica a
 * `largura_do_glifo * advance_factor` da atual, nao num passo de coluna fixo.
 * Com passo fixo as letras grandes das areas escuras se atropelam — o que a
 * peca impressa nao faz. E' a diferenca entre diagramar e so' pintar.
 */
function precomputar() {
  const { placa } = estado;
  const linhas = P.linhas;
  const passoLinha = placa.h / linhas;
  const corpo = passoLinha / P.razaoLinha;

  estado.linhas = linhas;
  estado.passoLinha = passoLinha;
  estado.passoCorpo = corpo;

  // sondagem: reduzir a foto para AMOSTRA_X x linhas COM suavizacao e' o
  // equivalente honesto da sonda por janela do motor (Field.mean).
  const amostraFoto = amostrar(estado.foto, AMOSTRA_X, linhas, estado.caixaFoto);

  // a tinta vem da arte final. Em 3x3 por celula e pegando o pixel mais
  // ESCURO: amostrar o centro sortearia o branco do papel entre duas letras.
  const sub = 3;
  const amostraArte = amostrar(estado.arte, AMOSTRA_X * sub, linhas * sub, [
    0, 0, estado.arte.naturalWidth, estado.arte.naturalHeight,
  ]);

  const lum = new Float32Array(AMOSTRA_X * linhas);
  for (let i = 0; i < lum.length; i++) {
    const d = amostraFoto.data;
    lum[i] = (0.299 * d[i * 4] + 0.587 * d[i * 4 + 1] + 0.114 * d[i * 4 + 2]) / 255;
  }

  let mask = new Uint8Array(lum.length);
  for (let i = 0; i < mask.length; i++) mask[i] = lum[i] < P.limiar ? 1 : 0;
  if (estado.obra.layers.includes("máscara")) mask = fechar(mask, AMOSTRA_X, linhas, 1);
  else mask.fill(1); // halftone puro: a arte inteira e' figura
  estado.lum = lum;
  estado.mask = mask;
  estado.cols = AMOSTRA_X;

  const tinta = (ix, r) => {
    let melhor = 1e9;
    let rgb = [17, 17, 17];
    const d = amostraArte.data;
    for (let sy = 0; sy < sub; sy++) {
      for (let sx = 0; sx < sub; sx++) {
        const px = ix * sub + sx + (r * sub + sy) * AMOSTRA_X * sub;
        const v = 0.299 * d[px * 4] + 0.587 * d[px * 4 + 1] + 0.114 * d[px * 4 + 2];
        if (v < melhor) {
          melhor = v;
          rgb = [d[px * 4], d[px * 4 + 1], d[px * 4 + 2]];
        }
      }
    }
    return `rgb(${rgb[0]},${rgb[1]},${rgb[2]})`;
  };

  const onda = Math.max(60, placa.w * P.ondaFrac);
  const ondaRot = Math.max(50, placa.w * P.rotOndaFrac);
  const amp = corpo * P.ondulacao;

  // medidor de largura de glifo, com cache: sao milhares de measureText e o
  // par (caractere, corpo arredondado) se repete o tempo todo
  const regua = document.createElement("canvas").getContext("2d");
  const fam = `"${estado.obra.font}", "Archivo Variable", Georgia, serif`;
  const cacheLargura = new Map();
  const largura = (ch, px, negrito) => {
    const chave = `${ch}|${px.toFixed(1)}|${negrito ? 1 : 0}`;
    let v = cacheLargura.get(chave);
    if (v === undefined) {
      regua.font = `${negrito ? 700 : 400} ${px.toFixed(2)}px ${fam}`;
      v = regua.measureText(ch).width;
      cacheLargura.set(chave, v);
    }
    return v;
  };

  const celulas = [];
  let iChar = 0;
  const proximoChar = () => {
    let ch;
    let voltas = 0;
    do {
      ch = estado.texto[iChar % estado.texto.length];
      iChar++;
    } while (ch === " " && ++voltas < 8);
    return ch;
  };

  for (let r = 0; r < linhas; r++) {
    const faseLinha = r * 0.5;
    const faseRot = r * 0.4;
    const yb = placa.y + (r + 0.85) * passoLinha;
    let x = placa.x;

    while (x < placa.x + placa.w) {
      const nx = (x - placa.x) / placa.w;
      const ix = Math.min(AMOSTRA_X - 1, Math.max(0, Math.floor(nx * AMOSTRA_X)));
      const i = r * AMOSTRA_X + ix;

      const dentro = mask[i] === 1;
      const escuridao = dentro ? clamp01(1 - lum[i]) : 0;
      const dk = Math.pow(escuridao, P.gamma);

      if (dk <= P.piso) {
        // area clara: anda um passo pequeno e nao desenha nada
        x += corpo * P.razaoColuna;
        continue;
      }

      const px = corpo * (P.corpoMin + (P.corpoMax - P.corpoMin) * dk);
      const negrito = dk > P.negritoEm;
      const ch = proximoChar();
      const w = largura(ch, px, negrito);

      const y = yb + amp * Math.sin((2 * Math.PI * (x - placa.x)) / onda + faseLinha);
      let ang = P.rotGrausMax * Math.sin((2 * Math.PI * (x - placa.x)) / ondaRot + faseRot);
      ang = Math.max(-P.rotGrausMax, Math.min(P.rotGrausMax, ang));

      celulas.push({
        r, ix, i,
        x: x + w / 2,
        y,
        lum: lum[i],
        dentro,
        dk,
        vazio: false,
        corpo: px,
        largura: w,
        negrito,
        cos: Math.cos((ang * Math.PI) / 180),
        sin: Math.sin((ang * Math.PI) / 180),
        cor: tinta(ix, r),
        ch,
      });

      x += Math.max(corpo * 0.28, w * P.avanco);
    }
  }
  estado.celulas = celulas;

  // indice por linha — a sonda anda por ele, e desenhar em cascata por linha
  // fica O(1) pra achar quem pertence a cada faixa
  estado.porLinha = Array.from({ length: linhas }, () => []);
  for (const cel of celulas) estado.porLinha[cel.r].push(cel);
}

// ---------------------------------------------------------------------------
// medidas do canvas
// ---------------------------------------------------------------------------

function medir() {
  const canvas = el.plano;
  const caixa = canvas.getBoundingClientRect();
  const dpr = Math.max(1, window.devicePixelRatio || 1);
  canvas.width = Math.round(caixa.width * dpr);
  canvas.height = Math.round(caixa.height * dpr);
  estado.dpr = dpr;

  // calhas para os eixos do plano cartesiano
  const calhaE = Math.max(22, caixa.width * 0.075);
  const calhaB = Math.max(18, caixa.height * 0.05);
  const dispW = caixa.width - calhaE;
  const dispH = caixa.height - calhaB;

  const aspecto = estado.obra ? estado.obra.aspect : 1;
  let w = dispW;
  let h = w / aspecto;
  if (h > dispH) {
    h = dispH;
    w = h * aspecto;
  }
  estado.placa = { x: calhaE + (dispW - w) / 2, y: (dispH - h) / 2, w, h };

  if (estado.obra) precomputar();
}

// ---------------------------------------------------------------------------
// pintura dos textos (DOM) — tambem funcao pura de (ato, u)
// ---------------------------------------------------------------------------

function pintarLeituras(pares) {
  el.leituras.innerHTML = pares
    .map(
      ([k, v, destaque]) =>
        `<div><dt>${k}</dt><dd${destaque ? ' data-destaque="1"' : ""}>${v}</dd></div>`
    )
    .join("");
}

/** o titulo do ato se monta letra a letra — o mesmo gesto de assemble.js,
 *  so' que por progresso, nunca por relogio (e com ruido semeado) */
function pintarAto(texto, u) {
  if (el.ato.dataset.txt !== texto) {
    el.ato.dataset.txt = texto;
    el.ato.innerHTML = [...texto]
      .map((ch) => `<span>${ch === " " ? "&nbsp;" : ch}</span>`)
      .join("");
  }
  const spans = el.ato.children;
  for (let i = 0; i < spans.length; i++) {
    const p = suave(cascata(u, i, spans.length, 0.55));
    const dx = (ruido(i, 3) * 2 - 1) * 26 * (1 - p);
    const dy = (ruido(i, 7) * 2 - 1) * 22 * (1 - p);
    const rot = (ruido(i, 11) * 2 - 1) * 18 * (1 - p);
    spans[i].style.opacity = p.toFixed(3);
    spans[i].style.transform = `translate(${dx.toFixed(2)}px, ${dy.toFixed(2)}px) rotate(${rot.toFixed(2)}deg)`;
  }
}

// ---------------------------------------------------------------------------
// desenho da bancada
// ---------------------------------------------------------------------------

function ctx2d() {
  const x = el.plano.getContext("2d");
  x.setTransform(estado.dpr, 0, 0, estado.dpr, 0, 0);
  return x;
}

function limpar(x) {
  x.save();
  x.setTransform(1, 0, 0, 1, 0, 0);
  x.clearRect(0, 0, el.plano.width, el.plano.height);
  x.restore();
}

function desenharFoto(x, alfa, escala = 1, cinza = 0) {
  if (alfa <= 0) return;
  const { placa } = estado;
  const [sx, sy, sw, sh] = estado.caixaFoto;
  x.save();
  x.globalAlpha = alfa;
  const cx = placa.x + placa.w / 2;
  const cy = placa.y + placa.h / 2;
  x.translate(cx, cy);
  x.scale(escala, escala);
  x.translate(-cx, -cy);
  if (cinza > 0) x.filter = `grayscale(${(cinza * 100).toFixed(0)}%)`;
  x.drawImage(estado.foto, sx, sy, sw, sh, placa.x, placa.y, placa.w, placa.h);
  x.restore();
}

/** o plano cartesiano: moldura, ticks e legendas em cm — a peca e' um objeto fisico */
function desenharPlano(x, u) {
  const { placa, obra } = estado;
  const p = clamp01(u);
  if (p <= 0) return;

  x.save();
  x.lineWidth = 1;
  x.strokeStyle = CORES.regua;
  x.font = `500 ${Math.max(7, placa.w * 0.021)}px "JetBrains Mono", monospace`;
  x.fillStyle = CORES.cinza;

  // eixos, desenhados progressivamente a partir da origem (canto inf. esquerdo)
  x.beginPath();
  x.moveTo(placa.x, placa.y + placa.h);
  x.lineTo(placa.x + placa.w * p, placa.y + placa.h);
  x.moveTo(placa.x, placa.y + placa.h);
  x.lineTo(placa.x, placa.y + placa.h - placa.h * p);
  x.strokeStyle = CORES.tinta;
  x.stroke();

  // ticks: 6 divisoes em cada eixo, rotuladas em cm reais da peca
  const div = 6;
  x.strokeStyle = CORES.regua;
  for (let i = 0; i <= div; i++) {
    const f = i / div;
    if (f > p) break;
    const px = placa.x + placa.w * f;
    const py = placa.y + placa.h - placa.h * f;
    x.beginPath();
    x.moveTo(px, placa.y + placa.h);
    x.lineTo(px, placa.y + placa.h + 4);
    x.moveTo(placa.x - 4, py);
    x.lineTo(placa.x, py);
    x.stroke();
    // o rotulo da ponta encosta na borda do canvas: alinha pra dentro, senao
    // o "96" sai cortado em "9"
    x.textAlign = i === div ? "right" : i === 0 ? "left" : "center";
    x.textBaseline = "top";
    x.fillText(`${Math.round(obra.widthCm * f)}`, px, placa.y + placa.h + 6);
    x.textAlign = "right";
    x.textBaseline = "middle";
    x.fillText(`${Math.round(obra.heightCm * f)}`, placa.x - 6, py);
  }

  // grade interna, fraca, entrando depois dos eixos
  const gp = clamp01((p - 0.45) / 0.55);
  if (gp > 0) {
    x.globalAlpha = gp * 0.5;
    x.strokeStyle = CORES.regua;
    x.setLineDash([2, 4]);
    x.beginPath();
    for (let i = 1; i < div; i++) {
      const f = i / div;
      x.moveTo(placa.x + placa.w * f, placa.y);
      x.lineTo(placa.x + placa.w * f, placa.y + placa.h);
      x.moveTo(placa.x, placa.y + placa.h - placa.h * f);
      x.lineTo(placa.x + placa.w, placa.y + placa.h - placa.h * f);
    }
    x.stroke();
    x.setLineDash([]);
  }
  x.restore();
}

/** varre as celulas desenhando `pinta(celula, progressoDaCelula)` em cascata por linha */
function porLinhas(u, pinta, janela = 0.5) {
  const { celulas, linhas } = estado;
  for (const cel of celulas) {
    const p = cascata(u, cel.r, linhas, janela);
    if (p > 0) pinta(cel, p);
  }
}

// ---------------------------------------------------------------------------
// os nove atos
// ---------------------------------------------------------------------------

const desenho = {
  foto(x, u) {
    desenharFoto(x, suave(clamp01(u * 1.4)), mix(1.035, 1, saidaCubica(u)));
    el.formula.textContent = `${estado.obra.px[0]} × ${estado.obra.px[1]} px · referência`;
    pintarLeituras([
      ["obra", estado.obra.title],
      ["origem", estado.obra.subtitle.split(" · ")[0] || "—"],
      ["família", estado.obra.family],
    ]);
  },

  grade(x, u) {
    desenharFoto(x, mix(1, 0.42, suave(u)));
    desenharPlano(x, saidaCubica(u));
    el.formula.textContent = `página ${estado.obra.widthCm} × ${estado.obra.heightCm} cm @ 150 dpi`;
    pintarLeituras([
      ["largura", `${estado.obra.widthCm} cm`],
      ["altura", `${estado.obra.heightCm} cm`],
      ["corpo", `${estado.obra.bodyMm} mm`],
      ["malha (cena)", `${estado.linhas} × ${estado.cols}`],
    ]);
  },

  luminancia(x, u) {
    const p = suave(u);
    const { placa } = estado;
    desenharFoto(x, 0.42);
    // limpa e redesenha em cinza so' na faixa ja varrida — a "cortina" de luz
    x.save();
    x.beginPath();
    x.rect(placa.x, placa.y, placa.w * p, placa.h);
    x.clip();
    x.fillStyle = CORES.papel;
    x.fillRect(placa.x, placa.y, placa.w, placa.h);
    desenharFoto(x, 0.92, 1, 1);
    x.restore();
    if (p > 0 && p < 1) {
      x.save();
      x.strokeStyle = CORES.accent;
      x.lineWidth = 1.5;
      x.beginPath();
      x.moveTo(placa.x + placa.w * p, placa.y);
      x.lineTo(placa.x + placa.w * p, placa.y + placa.h);
      x.stroke();
      x.restore();
    }
    desenharPlano(x, 1);
    el.formula.textContent = "lum = (0,299·R + 0,587·G + 0,114·B) / 255";
    const media = estado.celulas.reduce((s, c) => s + c.lum, 0) / estado.celulas.length;
    pintarLeituras([
      ["varrido", `${Math.round(p * 100)} %`],
      ["lum média", media.toFixed(3)],
      ["canal", "único"],
    ]);
  },

  mascara(x, u) {
    const p = suave(u);
    const { placa } = estado;
    desenharFoto(x, 0.3, 1, 1);
    desenharPlano(x, 1);

    // o limiar "desce" ate o valor real: a figura se fecha diante da camera.
    // A silhueta sai da grade de sondagem (lum), nao da lista de glifos — e'
    // ela que o mask.py enxerga.
    const limiarVisto = mix(0.95, P.limiar, p);
    const cols = estado.cols;
    const cw = placa.w / cols;
    const ch = placa.h / estado.linhas;
    const eFigura = (ix, r) =>
      ix >= 0 && ix < cols && r >= 0 && r < estado.linhas &&
      estado.lum[r * cols + ix] < limiarVisto;

    x.save();
    x.fillStyle = CORES.tinta;
    x.globalAlpha = 0.88;
    let dentro = 0;
    for (let r = 0; r < estado.linhas; r++) {
      // varre em faixas horizontais contiguas: um fillRect por corrida, em vez
      // de um por celula — sem costura de antialias entre retangulos vizinhos
      let inicio = -1;
      for (let ix = 0; ix <= cols; ix++) {
        const fig = ix < cols && eFigura(ix, r);
        if (fig) dentro++;
        if (fig && inicio < 0) inicio = ix;
        if (!fig && inicio >= 0) {
          x.fillRect(placa.x + inicio * cw, placa.y + r * ch, (ix - inicio) * cw, ch + 0.5);
          inicio = -1;
        }
      }
    }
    x.restore();

    // contorno em accent: a borda da figura, que e' o assunto do ato
    x.save();
    x.strokeStyle = CORES.accent;
    x.lineWidth = 1.4;
    x.globalAlpha = clamp01((p - 0.35) / 0.65);
    x.beginPath();
    for (let r = 0; r < estado.linhas; r++) {
      for (let ix = 0; ix < cols; ix++) {
        if (!eFigura(ix, r)) continue;
        const px = placa.x + ix * cw;
        const py = placa.y + r * ch;
        if (!eFigura(ix - 1, r)) { x.moveTo(px, py); x.lineTo(px, py + ch); }
        if (!eFigura(ix + 1, r)) { x.moveTo(px + cw, py); x.lineTo(px + cw, py + ch); }
        if (!eFigura(ix, r - 1)) { x.moveTo(px, py); x.lineTo(px + cw, py); }
        if (!eFigura(ix, r + 1)) { x.moveTo(px, py + ch); x.lineTo(px + cw, py + ch); }
      }
    }
    x.stroke();
    x.restore();

    el.formula.textContent = `máscara = lum < ${limiarVisto.toFixed(2)}`;
    pintarLeituras([
      ["limiar", limiarVisto.toFixed(2), true],
      ["figura", `${Math.round((dentro / (cols * estado.linhas)) * 100)} %`],
      ["camadas", estado.obra.layers.join(" + ")],
    ]);
  },

  sonda(x, u) {
    const { placa } = estado;
    desenharFoto(x, 0.22, 1, 1);
    desenharPlano(x, 1);

    // a sonda anda em serpentina; cada parada ja visitada deixa a marca da
    // medida (um risco proporcional ao corpo que aquela escuridao pediu)
    const paradas = P.paradasSonda;
    const atual = u * paradas;
    const faixas = 4; // quantas idas e vindas a sonda faz de cima a baixo
    const alvo = (k) => {
      const f = k / paradas;
      const linha = Math.min(estado.linhas - 1, Math.floor(f * (estado.linhas - 2)) + 1);
      const naFaixa = (k % (paradas / faixas)) / (paradas / faixas);
      const dir = Math.floor(k / (paradas / faixas)) % 2 === 0 ? naFaixa : 1 - naFaixa;
      // procura a linha mais proxima que tenha glifo (linhas claras ficam vazias)
      for (let d = 0; d < estado.linhas; d++) {
        for (const r of [linha + d, linha - d]) {
          const fila = estado.porLinha[r];
          if (fila && fila.length) {
            return fila[Math.min(fila.length - 1, Math.floor(dir * (fila.length - 1)))];
          }
        }
      }
      return null;
    };

    x.save();
    for (let k = 0; k < Math.min(paradas, Math.ceil(atual)); k++) {
      const cel = alvo(k);
      if (!cel) continue;
      x.globalAlpha = 0.5;
      x.strokeStyle = CORES.cinza;
      x.lineWidth = 1;
      x.beginPath();
      x.moveTo(cel.x, cel.y - cel.corpo * 0.5);
      x.lineTo(cel.x, cel.y + cel.corpo * 0.5);
      x.stroke();
    }
    x.restore();

    const cel = alvo(Math.min(paradas - 1, Math.floor(atual)));
    if (cel) {
      const lado = estado.passoCorpo * 2.4;
      x.save();
      x.strokeStyle = CORES.accent;
      x.lineWidth = 1.6;
      x.strokeRect(cel.x - lado / 2, cel.y - lado / 2, lado, lado);
      x.beginPath();
      x.moveTo(cel.x - lado, cel.y);
      x.lineTo(cel.x - lado / 2, cel.y);
      x.moveTo(cel.x + lado / 2, cel.y);
      x.lineTo(cel.x + lado, cel.y);
      x.stroke();
      x.restore();

      const mm = (
        estado.obra.bodyMm *
        (P.corpoMin + (P.corpoMax - P.corpoMin) * cel.dk)
      ).toFixed(1);
      el.formula.textContent = `escuridão^${P.gamma} → corpo = ${mm} mm${cel.negrito ? " · negrito" : ""}`;
      pintarLeituras([
        ["posição", `${cel.c}, ${cel.r}`],
        ["escuridão", cel.dk.toFixed(3), true],
        ["corpo", `${mm} mm`],
        ["peso", cel.negrito ? "bold" : "regular"],
      ]);
    }
  },

  pontos(x, u) {
    desenharFoto(x, mix(0.22, 0, suave(u)), 1, 1);
    desenharPlano(x, 1);
    x.save();
    x.fillStyle = CORES.tinta;
    porLinhas(u, (cel, p) => {
      if (cel.vazio) return;
      const r = (cel.corpo * 0.34) * suave(p);
      x.globalAlpha = 0.55 + 0.45 * cel.dk;
      x.beginPath();
      x.arc(cel.x, cel.y, r, 0, Math.PI * 2);
      x.fill();
    });
    x.restore();
    const n = estado.celulas.filter((c) => !c.vazio).length;
    el.formula.textContent = `corpo = ${P.corpoMin}·L + ${(P.corpoMax - P.corpoMin).toFixed(2)}·L·escuridão^${P.gamma}`;
    pintarLeituras([
      ["pontos", Math.round(n * clamp01(u * 1.15)).toLocaleString("pt-BR")],
      ["mín", `${(estado.obra.bodyMm * P.corpoMin).toFixed(1)} mm`],
      ["máx", `${(estado.obra.bodyMm * P.corpoMax).toFixed(1)} mm`],
    ]);
  },

  cores(x, u) {
    desenharPlano(x, 1);
    const p = suave(u);
    x.save();
    // a tinta entra em cascata pela posicao horizontal: uma cortina de cor
    // atravessando a bancada da esquerda pra direita
    porLinhas(1, (cel) => {
      const r = cel.corpo * 0.34;
      x.globalAlpha = 0.55 + 0.45 * cel.dk;
      const pc = clamp01((p - (cel.ix / estado.cols) * 0.55) / 0.45);
      x.fillStyle = pc <= 0 ? CORES.tinta : cel.cor;
      x.beginPath();
      x.arc(cel.x, cel.y, r, 0, Math.PI * 2);
      x.fill();
    });
    x.restore();
    el.formula.textContent = "tinta = cor da referência no centro da sonda";
    pintarLeituras([
      ["accent", CORES.accent.toUpperCase(), true],
      ["camadas", estado.obra.layers.join(" + ")],
      ["fonte", estado.obra.font],
    ]);
  },

  letras(x, u) {
    desenharPlano(x, 1);
    const fam = `"${estado.obra.font}", "Archivo Variable", Georgia, serif`;
    // as letras substituem os pontos linha a linha; o ponto encolhe enquanto
    // o glifo cresce, entao a troca nao pisca
    x.save();
    x.textAlign = "center";
    x.textBaseline = "alphabetic";
    porLinhas(u, (cel, p) => {
      if (cel.vazio) return;
      const s = suave(p);
      x.globalAlpha = 0.6 + 0.4 * cel.dk;
      x.fillStyle = cel.cor;
      if (s < 1) {
        const r = cel.corpo * 0.34 * (1 - s);
        if (r > 0.2) {
          x.beginPath();
          x.arc(cel.x, cel.y, r, 0, Math.PI * 2);
          x.fill();
        }
      }
      if (s <= 0) return;
      x.globalAlpha *= s;
      x.font = `${cel.negrito ? 700 : 400} ${(cel.corpo * s).toFixed(2)}px ${fam}`;
      x.setTransform(
        estado.dpr * cel.cos, estado.dpr * cel.sin,
        -estado.dpr * cel.sin, estado.dpr * cel.cos,
        estado.dpr * cel.x, estado.dpr * cel.y
      );
      x.fillText(cel.ch, 0, 0);
      x.setTransform(estado.dpr, 0, 0, estado.dpr, 0, 0);
    }, 0.42);
    x.restore();

    // no fim do ato, a arte de verdade entra por cima: o que a cena diagramou
    // e o que o motor imprimiu, lado a lado no mesmo lugar
    const troca = clamp01((u - 0.82) / 0.18);
    if (troca > 0) {
      const { placa } = estado;
      x.save();
      x.globalAlpha = suave(troca);
      x.drawImage(estado.arte, placa.x, placa.y, placa.w, placa.h);
      x.restore();
    }

    const total = estado.obra.glyphs || 0;
    el.formula.textContent = `${estado.texto.slice(0, 46).trim()}…`;
    pintarLeituras([
      ["glifos (peça)", total.toLocaleString("pt-BR"), true],
      ["desenhados", Math.round(total * clamp01(u * 1.1)).toLocaleString("pt-BR")],
      ["fonte", estado.obra.font],
      ["corpo", `${estado.obra.bodyMm} mm`],
    ]);
  },

  ficha(x, u) {
    const { placa, obra } = estado;
    const p = suave(u);
    // a arte recua para caber a ficha: sobe e encolhe, como uma prancha
    const k = mix(1, 0.78, p);
    const dy = -placa.h * 0.06 * p;
    x.save();
    x.globalAlpha = 1;
    const w = placa.w * k;
    const h = placa.h * k;
    const px = placa.x + (placa.w - w) / 2;
    const py = placa.y + (placa.h - h) / 2 + dy;
    x.drawImage(estado.arte, px, py, w, h);
    x.strokeStyle = CORES.tinta;
    x.lineWidth = 1;
    x.strokeRect(px - 0.5, py - 0.5, w + 1, h + 1);
    x.restore();

    el.formula.textContent = `${obra.widthCm} × ${obra.heightCm} cm · 150 dpi · ${obra.px[0]} × ${obra.px[1]} px`;
    pintarLeituras([
      ["fonte", obra.font],
      ["corpo", `${obra.bodyMm} mm`],
      ["camadas", obra.layers.join(" + ")],
      ["glifos", (obra.glyphs || 0).toLocaleString("pt-BR"), true],
    ]);
  },
};

// ---------------------------------------------------------------------------
// contrato publico
// ---------------------------------------------------------------------------

function seek(ato, u) {
  const nome = ATOS.includes(ato) ? ato : ATOS[0];
  const p = clamp01(u);
  const x = ctx2d();
  limpar(x);
  desenho[nome](x, p);

  const idx = ATOS.indexOf(nome);
  el.passo.textContent = `${String(idx + 1).padStart(2, "0")} / ${String(ATOS.length).padStart(2, "0")}`;
  el.glosa.textContent = GLOSA_ATO[nome];
  pintarAto(TITULO_ATO[nome], clamp01(p * 3.2));
}

const pronto = (async () => {
  await document.fonts.ready;
  await carregar();
  medir();
  seek(ATOS[0], 0);
  document.documentElement.dataset.cenaPronta = "1";
})();

window.__cena = {
  pronto,
  atos: ATOS,
  seek,
  medir,
  parametros: P,
  configurar(novos) {
    Object.assign(P, novos);
    medir();
  },
};

// util so' para folhear a cena no navegador durante o ajuste — a captura
// nunca passa por aqui (ela chama seek() diretamente).
window.addEventListener("resize", () => {
  medir();
  seek(el.plano.dataset.ato || ATOS[0], Number(el.plano.dataset.u || 0));
});
window.addEventListener("keydown", async (e) => {
  await pronto;
  const i = ATOS.indexOf(el.plano.dataset.ato || ATOS[0]);
  if (e.key === "ArrowRight") {
    const n = ATOS[Math.min(ATOS.length - 1, i + 1)];
    el.plano.dataset.ato = n;
    seek(n, 1);
  }
  if (e.key === "ArrowLeft") {
    const n = ATOS[Math.max(0, i - 1)];
    el.plano.dataset.ato = n;
    seek(n, 1);
  }
});
