/**
 * Balanco continuo das letras — homenagem visual a ondulacao de
 * `src/typo/typography.py`:
 *
 *     y   = amp * sin(2*pi*x/onda + fase_da_linha)
 *     rot = theta * sin(2*pi*x/onda_rot + fase)
 *
 * Aqui `x` e o INDICE do caractere (nao pixel de imagem) e o "tempo" faz as
 * vezes do avanco de leitura do motor original — e uma porta conceitual,
 * nao literal, pensada pra rodar em requestAnimationFrame no navegador.
 *
 * Um unico rAF pra pagina inteira: cada grupo registrado (registerWobble)
 * tem sua propria amplitude/fase, mas todos sao avaliados no mesmo tick.
 */
const groups = [];
let running = false;
let rafId = null;
const prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

export function registerWobble(spans, opts = {}) {
  if (prefersReduced || !spans || !spans.length) return () => {};
  const {
    ampY = 2.6,
    ampRot = 3.8,
    wavelength = 8,
    speed = 1,
    seedOffset = 0,
    maxChars = 220,
  } = opts;

  const targets = spans.slice(0, maxChars);
  const group = { spans: targets, ampY, ampRot, wavelength, speed, seedOffset, active: true };
  groups.push(group);
  start();

  return () => {
    group.active = false;
    const idx = groups.indexOf(group);
    if (idx >= 0) groups.splice(idx, 1);
    if (!groups.length) stop();
  };
}

function tick(t) {
  const time = t / 1000;
  for (const g of groups) {
    if (!g.active) continue;
    for (const span of g.spans) {
      const i = Number(span.dataset.index || 0);
      const phase = (i / g.wavelength) * Math.PI * 2 + g.seedOffset;
      const y = Math.sin(time * g.speed + phase) * g.ampY;
      const rot = Math.sin(time * g.speed * 0.82 + phase * 1.3) * g.ampRot;
      span.style.transform = `translateY(${y.toFixed(2)}px) rotate(${rot.toFixed(2)}deg)`;
    }
  }
  rafId = requestAnimationFrame(tick);
}

function start() {
  if (running) return;
  running = true;
  rafId = requestAnimationFrame(tick);
}

function stop() {
  running = false;
  if (rafId) cancelAnimationFrame(rafId);
  rafId = null;
}

/** pausa tudo (ex: aba em background) sem perder os grupos registrados */
export function pauseWobble() {
  if (rafId) cancelAnimationFrame(rafId);
  running = false;
}

export function resumeWobble() {
  if (!running && groups.length) start();
}
