/**
 * i18n em tempo de build — uma página por idioma, não troca no cliente.
 *
 * Por quê: quem chega da Itália ou dos EUA chega pela busca. Dicionário
 * trocado no navegador dá uma URL só, um <title> só — o Google indexa uma
 * versão e as outras não existem para quem procura. Aqui cada idioma é uma
 * página de verdade (`/en/`, `/es/`, `/it/`), com o texto já no HTML, ligadas
 * entre si por `hreflang`. De quebra é mais leve: nenhum dicionário viaja no
 * bundle e não há texto trocando depois da primeira pintura.
 *
 * Fonte da verdade: `index.html` em português. Os elementos traduzíveis são
 * marcados com `data-i18n="chave"` (troca o conteúdo) e `data-i18n-attr=
 * "alt:chave,aria-label:chave"` (troca atributos). Os catálogos vivem em
 * `src/i18n/<code>.json`. O português NÃO tem catálogo de página: o texto do
 * `index.html` é o original. Faltando chave em en/es/it, a build quebra —
 * página publicada pela metade é pior que build vermelha.
 *
 * Três marcadores geram o que depende da lista de idiomas:
 *   <!--i18n:head-->              hreflang + canonical + og:locale + detecção
 *   <!--i18n:langswitch-->        seletor do cabeçalho
 *   <!--i18n:langswitch:footer--> seletor do rodapé
 *
 * As strings que o JS monta em tempo de execução (galeria, construtor de
 * pedido) não cabem no HTML: vão num `<script type="application/json">` no fim
 * do body — só as do idioma daquela página.
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { DEFAULT_LANG, LOCALES, pathFor } from "../src/i18n/locales.js";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const SITE_ROOT = path.resolve(HERE, "..");
const CATALOG_DIR = path.join(SITE_ROOT, "src", "i18n");
const MAIN_HTML = path.join(SITE_ROOT, "index.html");

/** Tags sem fechamento — `data-i18n` (conteúdo) nelas é erro de marcação. */
const VOID_TAGS = new Set([
  "area", "base", "br", "col", "embed", "hr", "img", "input",
  "link", "meta", "param", "source", "track", "wbr",
]);

// ---------------------------------------------------------------- catálogos

function loadCatalogs() {
  const catalogs = {};
  for (const loc of LOCALES) {
    const file = path.join(CATALOG_DIR, `${loc.code}.json`);
    catalogs[loc.code] = JSON.parse(fs.readFileSync(file, "utf8"));
  }
  return catalogs;
}

// ------------------------------------------------------------- html helpers

function attrValue(attrs, name) {
  const m = new RegExp(`\\s${name}="([^"]*)"`).exec(attrs);
  return m ? m[1] : null;
}

function setAttrValue(attrs, name, value) {
  const re = new RegExp(`(\\s${name}=")[^"]*(")`);
  if (re.test(attrs)) return attrs.replace(re, `$1${value}$2`);
  // tag auto-fechada (`<meta ... />`): o atributo novo entra antes da barra
  const trailing = /\s*\/$/.exec(attrs);
  if (trailing) return `${attrs.slice(0, trailing.index)} ${name}="${value}"${trailing[0]}`;
  return `${attrs} ${name}="${value}"`;
}

// leva junto o espaço/quebra de linha que vinha antes: senão a marcação
// deixa buraco no meio da tag depois de traduzida
function stripI18nAttrs(attrs) {
  return attrs.replace(/\s*\bdata-i18n(?:-attr)?="[^"]*"/g, "");
}

function escapeAttr(value) {
  return String(value).replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;");
}

/** Índice do `</tag>` que fecha a abertura em `from`, respeitando aninhamento. */
function findClose(html, tag, from) {
  const re = new RegExp(`<(/?)${tag}\\b`, "gi");
  re.lastIndex = from;
  let depth = 1;
  let m;
  while ((m = re.exec(html))) {
    depth += m[1] ? -1 : 1;
    if (depth === 0) return m.index;
  }
  return -1;
}

/** Nomes de `data-*` que o JS usa como gancho dentro de um trecho de HTML. */
function dataHooks(fragment) {
  return [...new Set((fragment.match(/\bdata-[a-z][\w-]*/g) || []))];
}

// ------------------------------------------------------------- markup gerado

function langSwitchHtml(current, catalog, variant) {
  const aria = escapeAttr(catalog.html?.["lang.aria"] || "Idioma");
  const links = LOCALES.map((loc) => {
    const isCurrent = loc.code === current.code;
    return (
      `<a href="${pathFor(loc.code)}" hreflang="${loc.htmlLang}" lang="${loc.htmlLang}"` +
      ` title="${escapeAttr(loc.label)}" data-lang-link="${loc.code}"` +
      (isCurrent ? ` class="is-current" aria-current="page"` : "") +
      `>${loc.short}</a>`
    );
  }).join("");

  if (variant === "footer") {
    return `<nav class="lang-switch lang-switch--footer" aria-label="${aria}">${links}</nav>`;
  }

  // Cabeçalho: os 4 links continuam de verdade no DOM (Google segue, e sem
  // JS eles ficam visíveis do jeito antigo, em linha). Com JS, viram um
  // dropdown abaixo do breakpoint do menu hambúrguer — ver .lang-switch__list
  // em components.css e o toggle em main.js.
  return (
    `<div class="lang-switch lang-switch--menu" data-lang-switch>` +
    `<button type="button" class="lang-switch__toggle" data-lang-toggle` +
    ` aria-haspopup="true" aria-expanded="false" aria-label="${aria}">` +
    `${current.short} <span aria-hidden="true">&#9662;</span></button>` +
    `<nav class="lang-switch__list" data-lang-list aria-label="${aria}">${links}</nav>` +
    `</div>`
  );
}

/**
 * Detecção por `navigator.language` — só na raiz e só antes da primeira
 * pintura, senão o visitante lê meia página em português e ela troca embaixo
 * dele. Escolha manual manda: gravada em `localStorage`, nunca mais redireciona.
 * `replace` em vez de `assign` para o botão voltar não cair de novo aqui.
 */
function detectScript() {
  const codes = LOCALES.filter((l) => l.code !== DEFAULT_LANG).map((l) => `${l.code}:1`).join(",");
  return (
    `<script>!function(){try{if(localStorage.getItem("omp-lang"))return;` +
    `var l=(navigator.language||"").slice(0,2).toLowerCase();` +
    `if({${codes}}[l])location.replace("/"+l+"/"+location.search+location.hash)}catch(e){}}();</script>`
  );
}

function headHtml(current, siteUrl) {
  const out = [`<meta property="og:locale" content="${current.ogLocale}" />`];
  if (siteUrl) {
    const abs = (code) => `${siteUrl}${pathFor(code)}`;
    out.push(`<link rel="canonical" href="${abs(current.code)}" />`);
    out.push(`<meta property="og:url" content="${abs(current.code)}" />`);
    for (const loc of LOCALES) {
      out.push(`<link rel="alternate" hreflang="${loc.htmlLang}" href="${abs(loc.code)}" />`);
    }
    out.push(`<link rel="alternate" hreflang="x-default" href="${abs(DEFAULT_LANG)}" />`);
  }
  if (current.code === DEFAULT_LANG) out.push(detectScript());
  return out.join("\n    ");
}

// ------------------------------------------------------------------ tradução

/**
 * Aplica um idioma ao HTML-fonte. Devolve `{ html, missing }` — chaves
 * faltando não param a tradução (o texto em português fica no lugar), quem
 * decide se isso é fatal é o chamador: em dev, aviso; na build, erro.
 */
export function translate(html, loc, catalogs, siteUrl = "") {
  const catalog = catalogs[loc.code] || {};
  const strings = catalog.html || {};
  const isDefault = loc.code === DEFAULT_LANG;
  const missing = [];

  const lookup = (key, original) => {
    if (Object.prototype.hasOwnProperty.call(strings, key)) return strings[key];
    // pt é o idioma-fonte: o texto do index.html já é o original, não falta nada
    if (!isDefault) missing.push(key);
    return original;
  };

  // 1. elementos e atributos marcados
  const openTag = /<([a-zA-Z][\w:-]*)((?:"[^"]*"|'[^']*'|[^>"'])*?)(\/?)>/g;
  let out = "";
  let pos = 0;
  let m;
  while ((m = openTag.exec(html))) {
    const [full, tag, attrs, selfClose] = m;
    const key = attrValue(attrs, "data-i18n");
    const attrSpec = attrValue(attrs, "data-i18n-attr");
    if (!key && !attrSpec) continue;

    out += html.slice(pos, m.index);

    let newAttrs = attrs;
    if (attrSpec) {
      for (const pair of attrSpec.split(",")) {
        const [attrName, attrKey] = pair.split(":").map((s) => s.trim());
        if (!attrName || !attrKey) continue;
        const original = attrValue(attrs, attrName) ?? "";
        newAttrs = setAttrValue(newAttrs, attrName, escapeAttr(lookup(attrKey, original)));
      }
    }
    newAttrs = stripI18nAttrs(newAttrs);

    const openEnd = m.index + full.length;
    if (!key) {
      out += `<${tag}${newAttrs}${selfClose}>`;
      pos = openEnd;
      continue;
    }

    if (VOID_TAGS.has(tag.toLowerCase())) {
      throw new Error(`[i18n] data-i18n="${key}" numa tag <${tag}> sem conteúdo — use data-i18n-attr`);
    }
    const closeAt = findClose(html, tag, openEnd);
    if (closeAt < 0) throw new Error(`[i18n] <${tag} data-i18n="${key}"> sem fechamento`);

    const original = html.slice(openEnd, closeAt);
    const value = lookup(key, original);
    // o texto traduzido não pode perder os ganchos que o JS procura
    for (const hook of dataHooks(original)) {
      if (!value.includes(hook)) {
        throw new Error(
          `[i18n] ${loc.code}: a tradução de "${key}" perdeu o gancho ${hook} — ` +
            `o JS não vai encontrar o elemento`
        );
      }
    }

    out += `<${tag}${newAttrs}>${value}`;
    pos = closeAt;
    openTag.lastIndex = closeAt;
  }
  out += html.slice(pos);

  // 2. idioma do documento + marcadores gerados
  out = out
    .replace(/<html\s+lang="[^"]*"/i, `<html lang="${loc.htmlLang}"`)
    .replace("<!--i18n:head-->", headHtml(loc, siteUrl))
    .replace("<!--i18n:langswitch-->", langSwitchHtml(loc, catalog, ""))
    .replace("<!--i18n:langswitch:footer-->", langSwitchHtml(loc, catalog, "footer"));

  // 3. comentário é nota para quem edita o index.html, não tem por que
  //    viajar quatro vezes até o navegador (e em português, na página it)
  out = out.replace(/\n?\s*<!--[\s\S]*?-->/g, "");

  // 4. strings de runtime — só as deste idioma
  const runtime = JSON.stringify({
    lang: loc.code,
    locale: loc.locale,
    js: catalog.js || {},
    works: catalog.works || {},
  }).replace(/</g, "\\u003c");
  out = out.replace(
    "</body>",
    `  <script type="application/json" data-i18n-runtime>${runtime}</script>\n  </body>`
  );

  return { html: out, missing };
}

// -------------------------------------------------------------------- plugin

export default function i18nPages({ siteUrl = "" } = {}) {
  let isDev = false;

  const report = (loc, missing, fatal) => {
    if (!missing.length) return;
    const list = [...new Set(missing)].join(", ");
    const msg = `[i18n] ${loc.code}: ${missing.length} chave(s) sem tradução — ${list}`;
    if (fatal) throw new Error(msg);
    console.warn(`\x1b[33m${msg}\x1b[0m`);
  };

  return {
    name: "omp:i18n-pages",
    enforce: "post",

    configResolved(config) {
      isDev = config.command === "serve";
    },

    // dev: a raiz sai traduzida para pt pelo hook normal do Vite; os outros
    // idiomas não existem em disco, então são servidos por middleware. Ele
    // precisa ser registrado aqui no corpo do hook (e não no retorno), senão
    // roda depois do fallback de SPA do Vite e `/en/` cai na página em pt.
    configureServer(server) {
      server.watcher.add(CATALOG_DIR);
      server.watcher.on("change", (file) => {
        if (file.startsWith(CATALOG_DIR)) (server.hot ?? server.ws).send({ type: "full-reload" });
      });

      server.middlewares.use(async (req, res, next) => {
        const url = (req.url || "").split("?")[0];
        const m = /^\/([a-z]{2})(\/|\/index\.html)?$/.exec(url);
        const loc = m && LOCALES.find((l) => l.code === m[1] && l.code !== DEFAULT_LANG);
        if (!loc) return next();
        if (!m[2]) {
          res.writeHead(301, { Location: `/${loc.code}/` });
          return res.end();
        }
        try {
          const source = fs.readFileSync(MAIN_HTML, "utf8");
          // `/<code>/index.html` faz o hook abaixo se abster: a tradução
          // deste request é a daqui, não a do pt
          const piped = await server.transformIndexHtml(
            `/${loc.code}/index.html`,
            source,
            req.originalUrl
          );
          const { html, missing } = translate(piped, loc, loadCatalogs(), siteUrl);
          report(loc, missing, false);
          res.setHeader("Content-Type", "text/html;charset=utf-8");
          res.end(html);
        } catch (err) {
          next(err);
        }
      });
    },

    transformIndexHtml: {
      order: "post",
      handler(html, ctx) {
        // na build o HTML sai cru (com os marcadores) e as quatro páginas são
        // escritas de uma vez em writeBundle — senão o pt já viria traduzido,
        // sem marcação para gerar os outros idiomas a partir dele
        if (!isDev || ctx.path !== "/index.html") return html;
        const loc = LOCALES.find((l) => l.code === DEFAULT_LANG);
        const { html: translated, missing } = translate(html, loc, loadCatalogs(), siteUrl);
        report(loc, missing, false);
        return translated;
      },
    },

    writeBundle(options) {
      const outDir = options.dir;
      const built = path.join(outDir, "index.html");
      if (!fs.existsSync(built)) return;
      const source = fs.readFileSync(built, "utf8");
      const catalogs = loadCatalogs();

      for (const loc of LOCALES) {
        const { html, missing } = translate(source, loc, catalogs, siteUrl);
        report(loc, missing, true);
        const dest =
          loc.code === DEFAULT_LANG
            ? built
            : path.join(outDir, loc.code, "index.html");
        fs.mkdirSync(path.dirname(dest), { recursive: true });
        fs.writeFileSync(dest, html);
      }

      const paths = LOCALES.map((l) => pathFor(l.code)).join("  ");
      console.log(`\x1b[32m[i18n]\x1b[0m ${LOCALES.length} idiomas: ${paths}`);
      if (!siteUrl) {
        console.warn(
          "\x1b[33m[i18n] SITE_URL vazio: saiu sem canonical/hreflang. " +
            "O Google só liga as versões com URL absoluta — preencha em src/config.js\x1b[0m"
        );
      }
    },
  };
}
