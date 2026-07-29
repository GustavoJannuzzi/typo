/**
 * O cursor como instrumento de medida — no hero, o ponteiro carrega uma
 * pequena leitura em fonte mono (LUM / X / Y), como se estivesse sondando
 * a escuridao local do jeito que `typography.py` sonda a imagem de
 * referencia. So aparece em dispositivos com ponteiro fino (mouse) — em
 * touch a leitura nao faz sentido e fica desligada.
 *
 * `onMove(nx, ny, active)` alimenta o halftoneCanvas para a "lupa" reagir
 * ao ponteiro.
 */
export function initProbeCursor(root, label, { onMove, onLeave } = {}) {
  const fine = window.matchMedia("(hover: hover) and (pointer: fine)").matches;
  if (!fine || !label) {
    return { destroy() {} };
  }

  function pseudoLum(nx, ny) {
    const v = 0.5 + 0.5 * Math.sin(nx * 7.3) * Math.cos(ny * 5.1 + nx * 2.2);
    return Math.max(0, Math.min(1, v));
  }

  function handleMove(e) {
    const rect = root.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    if (x < 0 || y < 0 || x > rect.width || y > rect.height) return;
    const nx = x / rect.width;
    const ny = y / rect.height;
    label.hidden = false;
    label.style.left = `${x}px`;
    label.style.top = `${y}px`;
    label.textContent = `LUM ${pseudoLum(nx, ny).toFixed(2)} · X ${Math.round(x)} Y ${Math.round(y)}`;
    onMove && onMove(nx, ny, 1);
  }

  function handleLeave() {
    label.hidden = true;
    onLeave && onLeave();
    onMove && onMove(0.5, 0.4, 0);
  }

  root.addEventListener("pointermove", handleMove);
  root.addEventListener("pointerleave", handleLeave);

  return {
    destroy() {
      root.removeEventListener("pointermove", handleMove);
      root.removeEventListener("pointerleave", handleLeave);
    },
  };
}
