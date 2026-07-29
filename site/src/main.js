import { CONFIG, whatsappLink } from "./config.js";
import works from "./data/works.json";

import { runIntro } from "./modules/intro.js";
import { assemble } from "./modules/assemble.js";
import { registerWobble } from "./modules/wobble.js";
import { initHaltoneCanvas } from "./modules/halftoneCanvas.js";
import { initProbeCursor } from "./modules/probeCursor.js";
import { initWipeCompare } from "./modules/wipeCompare.js";
import { initGallery } from "./modules/gallery.js";
import { initBriefBuilder } from "./modules/briefBuilder.js";

// --- intro --------------------------------------------------------------
const introEl = document.querySelector("[data-intro]");
if (introEl) runIntro(introEl);

// --- header: menu mobile -------------------------------------------------
const navToggle = document.querySelector("[data-nav-toggle]");
const nav = document.querySelector("[data-nav]");
if (navToggle && nav) {
  navToggle.addEventListener("click", () => {
    const open = nav.classList.toggle("is-open");
    navToggle.setAttribute("aria-expanded", String(open));
  });
  nav.querySelectorAll("a").forEach((a) =>
    a.addEventListener("click", () => {
      nav.classList.remove("is-open");
      navToggle.setAttribute("aria-expanded", "false");
    })
  );
}

// --- textos que se montam ao entrar na tela ------------------------------
document.querySelectorAll("[data-assemble]").forEach((el) => {
  const isHero = el.hasAttribute("data-wobble");
  assemble(el, {
    threshold: isHero ? 0.1 : 0.4,
    onSettled: isHero
      ? (spans) => registerWobble(spans, { ampY: 2.2, ampRot: 3.2, wavelength: 7 })
      : undefined,
  });
});

// --- hero: canvas vivo + cursor-instrumento ------------------------------
const heroSection = document.querySelector(".hero");
const heroCanvas = document.querySelector("[data-hero-canvas]");
const probeLabel = document.querySelector("[data-probe]");
if (heroSection && heroCanvas) {
  const canvasApi = initHaltoneCanvas(heroCanvas);
  if (probeLabel) {
    initProbeCursor(heroSection, probeLabel, {
      onMove: (nx, ny, active) => canvasApi.setPointer(nx, ny, active),
      onLeave: () => canvasApi.clearPointer(),
    });
  }
}

// --- coleção --------------------------------------------------------------
const galleryRail = document.querySelector("[data-gallery]");
const galleryDetail = document.querySelector("[data-gallery-detail]");
if (galleryRail && galleryDetail) {
  initGallery(galleryRail, galleryDetail, works);
}

// --- comparador antes/depois ----------------------------------------------
const compareEl = document.querySelector("[data-compare]");
if (compareEl) initWipeCompare(compareEl);

// --- edição de lançamento: vagas e preços ---------------------------------
const slotsRemaining = Math.max(0, CONFIG.LAUNCH_SLOTS_TOTAL - CONFIG.LAUNCH_SLOTS_TAKEN);
document.querySelectorAll("[data-slots-total]").forEach((el) => {
  el.textContent = String(CONFIG.LAUNCH_SLOTS_TOTAL);
});
document.querySelectorAll("[data-slots-remaining]").forEach((el) => {
  el.textContent =
    slotsRemaining > 0
      ? `restam ${slotsRemaining} de ${CONFIG.LAUNCH_SLOTS_TOTAL} vagas`
      : "vagas de lançamento esgotadas";
});
document.querySelectorAll("[data-price-launch]").forEach((el) => {
  el.textContent = CONFIG.LAUNCH_PRICE;
});
document.querySelectorAll("[data-price-regular]").forEach((el) => {
  el.textContent = CONFIG.REGULAR_PRICE;
});

// --- construtor de pedido ---------------------------------------------
const briefForm = document.querySelector("[data-brief-form]");
if (briefForm) initBriefBuilder(briefForm, works);

// --- rodapé: contatos -------------------------------------------------
const waLink = document.querySelector("[data-footer-whatsapp]");
if (waLink && CONFIG.WHATSAPP) {
  waLink.href = whatsappLink("Olá! Quero saber mais sobre a Onde Moram as Palavras.");
  waLink.textContent = "WhatsApp";
  waLink.target = "_blank";
  waLink.rel = "noopener";
}
const emailLink = document.querySelector("[data-footer-email]");
if (emailLink && CONFIG.EMAIL) {
  emailLink.href = `mailto:${CONFIG.EMAIL}`;
  emailLink.textContent = CONFIG.EMAIL;
}
