import { CONFIG, whatsappLink } from "./config.js";
import works from "./data/works.json";
import { t } from "./i18n/runtime.js";

import { runIntro } from "./modules/intro.js";
import { assemble } from "./modules/assemble.js";
import { registerWobble } from "./modules/wobble.js";
import { initHaltoneCanvas } from "./modules/halftoneCanvas.js";
import { initWipeCompare } from "./modules/wipeCompare.js";
import { initGallery } from "./modules/gallery.js";
import { initBriefBuilder } from "./modules/briefBuilder.js";

// --- intro --------------------------------------------------------------
const introEl = document.querySelector("[data-intro]");
if (introEl) runIntro(introEl);

// --- idioma: a escolha manual manda --------------------------------------
// A raiz redireciona por navigator.language (script inline no <head>), mas
// quem troca de idioma na mao trava a escolha: dai em diante nunca mais e'
// mandado pra outra versao. Sem isso, um brasileiro no exterior com o
// navegador em ingles nao conseguiria ficar no portugues.
document.querySelectorAll("[data-lang-link]").forEach((link) => {
  link.addEventListener("click", () => {
    try {
      localStorage.setItem("omp-lang", link.dataset.langLink);
    } catch (e) {
      /* modo privado: sem memoria, mas a navegacao segue */
    }
  });
});

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

// --- header: seletor de idioma vira dropdown no mobile --------------------
const langSwitch = document.querySelector("[data-lang-switch]");
const langToggle = document.querySelector("[data-lang-toggle]");
if (langSwitch && langToggle) {
  langToggle.addEventListener("click", () => {
    const open = langSwitch.classList.toggle("is-open");
    langToggle.setAttribute("aria-expanded", String(open));
  });
  document.addEventListener("click", (e) => {
    if (langSwitch.classList.contains("is-open") && !langSwitch.contains(e.target)) {
      langSwitch.classList.remove("is-open");
      langToggle.setAttribute("aria-expanded", "false");
    }
  });
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

// --- hero: canvas vivo (respiracao + rolagem) ----------------------------
const heroCanvas = document.querySelector("[data-hero-canvas]");
if (heroCanvas) initHaltoneCanvas(heroCanvas);

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
  const vars = { n: slotsRemaining, total: CONFIG.LAUNCH_SLOTS_TOTAL };
  el.textContent =
    slotsRemaining > 1
      ? t("slots.remaining", vars)
      : slotsRemaining === 1
        ? t("slots.remainingOne", vars)
        : t("slots.soldOut");
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
  waLink.href = whatsappLink(t("footer.waMessage"));
  waLink.textContent = "WhatsApp";
  waLink.target = "_blank";
  waLink.rel = "noopener";
}
const emailLink = document.querySelector("[data-footer-email]");
if (emailLink && CONFIG.EMAIL) {
  emailLink.href = `mailto:${CONFIG.EMAIL}`;
  emailLink.textContent = CONFIG.EMAIL;
}
