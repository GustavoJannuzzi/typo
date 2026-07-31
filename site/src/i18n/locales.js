/**
 * Os idiomas da landing — fonte única da lista.
 *
 * Lido pelo plugin de build (`build/i18n.js`), que gera uma página por idioma,
 * o seletor visível e as tags `hreflang`. Para acrescentar um idioma: uma
 * entrada aqui + um `<code>.json` ao lado. A build reclama se faltar chave.
 *
 * `code` é o prefixo da URL (/en/), `htmlLang` vai no <html lang>, `locale`
 * é o que o navegador usa para formatar número (glifos, cm) e `label` é o
 * endônimo — o nome do idioma no próprio idioma, que é o que se põe num
 * seletor: quem lê italiano procura "Italiano", não "Italian".
 */
export const DEFAULT_LANG = "pt";

export const LOCALES = [
  { code: "pt", htmlLang: "pt-BR", locale: "pt-BR", ogLocale: "pt_BR", label: "Português", short: "PT" },
  { code: "en", htmlLang: "en", locale: "en-US", ogLocale: "en_US", label: "English", short: "EN" },
  { code: "es", htmlLang: "es", locale: "es-ES", ogLocale: "es_ES", label: "Español", short: "ES" },
  { code: "it", htmlLang: "it", locale: "it-IT", ogLocale: "it_IT", label: "Italiano", short: "IT" },
];

/** URL da versão: o idioma padrão mora na raiz, os outros em /<code>/. */
export function pathFor(code) {
  return code === DEFAULT_LANG ? "/" : `/${code}/`;
}
