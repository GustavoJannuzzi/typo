/**
 * O hero vivo: uma porta conceitual do laco principal de
 * `src/typo/typography.py` para <canvas>, rodando no navegador.
 *
 * O motor original varre uma imagem de referencia, mede escuridao local e
 * desenha caracteres em tamanho/peso/rotacao proporcionais. Aqui nao ha
 * foto — a "escuridao local" vem de um campo sintetico: blobs radiais que
 * *respiram* (o raio pulsa devagar, como uma chapa em revelacao) e derivam
 * conforme a pagina rola. Nao ha interacao com ponteiro: a maioria dos
 * acessos e mobile, onde ela nao existe e so custa bateria.
 *
 * Mesma matematica de mapeamento do motor:
 *   dk       = darkness^gamma                          (typography.py)
 *   fontSize = sizeMin + (sizeMax-sizeMin) * dk
 *   rotacao  = rotAmp * sin(2*pi*x/rotWave + faseDaLinha), com clamp
 *   baseline = yb + amp * sin(2*pi*x/onda + faseDaLinha)  (ondulacao)
 *
 * Orcamento de desempenho — o gargalo e a quantidade de `fillText` por
 * segundo, entao tudo que da pra congelar esta congelado:
 *   - a GRADE (posicao, caractere, seno/cosseno da rotacao) e calculada uma
 *     vez por resize; a rotacao nao depende do tempo, so de x.
 *   - a escuridao vira um de LEVELS baldes; fonte e opacidade de cada balde
 *     sao strings pre-montadas, entao o laco nao formata texto nem aloca.
 *   - `setTransform` no lugar de save/translate/rotate/restore (1 op no
 *     lugar de 4) e trocas de estado so quando o balde muda.
 *   - o desenho e limitado a FPS_CAP: a respiracao e lenta, 60fps nao
 *     acrescenta nada e dobra o custo.
 */
const STREAM =
  "ONDE MORAM AS PALAVRAS   UMA IMAGEM FEITA DE MILHARES DE PALAVRAS   " +
  "SUA HISTORIA ESCRITA ATE VIRAR IMAGEM   NOVE ESPECIMES CATALOGADOS   ";

const GAMMA = 1.35;
const SIZE_MIN_RATIO = 0.34;
const SIZE_MAX_RATIO = 1.55;
const BOLD_THRESHOLD = 0.6;
const ACCENT_THRESHOLD = 0.72;
const FLOOR = 0.1;
const MAX_CELLS = 4200;
const LEVELS = 24;
const FRAME_MS = 1000 / 30;

/** quanto o campo sobe e revira ao longo de uma tela de rolagem */
const SCROLL_RISE = 0.18;
const SCROLL_SWIRL = 2.6;
/** deslocamento da malha inteira, em fracao da altura — parallax */
const SCROLL_PARALLAX = 0.12;

const prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

function readColor(varName, fallback) {
  const v = getComputedStyle(document.documentElement).getPropertyValue(varName).trim();
  return v || fallback;
}

export function initHaltoneCanvas(canvas) {
  const ctx = canvas.getContext("2d", { alpha: true });
  const ink = readColor("--ink", "#111111");
  const accent = readColor("--accent", "#963a2a");

  let cells = [];
  let rectW = 0;
  let rectH = 0;
  let canvasTop = 0;
  let dpr = Math.min(window.devicePixelRatio || 1, 2);
  let running = false;
  let rafId = null;
  let visible = true;
  let lastDraw = 0;
  let scrollY = window.scrollY;

  /** fonte e opacidade por balde de escuridao — montadas em buildGrid */
  let levelFont = [];
  let levelAlpha = [];
  let levelBold = [];

  const blobs = [
    { cx: 0.5, cy: 0.42, rx: 0.34, ry: 0.4, amp: 1.0, speed: 0.06, phase: 0, driftX: 0.05, driftY: 0.04, breath: 0.15 },
    { cx: 0.28, cy: 0.62, rx: 0.2, ry: 0.22, amp: 0.55, speed: 0.09, phase: 2.1, driftX: 0.06, driftY: 0.05, breath: 0.2 },
    { cx: 0.7, cy: 0.58, rx: 0.22, ry: 0.24, amp: 0.5, speed: 0.075, phase: 4.4, driftX: 0.05, driftY: 0.06, breath: 0.18 },
  ];

  /**
   * `t` faz o campo respirar (pulso lento de raio + deriva); `s` e o
   * progresso da rolagem dentro do hero (0..1) e faz a massa de tinta subir
   * e revirar — as duas coisas somadas, nunca uma no lugar da outra.
   */
  function fieldValue(nx, ny, t, s) {
    let v = 0;
    for (const b of blobs) {
      const breath = 1 + b.breath * Math.sin(t * 0.42 + b.phase);
      const bx = b.cx + Math.sin(t * b.speed + b.phase) * b.driftX + Math.sin(s * SCROLL_SWIRL + b.phase) * 0.07;
      const by = b.cy + Math.cos(t * b.speed * 0.8 + b.phase) * b.driftY - s * SCROLL_RISE;
      const dx = (nx - bx) / (b.rx * breath);
      const dy = (ny - by) / (b.ry * breath);
      v += b.amp * Math.exp(-(dx * dx + dy * dy) * 2.1);
    }
    return v;
  }

  function buildGrid() {
    const lineH = Math.max(14, Math.min(30, rectW * 0.026));
    const rowStep = lineH * 0.95;
    const colStep = lineH * 0.62;

    const rows = Math.ceil(rectH / rowStep);
    const cols = Math.ceil(rectW / colStep);
    const total = rows * cols;
    const scale = total > MAX_CELLS ? Math.sqrt(total / MAX_CELLS) : 1;

    const finalRowStep = rowStep * scale;
    const finalColStep = colStep * scale;
    const finalLineH = lineH * scale;

    const undulationAmp = finalLineH * 0.4;
    const undulationWave = Math.max(120, rectW * 0.5);
    const rotWave = Math.max(90, rectW * 0.22);
    const rotClamp = 16;

    const next = [];
    let charIdx = 0;
    let rowIndex = 0;
    for (let yb = finalLineH; yb < rectH + finalRowStep; yb += finalRowStep, rowIndex++) {
      const rowPhase = rowIndex * 0.5;
      const rotPhase = rowIndex * 0.4;
      for (let x = 0; x < rectW; x += finalColStep) {
        const y = yb + undulationAmp * Math.sin((2 * Math.PI * x) / undulationWave + rowPhase);
        const ch = STREAM[charIdx % STREAM.length];
        charIdx++;
        if (ch === " ") continue;
        // a rotacao so depende de x — congela aqui e nunca mais recalcula
        let ang = rotClamp * Math.sin((2 * Math.PI * x) / rotWave + rotPhase);
        ang = Math.max(-rotClamp, Math.min(rotClamp, ang));
        const rad = (ang * Math.PI) / 180;
        next.push({ x, y, ch, nx: x / rectW, cos: Math.cos(rad), sin: Math.sin(rad) });
      }
    }
    cells = next;

    levelFont = new Array(LEVELS);
    levelAlpha = new Float32Array(LEVELS);
    levelBold = new Array(LEVELS);
    for (let i = 0; i < LEVELS; i++) {
      const dk = (i + 0.5) / LEVELS;
      const fs = finalLineH * (SIZE_MIN_RATIO + (SIZE_MAX_RATIO - SIZE_MIN_RATIO) * dk);
      levelBold[i] = dk > BOLD_THRESHOLD;
      levelFont[i] = `${levelBold[i] ? 800 : 420} ${fs.toFixed(1)}px "Archivo Variable", sans-serif`;
      levelAlpha[i] = 0.55 + 0.45 * dk;
    }
  }

  function resize() {
    const rect = canvas.getBoundingClientRect();
    rectW = Math.max(1, Math.round(rect.width));
    rectH = Math.max(1, Math.round(rect.height));
    canvasTop = rect.top + window.scrollY;
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = rectW * dpr;
    canvas.height = rectH * dpr;
    buildGrid();
    draw(performance.now());
  }

  function draw(tMs) {
    const t = tMs / 1000;
    const s = Math.max(0, Math.min(1, (scrollY - canvasTop) / rectH));
    const parallax = s * rectH * SCROLL_PARALLAX;

    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, rectW, rectH);
    ctx.textBaseline = "alphabetic";

    let curLevel = -1;
    let curFill = "";
    for (let i = 0; i < cells.length; i++) {
      const cell = cells[i];
      const dark = fieldValue(cell.nx, (cell.y - parallax) / rectH, t, s);
      if (dark < FLOOR) continue;
      const dk = Math.pow(dark > 1 ? 1 : dark, GAMMA);

      let level = (dk * LEVELS) | 0;
      if (level >= LEVELS) level = LEVELS - 1;
      if (level !== curLevel) {
        curLevel = level;
        ctx.font = levelFont[level];
        ctx.globalAlpha = levelAlpha[level];
      }

      const fill = level >= ACCENT_THRESHOLD * LEVELS && cell.nx > 0.32 && cell.nx < 0.68 ? accent : ink;
      if (fill !== curFill) {
        curFill = fill;
        ctx.fillStyle = fill;
      }

      const y = cell.y - parallax;
      ctx.setTransform(dpr * cell.cos, dpr * cell.sin, -dpr * cell.sin, dpr * cell.cos, dpr * cell.x, dpr * y);
      ctx.fillText(cell.ch, 0, 0);
    }
    ctx.globalAlpha = 1;
  }

  function tick(tMs) {
    if (tMs - lastDraw >= FRAME_MS) {
      lastDraw = tMs;
      draw(tMs);
    }
    if (running && visible) rafId = requestAnimationFrame(tick);
  }

  function start() {
    if (running || prefersReduced) return;
    running = true;
    rafId = requestAnimationFrame(tick);
  }

  function stop() {
    running = false;
    if (rafId) cancelAnimationFrame(rafId);
    rafId = null;
  }

  function onScroll() {
    scrollY = window.scrollY;
  }

  const ro = new ResizeObserver(() => resize());
  ro.observe(canvas);

  // A primeira leitura do IntersectionObserver e assincrona e, em alguns
  // motores, pode chegar antes do layout final assentar (o canvas e
  // position:absolute dentro do hero) — reportando "fora da tela" por um
  // instante mesmo estando no topo da pagina. Como o hero e sempre a
  // primeira coisa visivel no carregamento, ignoramos essa primeira leitura
  // e so agimos (inclusive parar) a partir da segunda observacao em diante.
  let ioReadings = 0;
  const io = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        ioReadings++;
        visible = entry.isIntersecting;
        if (ioReadings === 1) return;
        if (visible) start();
        else stop();
      });
    },
    { threshold: 0.05 }
  );
  io.observe(canvas);

  window.addEventListener("scroll", onScroll, { passive: true });
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) stop();
    else if (visible) start();
  });

  resize();
  start();

  const api = {
    destroy: () => {
      stop();
      ro.disconnect();
      io.disconnect();
      window.removeEventListener("scroll", onScroll);
    },
    _debug: () => {
      const t = performance.now() / 1000;
      const s = Math.max(0, Math.min(1, (scrollY - canvasTop) / rectH));
      const darks = cells.map((c) => fieldValue(c.nx, c.y / rectH, t, s));
      return {
        running,
        visible,
        rectW,
        rectH,
        scrollProgress: +s.toFixed(3),
        cellCount: cells.length,
        drawnCount: darks.filter((d) => d >= FLOOR).length,
        centerDark: fieldValue(0.5, 0.42, t, s),
        maxDark: Math.max(...darks),
      };
    },
  };
  if (import.meta.env.DEV) window.__heroDebug = api._debug;
  return api;
}
