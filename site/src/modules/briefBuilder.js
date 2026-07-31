import { whatsappLink } from "../config.js";
import { t } from "../i18n/runtime.js";

/**
 * O construtor de pedido — resolve "sem e-commerce": em vez de formulario
 * que envia pra algum lugar, monta a MENSAGEM que o proprio visitante manda
 * pelo WhatsApp dele. Nada sai deste navegador por aqui.
 *
 * A mensagem sai no idioma da pagina: ela parte do WhatsApp do visitante, e
 * ninguem manda o que nao consegue ler. Os valores sao sempre os mesmos cinco
 * / sete / quatro, entao do lado de ca' da' pra reconhecer o pedido em
 * qualquer idioma.
 */
const SUBJECT_OPTIONS = ["pessoa", "pet", "casal", "lugar", "outra"];

const WORDS_OPTIONS = ["musica", "carta", "frases", "texto", "votos", "familia", "poema"];

// `family` casa com o campo homonimo de works.json — e' o que escolhe a
// miniatura de exemplo de cada estilo
const STYLE_OPTIONS = [
  { value: "retrato", family: "retrato" },
  { value: "cena", family: "cena" },
  { value: "paisagem", family: "paisagem" },
  { value: "estencil", family: "estencil" },
];

function labelOf(group, value) {
  return value ? t(`brief.${group}.${value}`) : "—";
}

function renderPills(container, group, values, current, onPick) {
  container.innerHTML = "";
  values.forEach((value) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "pill";
    btn.textContent = t(`brief.${group}.${value}`);
    btn.setAttribute("aria-pressed", String(value === current));
    if (value === current) btn.classList.add("is-active");
    btn.addEventListener("click", () => onPick(value));
    container.appendChild(btn);
  });
}

function renderStyleOptions(container, works, current, onPick) {
  container.innerHTML = "";
  STYLE_OPTIONS.forEach((opt) => {
    const sample = works.find((w) => w.family === opt.family);
    const card = document.createElement("button");
    card.type = "button";
    card.className = "style-option";
    card.setAttribute("aria-pressed", String(opt.value === current));
    if (opt.value === current) card.classList.add("is-active");
    card.innerHTML = `
      <span class="style-option__frame">
        ${sample ? `<img src="/art/${sample.slug}-thumb.webp" alt="" loading="lazy" width="400" height="300" />` : ""}
      </span>
      <span class="style-option__label">
        <span class="style-option__title">${t(`brief.style.${opt.value}`)}</span>
        <span class="style-option__desc">${t(`brief.style.${opt.value}.desc`)}</span>
      </span>
    `;
    card.addEventListener("click", () => onPick(opt.value));
    container.appendChild(card);
  });
}

function buildMessage(state) {
  const lines = [
    t("brief.msg.intro"),
    "",
    t("brief.msg.subject", { v: labelOf("subject", state.subject) }),
    t("brief.msg.words", { v: labelOf("words", state.words) }),
    t("brief.msg.style", { v: labelOf("style", state.style) }),
    "",
    t("brief.msg.name", { v: state.name || "—" }),
    t("brief.msg.email", { v: state.email || "—" }),
    "",
    t("brief.msg.tail"),
  ];
  return lines.join("\n");
}

export function initBriefBuilder(form, works) {
  const state = { subject: null, words: null, style: null, name: "", email: "" };

  const subjectEl = form.querySelector('[data-field="subject"]');
  const wordsEl = form.querySelector('[data-field="words"]');
  const styleEl = form.querySelector('[data-field="style"]');
  const nameEl = form.querySelector("[data-field-name]");
  const emailEl = form.querySelector("[data-field-email]");
  const previewEl = form.querySelector("[data-brief-preview]");
  const submitEl = form.querySelector("[data-brief-submit]");

  function update() {
    const message = buildMessage(state);
    previewEl.textContent = message;
    submitEl.href = whatsappLink(message);
  }

  function pickSubject(value) {
    state.subject = value;
    renderPills(subjectEl, "subject", SUBJECT_OPTIONS, state.subject, pickSubject);
    update();
  }
  function pickWords(value) {
    state.words = value;
    renderPills(wordsEl, "words", WORDS_OPTIONS, state.words, pickWords);
    update();
  }
  function pickStyle(value) {
    state.style = value;
    renderStyleOptions(styleEl, works, state.style, pickStyle);
    update();
  }

  renderPills(subjectEl, "subject", SUBJECT_OPTIONS, state.subject, pickSubject);
  renderPills(wordsEl, "words", WORDS_OPTIONS, state.words, pickWords);
  renderStyleOptions(styleEl, works, state.style, pickStyle);

  nameEl.addEventListener("input", () => {
    state.name = nameEl.value.trim();
    update();
  });
  emailEl.addEventListener("input", () => {
    state.email = emailEl.value.trim();
    update();
  });

  update();

  return { setStyle: pickStyle };
}
