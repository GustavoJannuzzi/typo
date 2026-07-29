/**
 * Divide o texto de um elemento em <span class="char"> por caractere,
 * preservando espacos. E a base do assemble.js (entrada por scroll) e do
 * wobble.js (balanco continuo).
 *
 * Acessibilidade: o texto original fica em aria-label no elemento pai;
 * cada span vira aria-hidden, para leitor de tela ler a palavra inteira
 * em vez de soletrar.
 */
export function splitText(el) {
  const text = el.textContent.trim();
  el.setAttribute("aria-label", text);
  el.innerHTML = "";
  const spans = [];
  let i = 0;
  for (const ch of text) {
    const isSpace = ch === " ";
    const span = document.createElement("span");
    span.className = isSpace ? "char char--space" : "char";
    span.textContent = isSpace ? " " : ch;
    span.setAttribute("aria-hidden", "true");
    span.style.display = "inline-block";
    span.dataset.index = String(i++);
    el.appendChild(span);
    spans.push(span);
  }
  return spans;
}
