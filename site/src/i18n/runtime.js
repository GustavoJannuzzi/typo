/**
 * As strings que o JS monta em tempo de execução.
 *
 * O texto da página já vem traduzido do build (uma página por idioma, ver
 * `build/i18n.js`). O que sobra são as strings que só existem depois que o JS
 * roda — rótulos da galeria, opções do construtor de pedido, a mensagem do
 * WhatsApp. Essas viajam num `<script type="application/json">` injetado na
 * página, **só as do idioma dela**: nenhum dicionário dos outros três entra no
 * bundle.
 *
 * Sem o bloco (ex.: abrir o index.html cru, fora do Vite), cai no português.
 */
const el = document.querySelector("[data-i18n-runtime]");
const data = el ? JSON.parse(el.textContent) : {};

export const LANG = data.lang || "pt";
export const LOCALE = data.locale || "pt-BR";

const STRINGS = data.js || {};
const WORKS = data.works || {};

/** `t("slots.remaining", { n: 3, total: 5 })` — chave sem tradução aparece crua. */
export function t(key, vars) {
  let value = STRINGS[key];
  if (value === undefined) return key;
  if (vars) {
    for (const name in vars) value = value.split(`{${name}}`).join(vars[name]);
  }
  return value;
}

/** Número no formato do idioma: 35.880 em pt/es/it, 35,880 em en. */
export function num(value) {
  return typeof value === "number" ? value.toLocaleString(LOCALE) : String(value ?? "—");
}

/**
 * Título e subtítulo das obras NÃO se traduzem: estão impressos no pôster, em
 * português — são parte da arte. O que se traduz é o texto de apoio (o blurb)
 * e, quando ajuda, uma tradução ao lado do título (`gloss`), que descreve sem
 * substituir.
 */
export function workBlurb(work) {
  return WORKS[work.slug]?.blurb || work.blurb;
}

export function workGloss(work) {
  return WORKS[work.slug]?.gloss || "";
}
