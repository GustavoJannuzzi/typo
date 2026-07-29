import { CONFIG, whatsappLink } from "../config.js";

/**
 * O construtor de pedido — resolve "sem e-commerce": em vez de formulario
 * que envia pra algum lugar, monta a MENSAGEM que o proprio visitante manda
 * pelo WhatsApp dele. Nada sai deste navegador por aqui.
 */
const SUBJECT_OPTIONS = [
  { value: "pessoa", label: "📷 Uma pessoa" },
  { value: "pet", label: "🐾 Um pet" },
  { value: "casal", label: "💍 Um casal" },
  { value: "lugar", label: "🏡 Um lugar especial" },
  { value: "outra", label: "✨ Outra imagem" },
];

const WORDS_OPTIONS = [
  { value: "musica", label: "🎵 Letra de música" },
  { value: "carta", label: "💌 Carta ou mensagem" },
  { value: "frases", label: "❤️ Frases importantes" },
  { value: "texto", label: "📖 Texto pessoal" },
  { value: "votos", label: "✍️ Votos de casamento" },
  { value: "familia", label: "👨‍👩‍👧 História de família" },
  { value: "poema", label: "🌎 Poema ou lembrança" },
];

const STYLE_OPTIONS = [
  { value: "retrato", label: "Retrato", desc: "Rosto ou figura em foco, fundo limpo.", family: "retrato" },
  { value: "cena", label: "Cena inteira", desc: "Halftone puro, textura da foto toda.", family: "cena" },
  { value: "paisagem", label: "Paisagem", desc: "Figura isolada, horizonte ao fundo.", family: "paisagem" },
  { value: "estencil", label: "Estêncil", desc: "Alto contraste, gráfico, cartaz.", family: "estencil" },
];

function labelOf(options, value) {
  return options.find((o) => o.value === value)?.label ?? "—";
}

function renderPills(container, options, current, onPick) {
  container.innerHTML = "";
  options.forEach((opt) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "pill";
    btn.textContent = opt.label;
    btn.setAttribute("aria-pressed", String(opt.value === current));
    if (opt.value === current) btn.classList.add("is-active");
    btn.addEventListener("click", () => onPick(opt.value));
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
        <span class="style-option__title">${opt.label}</span>
        <span class="style-option__desc">${opt.desc}</span>
      </span>
    `;
    card.addEventListener("click", () => onPick(opt.value));
    container.appendChild(card);
  });
}

function buildMessage(state) {
  const lines = [
    "Olá! Quero encomendar uma arte da Onde Moram as Palavras ✦",
    "",
    `O que vai virar arte: ${labelOf(SUBJECT_OPTIONS, state.subject)}`,
    `Palavras da obra: ${labelOf(WORDS_OPTIONS, state.words)}`,
    `Estilo: ${labelOf(STYLE_OPTIONS, state.style)}`,
    "",
    `Nome: ${state.name || "—"}`,
    `E-mail: ${state.email || "—"}`,
    "",
    "(Vou enviar a imagem e o texto completo por aqui.)",
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
    renderPills(subjectEl, SUBJECT_OPTIONS, state.subject, pickSubject);
    update();
  }
  function pickWords(value) {
    state.words = value;
    renderPills(wordsEl, WORDS_OPTIONS, state.words, pickWords);
    update();
  }
  function pickStyle(value) {
    state.style = value;
    renderStyleOptions(styleEl, works, state.style, pickStyle);
    update();
  }

  renderPills(subjectEl, SUBJECT_OPTIONS, state.subject, pickSubject);
  renderPills(wordsEl, WORDS_OPTIONS, state.words, pickWords);
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
