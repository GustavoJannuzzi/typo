/**
 * A coleção como bancada de espécimes: monta os cartões a partir de
 * works.json (dados reais dos exports em 150 dpi) e controla o overlay de
 * detalhe — o momento em que se ve que a imagem e feita de letras.
 */
const LAYER_LABELS = {
  "máscara": "máscara",
  "halftone puro": "halftone puro",
  paisagem: "paisagem",
  accent: "accent",
};

function specLine(work) {
  return [
    work.font,
    `${work.bodyMm.toLocaleString("pt-BR")} mm`,
    work.layers.map((l) => LAYER_LABELS[l] || l).join(" + "),
  ];
}

function cardTemplate(work) {
  const card = document.createElement("article");
  card.className = "gallery-card";
  card.setAttribute("role", "listitem");
  card.tabIndex = 0;
  card.dataset.slug = work.slug;

  const specs = specLine(work)
    .map((s) => `<span>${s}</span>`)
    .join("");

  card.innerHTML = `
    <div class="gallery-card__frame">
      <img src="/art/${work.slug}-thumb.webp" alt="Obra ${work.title}" loading="lazy" width="800" height="${Math.round(800 / work.aspect)}" />
    </div>
    <div class="gallery-card__body">
      <p class="display gallery-card__title">${work.title}</p>
      <p class="gallery-card__subtitle">${work.subtitle}</p>
      <div class="gallery-card__specs readout">${specs}</div>
    </div>
  `;
  return card;
}

export function initGallery(railEl, detailEl, works) {
  works.forEach((work) => railEl.appendChild(cardTemplate(work)));

  const img = detailEl.querySelector("[data-gallery-detail-img]");
  const eyebrow = detailEl.querySelector("[data-gallery-detail-eyebrow]");
  const title = detailEl.querySelector("[data-gallery-detail-title]");
  const meta = detailEl.querySelector("[data-gallery-detail-meta]");
  const blurb = detailEl.querySelector("[data-gallery-detail-blurb]");
  const toggleBtn = detailEl.querySelector("[data-gallery-toggle]");
  const closeEls = detailEl.querySelectorAll("[data-gallery-close]");

  let current = null;
  let showingDetail = true;
  let lastFocused = null;

  function render() {
    if (!current) return;
    img.src = showingDetail ? `/art/${current.slug}-detail.webp` : `/art/${current.slug}-full.webp`;
    img.alt = showingDetail
      ? `Detalhe ampliado da obra ${current.title}, mostrando as letras que a formam`
      : `Obra ${current.title} completa`;
    toggleBtn.textContent = showingDetail ? "Ver obra inteira" : "Ver de perto";
  }

  function open(work) {
    current = work;
    showingDetail = true;
    eyebrow.textContent = `${work.widthCm} × ${work.heightCm} cm · ${work.glyphs?.toLocaleString("pt-BR") ?? "—"} glifos`;
    title.textContent = work.title;
    meta.textContent = `${work.font} · ${work.bodyMm} mm · ${work.layers.join(" + ")}`;
    blurb.textContent = work.blurb;
    render();
    lastFocused = document.activeElement;
    detailEl.hidden = false;
    document.body.style.overflow = "hidden";
    detailEl.querySelector("[data-gallery-close]").focus();
  }

  function close() {
    detailEl.hidden = true;
    document.body.style.overflow = "";
    current = null;
    lastFocused?.focus?.();
  }

  railEl.addEventListener("click", (e) => {
    const card = e.target.closest(".gallery-card");
    if (!card) return;
    const work = works.find((w) => w.slug === card.dataset.slug);
    if (work) open(work);
  });

  railEl.addEventListener("keydown", (e) => {
    if (e.key !== "Enter" && e.key !== " ") return;
    const card = e.target.closest(".gallery-card");
    if (!card) return;
    e.preventDefault();
    const work = works.find((w) => w.slug === card.dataset.slug);
    if (work) open(work);
  });

  toggleBtn.addEventListener("click", () => {
    showingDetail = !showingDetail;
    render();
  });

  closeEls.forEach((el) => el.addEventListener("click", close));

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !detailEl.hidden) close();
  });

  return { open, close };
}
