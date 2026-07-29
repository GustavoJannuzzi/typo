/**
 * Comparador "arrasta pra revelar": a imagem ANTES (foto de referencia)
 * fica clipada dentro de uma mascara cuja largura e controlada pelo
 * arraste (mouse, touque ou teclado via <input type="range">). A imagem
 * DEPOIS (arte final) preenche o quadro inteiro por baixo.
 *
 * A mascara (.compare__before-wrap) tem largura em % igual a posicao do
 * arraste; a imagem dentro dela mantem a largura TOTAL do quadro (via
 * --frame-w), entao o que muda e uma "janela" sobre uma imagem de tamanho
 * fixo — nao um esticar/encolher da foto.
 */
export function initWipeCompare(root) {
  const frame = root.querySelector("[data-compare-frame]");
  const wrap = root.querySelector("[data-compare-before-wrap]");
  const handle = root.querySelector("[data-compare-handle]");
  const range = root.querySelector("[data-compare-range]");
  if (!frame || !wrap || !handle || !range) return { destroy() {} };

  let dragging = false;

  function syncFrameWidth() {
    frame.style.setProperty("--frame-w", `${frame.clientWidth}px`);
  }

  function setPct(pct) {
    const clamped = Math.max(0, Math.min(100, pct));
    wrap.style.width = `${clamped}%`;
    handle.style.left = `${clamped}%`;
    range.value = String(Math.round(clamped));
  }

  function pctFromClientX(clientX) {
    const rect = frame.getBoundingClientRect();
    return ((clientX - rect.left) / rect.width) * 100;
  }

  function onPointerDown(e) {
    dragging = true;
    frame.setPointerCapture?.(e.pointerId);
    setPct(pctFromClientX(e.clientX));
  }

  function onPointerMove(e) {
    if (!dragging) return;
    setPct(pctFromClientX(e.clientX));
  }

  function onPointerUp(e) {
    dragging = false;
    frame.releasePointerCapture?.(e.pointerId);
  }

  frame.addEventListener("pointerdown", onPointerDown);
  frame.addEventListener("pointermove", onPointerMove);
  frame.addEventListener("pointerup", onPointerUp);
  frame.addEventListener("pointercancel", onPointerUp);

  range.addEventListener("input", () => setPct(Number(range.value)));

  const ro = new ResizeObserver(syncFrameWidth);
  ro.observe(frame);
  syncFrameWidth();
  setPct(50);

  return {
    destroy() {
      frame.removeEventListener("pointerdown", onPointerDown);
      frame.removeEventListener("pointermove", onPointerMove);
      frame.removeEventListener("pointerup", onPointerUp);
      frame.removeEventListener("pointercancel", onPointerUp);
      ro.disconnect();
    },
  };
}
