/**
 * O hero vivo: uma porta conceitual do laco principal de
 * `src/typo/typography.py` para <canvas>, rodando no navegador.
 *
 * O motor original varre uma imagem de referencia, mede escuridao local e
 * desenha caracteres em tamanho/peso/rotacao proporcionais. Aqui nao ha
 * foto — a "escuridao local" vem de um campo sintetico (alguns blobs
 * radiais que derivam devagar, como uma chapa de revelacao), e o ponteiro
 * do usuario funciona como uma lupa que intensifica a tinta por perto,
 * reforcando a ideia de "instrumento de leitura".
 *
 * Mesma matematica de mapeamento do motor:
 *   dk       = darkness^gamma                          (typography.py)
 *   fontSize = sizeMin + (sizeMax-sizeMin) * dk
 *   rotacao  = rotAmp * sin(2*pi*x/rotWave + faseDaLinha), com clamp
 *   baseline = yb + amp * sin(2*pi*x/onda + faseDaLinha)  (ondulacao)
 *
 * Para performance, a GRADE de posicoes e fixa (calculada uma vez por
 * resize, com a ondulacao ja embutida na posicao Y de cada celula); a cada
 * frame so o tamanho/rotacao/cor mudam — nada de medir texto every frame.
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
const MAX_CELLS = 6000;

const prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

function readColor(varName, fallback) {
  const v = getComputedStyle(document.documentElement).getPropertyValue(varName).trim();
  return v || fallback;
}

export function initHaltoneCanvas(canvas) {
  const ctx = canvas.getContext("2d");
  const ink = readColor("--ink", "#111111");
  const accent = readColor("--accent", "#963a2a");

  let cells = [];
  let rectW = 0;
  let rectH = 0;
  let dpr = Math.min(window.devicePixelRatio || 1, 2);
  let running = false;
  let rafId = null;
  let visible = true;

  const pointer = { x: 0.5, y: 0.4, active: 0 };

  const blobs = [
    { cx: 0.5, cy: 0.42, rx: 0.34, ry: 0.4, amp: 1.0, speed: 0.06, phase: 0, driftX: 0.05, driftY: 0.04 },
    { cx: 0.28, cy: 0.62, rx: 0.2, ry: 0.22, amp: 0.55, speed: 0.09, phase: 2.1, driftX: 0.06, driftY: 0.05 },
    { cx: 0.7, cy: 0.58, rx: 0.22, ry: 0.24, amp: 0.5, speed: 0.075, phase: 4.4, driftX: 0.05, driftY: 0.06 },
  ];

  function fieldValue(nx, ny, t) {
    let v = 0;
    for (const b of blobs) {
      const bx = b.cx + Math.sin(t * b.speed + b.phase) * b.driftX;
      const by = b.cy + Math.cos(t * b.speed * 0.8 + b.phase) * b.driftY;
      const dx = (nx - bx) / b.rx;
      const dy = (ny - by) / b.ry;
      v += b.amp * Math.exp(-(dx * dx + dy * dy) * 2.1);
    }
    if (pointer.active > 0.01) {
      const dx = (nx - pointer.x) * 1.15;
      const dy = ny - pointer.y;
      const d2 = dx * dx + dy * dy;
      v += pointer.active * 0.85 * Math.exp(-d2 * 9);
    }
    return v;
  }

  function buildGrid() {
    const lineH = Math.max(13, Math.min(30, rectW * 0.024));
    const rowStep = lineH * 0.92;
    const colStep = lineH * 0.6;

    let rows = Math.ceil(rectH / rowStep);
    let cols = Math.ceil(rectW / colStep);
    let total = rows * cols;
    let scale = 1;
    if (total > MAX_CELLS) {
      scale = Math.sqrt(total / MAX_CELLS);
    }
    const finalRowStep = rowStep * scale;
    const finalColStep = colStep * scale;
    const finalLineH = lineH * scale;

    const undulationAmp = finalLineH * 0.4;
    const undulationWave = Math.max(120, rectW * 0.5);

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
        next.push({ x, y, ch, rowPhase: rotPhase, lineH: finalLineH });
      }
    }
    cells = next;
  }

  function resize() {
    const rect = canvas.getBoundingClientRect();
    rectW = Math.max(1, Math.round(rect.width));
    rectH = Math.max(1, Math.round(rect.height));
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = rectW * dpr;
    canvas.height = rectH * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    buildGrid();
    if (prefersReduced) draw(0);
  }

  function draw(tMs) {
    const t = tMs / 1000;
    ctx.clearRect(0, 0, rectW, rectH);
    ctx.textBaseline = "alphabetic";

    const rotWave = Math.max(90, rectW * 0.22);
    const rotClamp = 16;

    for (const cell of cells) {
      let dark = fieldValue(cell.x / rectW, cell.y / rectH, t);
      dark = Math.max(0, Math.min(1, dark));
      if (dark < FLOOR) continue;
      const dk = Math.pow(dark, GAMMA);

      const fs = cell.lineH * (SIZE_MIN_RATIO + (SIZE_MAX_RATIO - SIZE_MIN_RATIO) * dk);
      const bold = dk > BOLD_THRESHOLD;
      const isAccent = dk > ACCENT_THRESHOLD && cell.x / rectW > 0.32 && cell.x / rectW < 0.68;

      let ang = rotClamp * Math.sin((2 * Math.PI * cell.x) / rotWave + cell.rowPhase);
      ang = Math.max(-rotClamp, Math.min(rotClamp, ang));

      ctx.save();
      ctx.translate(cell.x, cell.y);
      ctx.rotate((ang * Math.PI) / 180);
      ctx.font = `${bold ? 800 : 420} ${fs.toFixed(1)}px "Archivo Variable", sans-serif`;
      ctx.fillStyle = isAccent ? accent : ink;
      ctx.globalAlpha = 0.55 + 0.45 * dk;
      ctx.fillText(cell.ch, 0, 0);
      ctx.restore();
    }
  }

  function tick(tMs) {
    draw(tMs);
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

  function setPointer(nx, ny, active) {
    pointer.x = nx;
    pointer.y = ny;
    pointer.active = active;
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

  document.addEventListener("visibilitychange", () => {
    if (document.hidden) stop();
    else if (visible) start();
  });

  resize();
  start();

  const api = {
    setPointer,
    clearPointer: () => setPointer(pointer.x, pointer.y, 0),
    destroy: () => {
      stop();
      ro.disconnect();
      io.disconnect();
    },
    _debug: () => {
      const t = performance.now() / 1000;
      const darks = cells.map((c) => fieldValue(c.x / rectW, c.y / rectH, t));
      const above = darks.filter((d) => d >= FLOOR).length;
      return {
        running,
        visible,
        rectW,
        rectH,
        cellCount: cells.length,
        centerDark: fieldValue(0.5, 0.42, t),
        maxDark: Math.max(...darks),
        aboveFloorCount: above,
        blobsSnapshot: blobs.map((b) => ({ cx: b.cx, cy: b.cy, amp: b.amp })),
      };
    },
  };
  if (import.meta.env.DEV) window.__heroDebug = api._debug;
  return api;
}
