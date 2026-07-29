import { splitText } from "./splitText.js";

const prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/**
 * Anima a "montagem" de um texto: as letras entram espalhadas (posicao e
 * rotacao aleatorias) e se assentam no lugar quando o elemento cruza a
 * viewport, em cascata. E a animacao de rolagem central da pagina — o
 * equivalente visual de "as letras se organizam ate formar a imagem".
 *
 * Retorna os spans, para quem quiser encadear com registerWobble() depois
 * que a montagem terminar (ver onSettled).
 */
export function assemble(el, opts = {}) {
  const {
    distance = 42,
    rotation = 22,
    duration = 560,
    stagger = 16,
    threshold = 0.4,
    onSettled,
  } = opts;

  const spans = splitText(el);

  if (prefersReduced) {
    onSettled && onSettled(spans);
    return spans;
  }

  spans.forEach((span) => {
    if (span.classList.contains("char--space")) return;
    const dx = (Math.random() * 2 - 1) * distance;
    const dy = (Math.random() * 0.7 + 0.5) * distance * (Math.random() < 0.5 ? -1 : 1);
    const rot = (Math.random() * 2 - 1) * rotation;
    span.style.transform = `translate(${dx.toFixed(1)}px, ${dy.toFixed(1)}px) rotate(${rot.toFixed(1)}deg)`;
    span.style.opacity = "0";
    span.style.transition = `transform ${duration}ms var(--ease-out), opacity ${Math.round(duration * 0.7)}ms linear`;
  });

  let played = false;
  const play = () => {
    if (played) return;
    played = true;
    spans.forEach((span, i) => {
      window.setTimeout(() => {
        span.style.transform = "translate(0,0) rotate(0deg)";
        span.style.opacity = "1";
      }, i * stagger);
    });
    if (onSettled) {
      const total = spans.length * stagger + duration;
      window.setTimeout(() => {
        spans.forEach((span) => {
          span.style.transition = "";
        });
        onSettled(spans);
      }, total + 40);
    }
  };

  const io = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          play();
          io.unobserve(el);
        }
      });
    },
    { threshold, rootMargin: "0px 0px -10% 0px" }
  );
  io.observe(el);

  return spans;
}
