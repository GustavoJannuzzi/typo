import { splitText } from "./splitText.js";

const prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const SEEN_KEY = "omp-intro-seen";

/**
 * A marca se monta a partir de letras espalhadas — a primeira coisa que o
 * visitante ve. Dura menos de 1s de assentamento, e pulavel a qualquer
 * momento. So toca uma vez por sessao de aba (sessionStorage) e nunca com
 * prefers-reduced-motion.
 */
export function runIntro(root) {
  const textEl = root.querySelector("[data-intro-text]");
  const skipBtn = root.querySelector("[data-intro-skip]");

  const finish = () => {
    root.classList.add("is-done");
    document.body.classList.remove("intro-lock");
    window.setTimeout(() => root.remove(), 520);
  };

  if (prefersReduced || sessionStorage.getItem(SEEN_KEY) === "1") {
    root.remove();
    document.body.classList.remove("intro-lock");
    return;
  }
  sessionStorage.setItem(SEEN_KEY, "1");
  document.body.classList.add("intro-lock");

  const spans = splitText(textEl);
  spans.forEach((span) => {
    if (span.classList.contains("char--space")) return;
    const dx = (Math.random() * 2 - 1) * 130;
    const dy = (Math.random() * 2 - 1) * 80;
    const rot = (Math.random() * 2 - 1) * 55;
    span.style.transform = `translate(${dx.toFixed(1)}px, ${dy.toFixed(1)}px) rotate(${rot.toFixed(1)}deg)`;
    span.style.opacity = "0";
    span.style.transition = "transform 620ms var(--ease-out), opacity 400ms linear";
  });

  requestAnimationFrame(() => {
    spans.forEach((span, i) => {
      window.setTimeout(() => {
        span.style.transform = "translate(0,0) rotate(0deg)";
        span.style.opacity = "1";
      }, i * 24);
    });
  });

  const total = spans.length * 24 + 620;
  const autoTimer = window.setTimeout(finish, total + 360);

  skipBtn.addEventListener(
    "click",
    () => {
      window.clearTimeout(autoTimer);
      finish();
    },
    { once: true }
  );
}
