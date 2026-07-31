/**
 * Tabela de easings nomeados. O roteiro escreve `ease: "saidaExpo"` e nunca
 * uma funcao — assim o roteiro continua sendo DADO, e afinar o ritmo de um
 * plano nao passa por editar codigo.
 *
 * Tambem aceita "cubic-bezier(a,b,c,d)" pra quando nenhum nome servir, com os
 * mesmos numeros que o CSS usa (da' pra copiar de --ease-out do base.css).
 */

const bezier = (x1, y1, x2, y2) => {
  // Newton-Raphson em x, depois avalia y. Suficiente e estavel para 60fps.
  const A = (a, b) => 1 - 3 * b + 3 * a;
  const B = (a, b) => 3 * b - 6 * a;
  const C = (a) => 3 * a;
  const calc = (t, a, b) => ((A(a, b) * t + B(a, b)) * t + C(a)) * t;
  const deriv = (t, a, b) => 3 * A(a, b) * t * t + 2 * B(a, b) * t + C(a);
  return (x) => {
    if (x <= 0) return 0;
    if (x >= 1) return 1;
    let t = x;
    for (let i = 0; i < 8; i++) {
      const d = deriv(t, x1, x2);
      if (Math.abs(d) < 1e-6) break;
      t -= (calc(t, x1, x2) - x) / d;
    }
    return calc(t, y1, y2);
  };
};

export const EASINGS = {
  linear: (t) => t,

  entradaQuad: (t) => t * t,
  saidaQuad: (t) => 1 - (1 - t) * (1 - t),
  suaveQuad: (t) => (t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2),

  entradaCubica: (t) => t * t * t,
  saidaCubica: (t) => 1 - Math.pow(1 - t, 3),
  suaveCubica: (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2),

  entradaQuinta: (t) => t ** 5,
  saidaQuinta: (t) => 1 - Math.pow(1 - t, 5),
  suaveQuinta: (t) => (t < 0.5 ? 16 * t ** 5 : 1 - Math.pow(-2 * t + 2, 5) / 2),

  entradaExpo: (t) => (t === 0 ? 0 : Math.pow(2, 10 * t - 10)),
  saidaExpo: (t) => (t === 1 ? 1 : 1 - Math.pow(2, -10 * t)),
  suaveExpo: (t) =>
    t === 0 ? 0 : t === 1 ? 1 : t < 0.5 ? Math.pow(2, 20 * t - 10) / 2 : (2 - Math.pow(2, -20 * t + 10)) / 2,

  /** um respiro no fim, sem passar do ponto — bom pra pouso de camera */
  pouso: bezier(0.16, 1, 0.3, 1), // = var(--ease-out) do site
  /** simetrico, para movimentos que saem e chegam parados */
  vaiEVolta: bezier(0.65, 0, 0.35, 1), // = var(--ease-in-out) do site
  /** ultrapassa um tico e volta: da' peso a um corte seco */
  recuo: (t) => {
    const c = 1.70158;
    return 1 + (c + 1) * Math.pow(t - 1, 3) + c * Math.pow(t - 1, 2);
  },
};

export function resolverEase(nome) {
  if (typeof nome === "function") return nome;
  if (!nome) return EASINGS.pouso;
  const bz = String(nome).match(
    /cubic-bezier\(\s*([-\d.]+)\s*,\s*([-\d.]+)\s*,\s*([-\d.]+)\s*,\s*([-\d.]+)\s*\)/
  );
  if (bz) return bezier(+bz[1], +bz[2], +bz[3], +bz[4]);
  const f = EASINGS[nome];
  if (!f) {
    throw new Error(
      `easing desconhecido: "${nome}". Disponiveis: ${Object.keys(EASINGS).join(", ")} — ou cubic-bezier(a,b,c,d).`
    );
  }
  return f;
}
