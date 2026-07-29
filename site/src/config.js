// Config da marca — preencha antes de publicar.
//
// WHATSAPP: DDI+DDD+numero, so digitos (ex: "5511987654321"). Usado em
// wa.me/<numero>?text=... — sem esse numero o botao de pedido nao funciona.
// EMAIL: para onde o arquivo final e' enviado (aparece no rodape/copy, nao
// e' usado para enviar nada por aqui — a pagina nao tem backend).

export const CONFIG = {
  BRAND: "Onde Moram as Palavras",
  WHATSAPP: "", // TODO: preencha antes de publicar, ex: "5511987654321"
  EMAIL: "", // TODO: preencha antes de publicar, ex: "contato@ondemoramaspalavras.com"
  INSTAGRAM: "", // opcional, ex: "@ondemoramaspalavras"

  LAUNCH_PRICE: "R$ 39,90",
  REGULAR_PRICE: "R$ 69,90",
  LAUNCH_SLOTS_TOTAL: 5,
  LAUNCH_SLOTS_TAKEN: 0, // TODO: atualize manualmente conforme forem vendendo
};

export function whatsappLink(message) {
  const digits = CONFIG.WHATSAPP.replace(/\D/g, "");
  const base = digits ? `https://wa.me/${digits}` : "https://wa.me/";
  return `${base}?text=${encodeURIComponent(message)}`;
}
