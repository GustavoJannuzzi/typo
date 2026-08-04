/**
 * Uma pagina de certificado por selo emitido — geradas na build, igual a
 * `/en/`, `/es/`, `/it/` e `/admin/`. Mesma tecnica de `build/i18n.js` (regex
 * de tag + `findClose` respeitando aninhamento), adaptada: em vez de trocar
 * IDIOMA, troca DADOS DA OBRA por selo, a partir de
 * `src/data/seals.json` (o registro: codigo -> obra, dono, edicao — escrito
 * por `scripts/make_seal.py`) e `src/data/certificates.json` (carta + contagem
 * + imagens por obra — escrito por `scripts/build_certificates.py`).
 *
 * Vocabulario dos marcadores, no espirito do `data-i18n`:
 *
 *   data-cert="chave"        troca o TEXTO do elemento (escapado)
 *   data-cert-html="chave"   troca o HTML INTERNO do elemento (ja vem pronto
 *                            do Python — carta e as linhas do ranking)
 *   data-cert-attr="attr:chave"  troca um atributo (os `src` das imagens)
 *   data-cert-if="chave"     mantem o elemento so' se `chave` for verdadeiro
 *                            no view model; "!chave" inverte. Remove o
 *                            elemento INTEIRO (nao so' o `hidden`) quando
 *                            falso — texto que nunca deveria aparecer nao
 *                            deve nem existir no HTML publicado.
 *   <!--cert:head-->         <title> + <meta og:*> especificos do selo
 *
 * FALHA ALTA, DE PROPOSITO. Selo em seals.json sem entrada em
 * certificates.json (obra sem certificado.md — ver build_certificates.py)
 * ou `<TAG data-cert-if="x">` sem fechamento correspondente aborta a build
 * inteira. Um selo ja' impresso aponta pra uma URL que precisa existir: uma
 * pagina de certificado publicada pela metade e' pior que build vermelha.
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const SITE_ROOT = path.resolve(HERE, "..");
const DATA_DIR = path.join(SITE_ROOT, "src", "data");
const TEMPLATE_HTML = path.join(SITE_ROOT, "certificado", "index.html");

// --------------------------------------------------------------------- io --

function readJson(file, fallback) {
  if (!fs.existsSync(file)) return fallback;
  const raw = fs.readFileSync(file, "utf8").trim();
  return raw ? JSON.parse(raw) : fallback;
}

function loadData() {
  const seals = readJson(path.join(DATA_DIR, "seals.json"), []);
  const certificates = readJson(path.join(DATA_DIR, "certificates.json"), {});
  return { seals, certificates };
}

// -------------------------------------------------------------- formatting --

function fmt(n) {
  return typeof n === "number" ? n.toLocaleString("pt-BR") : "";
}

function fmtDate(iso) {
  if (!iso) return "";
  return new Date(`${iso}T00:00:00`).toLocaleDateString("pt-BR", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

function escapeHtml(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function escapeAttr(s) {
  return String(s).replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;");
}

// ------------------------------------------------------------- view model --

/** Selo + certificado da obra -> os valores que os marcadores da pagina leem. */
function viewModelFor(seal, cert) {
  const contagem = cert.contagem;
  const art = cert.art;
  return {
    title: cert.title,
    subtitle: cert.subtitle,
    carta: cert.carta,

    contagem: Boolean(contagem),
    "heroi-vezes": contagem ? fmt(contagem.heroi.vezes) : "",
    "heroi-palavra": contagem ? contagem.heroi.palavra : "",
    "ranking-rows": contagem
      ? contagem.ranking
          .map((r) => `<tr><td>${escapeHtml(r.palavra)}</td><td>${fmt(r.vezes)}&times;</td></tr>`)
          .join("")
      : "",
    palavras: contagem ? fmt(contagem.palavras) : "",
    letras: contagem ? fmt(contagem.letras) : "",

    art: Boolean(art),
    "art-full": art ? art.full : "",
    "art-detail": art ? art.detail : "",

    code: seal.code,
    edition: seal.edition ? `${seal.edition.n}/${seal.edition.total}` : "",
    owner: seal.owner || "",
    "issued-on": fmtDate(seal.issuedOn),
  };
}

function headHtml(seal, cert, siteUrl) {
  const title = `${cert.title} — Certificado · Onde Moram as Palavras`;
  const desc = `Selo ${seal.code} · ficha de autenticidade de "${cert.title}".`;
  const out = [
    `<title>${escapeHtml(title)}</title>`,
    `<meta name="description" content="${escapeAttr(desc)}" />`,
    `<meta property="og:title" content="${escapeAttr(title)}" />`,
    `<meta property="og:description" content="${escapeAttr(desc)}" />`,
  ];
  if (siteUrl) {
    out.push(`<meta property="og:url" content="${siteUrl}/certificado/${seal.code}/" />`);
    if (cert.art) out.push(`<meta property="og:image" content="${siteUrl}${cert.art.full}" />`);
  }
  return out.join("\n    ");
}

// ------------------------------------------------------------ html helpers --
// (attrValue/setAttrValue/findClose replicam build/i18n.js — mesmo problema,
// mesma solucao; nao vale abstrair um modulo compartilhado por 3 funcoes)

function attrValue(attrs, name) {
  const m = new RegExp(`\\s${name}="([^"]*)"`).exec(attrs);
  return m ? m[1] : null;
}

function setAttrValue(attrs, name, value) {
  const re = new RegExp(`(\\s${name}=")[^"]*(")`);
  if (re.test(attrs)) return attrs.replace(re, `$1${value}$2`);
  const trailing = /\s*\/$/.exec(attrs);
  if (trailing) return `${attrs.slice(0, trailing.index)} ${name}="${value}"${trailing[0]}`;
  return `${attrs} ${name}="${value}"`;
}

function stripCertAttrs(attrs) {
  return attrs.replace(/\s*\bdata-cert(?:-html|-attr|-if)?="[^"]*"/g, "").replace(/\s*\bhidden\b(?!=)/g, "");
}

/** Indice do `</tag>` que fecha a abertura em `from`, respeitando aninhamento. */
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

// ---------------------------------------------------------------- render --

/** Aplica o view model ao HTML do template. Uma unica passada pelas tags. */
export function renderCertificate(html, view, { seal, cert } = {}) {
  const openTag = /<([a-zA-Z][\w:-]*)((?:"[^"]*"|'[^']*'|[^>"'])*?)(\/?)>/g;
  let out = "";
  let pos = 0;
  let m;

  while ((m = openTag.exec(html))) {
    const [full, tag, attrs, selfClose] = m;
    const ifKey = attrValue(attrs, "data-cert-if");
    const textKey = attrValue(attrs, "data-cert");
    const htmlKey = attrValue(attrs, "data-cert-html");
    const attrSpec = attrValue(attrs, "data-cert-attr");
    if (!ifKey && !textKey && !htmlKey && !attrSpec) continue;

    out += html.slice(pos, m.index);
    const openEnd = m.index + full.length;

    if (ifKey) {
      const negate = ifKey.startsWith("!");
      const key = negate ? ifKey.slice(1) : ifKey;
      if (!(key in view)) {
        throw new Error(`[cert] data-cert-if="${ifKey}" referencia chave inexistente no view model`);
      }
      const keep = negate ? !view[key] : Boolean(view[key]);
      const closeAt = findClose(html, tag, openEnd);
      if (closeAt < 0) throw new Error(`[cert] <${tag} data-cert-if="${ifKey}"> sem fechamento`);
      const closeMatch = /^<\/[a-zA-Z][\w:-]*\s*>/.exec(html.slice(closeAt));
      const closeLen = closeMatch ? closeMatch[0].length : 0;
      if (!keep) {
        pos = closeAt + closeLen; // remove o elemento inteiro, nao so' o `hidden`
      } else {
        out += `<${tag}${stripCertAttrs(attrs)}${selfClose}>`;
        pos = openEnd;
      }
      openTag.lastIndex = pos;
      continue;
    }

    let newAttrs = attrs;
    if (attrSpec) {
      const [attrName, key] = attrSpec.split(":").map((s) => s.trim());
      if (!(key in view)) {
        throw new Error(`[cert] data-cert-attr="${attrSpec}" referencia chave inexistente`);
      }
      newAttrs = setAttrValue(newAttrs, attrName, escapeAttr(view[key]));
    }
    newAttrs = stripCertAttrs(newAttrs);

    if (!textKey && !htmlKey) {
      out += `<${tag}${newAttrs}${selfClose}>`;
      pos = openEnd;
      openTag.lastIndex = pos;
      continue;
    }

    const key = textKey || htmlKey;
    if (!(key in view)) throw new Error(`[cert] data-cert${textKey ? "" : "-html"}="${key}" referencia chave inexistente`);
    const closeAt = findClose(html, tag, openEnd);
    if (closeAt < 0) throw new Error(`[cert] <${tag} data-cert="${key}"> sem fechamento`);
    const value = textKey ? escapeHtml(view[key]) : String(view[key]);

    out += `<${tag}${newAttrs}${selfClose}>${value}`;
    pos = closeAt;
    openTag.lastIndex = closeAt;
  }
  out += html.slice(pos);

  if (seal && cert) out = out.replace("<!--cert:head-->", headHtml(seal, cert, ""));
  return out;
}

function renderWithHead(html, seal, cert, siteUrl) {
  const view = viewModelFor(seal, cert);
  const applied = renderCertificate(html, view);
  return applied.replace("<!--cert:head-->", headHtml(seal, cert, siteUrl));
}

// -------------------------------------------------------------------- plugin --

export default function certificatePages({ siteUrl = "" } = {}) {
  return {
    name: "omp:certificate-pages",
    enforce: "post",

    // dev: /certificado/<CODE>/ nao existe em disco — middleware serve o
    // template processado na hora, sempre lendo os JSON de novo (sem cache),
    // pra `make_seal.py`/`build_certificates.py` rodados durante o `npm run
    // dev` aparecerem sem reiniciar o servidor.
    configureServer(server) {
      server.watcher.add(DATA_DIR);
      server.watcher.on("change", (file) => {
        if (file.startsWith(DATA_DIR)) (server.hot ?? server.ws).send({ type: "full-reload" });
      });

      server.middlewares.use(async (req, res, next) => {
        const url = (req.url || "").split("?")[0];
        const m = /^\/certificado\/([0-9A-Z]{4,8})\/?(?:index\.html)?$/i.exec(url);
        if (!m) return next();

        const code = m[1].toUpperCase();
        const { seals, certificates } = loadData();
        const seal = seals.find((s) => s.code === code);
        if (!seal) {
          res.statusCode = 404;
          res.end(`selo ${code} não encontrado em src/data/seals.json`);
          return;
        }
        const cert = certificates[seal.work];
        if (!cert) {
          res.statusCode = 500;
          res.end(`obra "${seal.work}" sem entrada em certificates.json — rode build_certificates.py`);
          return;
        }

        try {
          const source = fs.readFileSync(TEMPLATE_HTML, "utf8");
          const piped = await server.transformIndexHtml(url, source, req.originalUrl);
          res.setHeader("Content-Type", "text/html;charset=utf-8");
          res.end(renderWithHead(piped, seal, cert, siteUrl));
        } catch (err) {
          next(err);
        }
      });
    },

    writeBundle(options) {
      const outDir = options.dir;
      const builtTemplate = path.join(outDir, "certificado", "index.html");
      if (!fs.existsSync(builtTemplate)) return; // certificado/index.html nao esta' no rollupOptions.input

      const source = fs.readFileSync(builtTemplate, "utf8");
      const { seals, certificates } = loadData();

      if (!seals.length) {
        fs.rmSync(builtTemplate, { force: true });
        console.log("\x1b[33m[cert]\x1b[0m nenhum selo em src/data/seals.json — nada a gerar");
        return;
      }

      const missing = [...new Set(seals.filter((s) => !certificates[s.work]).map((s) => s.work))];
      if (missing.length) {
        throw new Error(
          `[cert] selo emitido para obra sem certificates.json: ${missing.join(", ")} — ` +
            "rode scripts/build_certificates.py antes do build (uma URL impressa nao pode cair em 404)"
        );
      }

      for (const seal of seals) {
        const cert = certificates[seal.work];
        const html = renderWithHead(source, seal, cert, siteUrl);
        const dest = path.join(outDir, "certificado", seal.code, "index.html");
        fs.mkdirSync(path.dirname(dest), { recursive: true });
        fs.writeFileSync(dest, html);
      }

      // o template cru (com "TÍTULO DA OBRA" etc.) nunca deve ficar acessivel
      fs.rmSync(builtTemplate, { force: true });

      console.log(`\x1b[32m[cert]\x1b[0m ${seals.length} certificado(s): ${seals.map((s) => `/certificado/${s.code}/`).join("  ")}`);
      if (!siteUrl) {
        console.warn(
          "\x1b[33m[cert] SITE_URL vazio: og:image/og:url saem sem URL absoluta " +
            "(o preview de link no WhatsApp nao funciona sem isso)\x1b[0m"
        );
      }
    },
  };
}
