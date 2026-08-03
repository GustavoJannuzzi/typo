/**
 * Servidor estatico minimo (zero dependencias) que junta, numa origem so, as
 * quatro coisas que o video precisa enxergar:
 *
 *   /            -> site/dist        (o build de producao, NAO o dev server)
 *   /cena/       -> video/cena       (a cena do processo de criacao)
 *   /dados/*     -> metadados        (works.json + o que da pra ler do project.yaml)
 *   /refs/<slug> -> projects/<slug>/refs/<primeira imagem>
 *   /texto/<slug>-> projects/<slug>/text/<primeiro .txt>
 *
 * Por que o build e nao o `vite dev`: o dev server injeta HMR, faz transform
 * sob demanda e responde em tempo variavel. Nada disso e determinístico. O
 * `dist/` e um monte de arquivo parado — sempre igual, sempre na mesma ordem.
 */
import { createServer } from "node:http";
import { readFile, readdir, stat } from "node:fs/promises";
import { existsSync } from "node:fs";
import { extname, join, normalize, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const AQUI = fileURLToPath(new URL(".", import.meta.url));
export const RAIZ = resolve(AQUI, "..", "..");
const DIST = join(RAIZ, "site", "dist");
const CENA = join(RAIZ, "video", "cena");
const PROJETOS = join(RAIZ, "projects");

const MIME = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".mjs": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".txt": "text/plain; charset=utf-8",
  ".svg": "image/svg+xml",
  ".webp": "image/webp",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".woff2": "font/woff2",
};

/**
 * Le do project.yaml so o punhado de campos que a cena precisa. NAO e um
 * parser de YAML — e leitura de quatro linhas com formato conhecido. Um
 * parser de verdade seria uma dependencia nova por causa de quatro campos.
 */
function lerProjeto(yaml) {
  const um = (re) => (yaml.match(re) || [])[1];
  const crop = um(/^\s*crop:\s*\[([^\]]+)\]/m);
  const semAspas = (v) => (v ? v.replace(/^["']|["']$/g, "") : null);
  return {
    image: um(/^\s*image:\s*(.+?)\s*(?:#.*)?$/m) || null,
    crop: crop ? crop.split(",").map((n) => Number(n.trim())) : null,
    textFile: um(/^\s*file:\s*(.+?)\s*(?:#.*)?$/m) || null,
    fonte: um(/^\s*family:\s*(.+?)\s*(?:#.*)?$/m) || null,
    accent: um(/^\s*color:\s*"?(#[0-9a-fA-F]{6})"?/m) || null,
    // titulo e subtitulo pro caso da obra nao estar em works.json — que e' o
    // do `magalenha`: o works.json e' gerado pelo build_site_assets.py, que
    // precisa da imagem de referencia, e a dele se perdeu. O project.yaml
    // continua sendo a fonte da verdade dos textos.
    title: semAspas(um(/^\s*title:\s*(.+?)\s*(?:#.*)?$/m)),
    subtitle: semAspas(um(/^\s*subtitle:\s*(.+?)\s*(?:#.*)?$/m)),
  };
}

async function primeiroArquivo(dir, exts) {
  if (!existsSync(dir)) return null;
  const nomes = (await readdir(dir)).filter((n) => exts.includes(extname(n).toLowerCase()));
  nomes.sort();
  return nomes[0] ? join(dir, nomes[0]) : null;
}

async function dadosProjetos() {
  const slugs = (await readdir(PROJETOS, { withFileTypes: true }))
    .filter((d) => d.isDirectory())
    .map((d) => d.name);
  const saida = {};
  for (const slug of slugs) {
    const yamlPath = join(PROJETOS, slug, "project.yaml");
    if (!existsSync(yamlPath)) continue;
    saida[slug] = lerProjeto(await readFile(yamlPath, "utf8"));
  }
  return saida;
}

/** impede que `..` no caminho escape da pasta servida */
function seguro(base, pedido) {
  const alvo = join(base, normalize(pedido).replace(/^(\.\.[\\/])+/, ""));
  return alvo.startsWith(base) ? alvo : null;
}

async function servirArquivo(res, caminho) {
  try {
    const s = await stat(caminho);
    if (s.isDirectory()) return servirArquivo(res, join(caminho, "index.html"));
    const buf = await readFile(caminho);
    res.writeHead(200, {
      "Content-Type": MIME[extname(caminho).toLowerCase()] || "application/octet-stream",
      "Content-Length": buf.length,
      "Cache-Control": "no-store",
    });
    res.end(buf);
    return true;
  } catch {
    res.writeHead(404, { "Content-Type": "text/plain" });
    res.end("404 " + caminho);
    return false;
  }
}

export function criarServidor() {
  return createServer(async (req, res) => {
    const url = new URL(req.url, "http://localhost");
    const p = decodeURIComponent(url.pathname);

    if (p === "/dados/works.json") {
      return servirArquivo(res, join(RAIZ, "site", "src", "data", "works.json"));
    }
    if (p === "/dados/projetos.json") {
      const json = JSON.stringify(await dadosProjetos());
      res.writeHead(200, { "Content-Type": MIME[".json"], "Cache-Control": "no-store" });
      return res.end(json);
    }
    if (p.startsWith("/refs/")) {
      const slug = p.slice("/refs/".length).replace(/\/$/, "");
      const proj = join(PROJETOS, slug, "refs");
      const arq = await primeiroArquivo(proj, [".png", ".jpg", ".jpeg", ".webp"]);
      return arq ? servirArquivo(res, arq) : servirArquivo(res, "inexistente");
    }
    if (p.startsWith("/texto/")) {
      const slug = p.slice("/texto/".length).replace(/\/$/, "");
      const arq = await primeiroArquivo(join(PROJETOS, slug, "text"), [".txt"]);
      return arq ? servirArquivo(res, arq) : servirArquivo(res, "inexistente");
    }
    if (p.startsWith("/cena/")) {
      const alvo = seguro(CENA, p.slice("/cena/".length) || "index.html");
      return alvo ? servirArquivo(res, alvo) : res.end();
    }

    // A cena carrega o CSS da identidade direto do FONTE (`/src/styles/*.css`),
    // nao do bundle: sao arquivos CSS planos, nao precisam de build, e assim a
    // cena continua valendo mesmo com o `dist/` vazio ou velho. Idem para os
    // assets de `public/`, que o Vite so' copia.
    for (const [prefixo, base] of [
      ["/src/", join(RAIZ, "site", "src")],
      ["/art/", join(RAIZ, "site", "public", "art")],
      ["/fonts/", join(RAIZ, "site", "public", "fonts")],
      // os recortes de `scripts/build_instagram.py`. O `-detail.webp` do site
      // tem 1100 px e amolece antes de 3x; as avulsas sao recortes 1:1 do
      // export de 150 dpi, entao um mergulho de verdade cabe sem carregar o
      // PNG de 27 MP inteiro no navegador.
      ["/social/", join(RAIZ, "social")],
    ]) {
      if (p.startsWith(prefixo)) {
        const alvo = seguro(base, p.slice(prefixo.length));
        return alvo ? servirArquivo(res, alvo) : res.end();
      }
    }

    const alvo = seguro(DIST, p === "/" ? "index.html" : p);
    return alvo ? servirArquivo(res, alvo) : res.end();
  });
}

/**
 * O tour renderiza o `dist/`, nao o fonte. Se alguem mexeu em site/src e nao
 * refez o build, o video sai do site ANTIGO — e isso e' invisivel ate' alguem
 * reparar num detalhe que "ja tinha sido corrigido". Melhor avisar.
 */
export async function distDesatualizado() {
  const distIndex = join(RAIZ, "site", "dist", "index.html");
  if (!existsSync(distIndex)) return "sem build: rode `npm --prefix site run build`";
  const tDist = (await stat(distIndex)).mtimeMs;

  let maisNovo = 0;
  const varrer = async (dir) => {
    if (!existsSync(dir)) return;
    for (const e of await readdir(dir, { withFileTypes: true })) {
      const p = join(dir, e.name);
      if (e.isDirectory()) await varrer(p);
      else maisNovo = Math.max(maisNovo, (await stat(p)).mtimeMs);
    }
  };
  await varrer(join(RAIZ, "site", "src"));
  const idx = join(RAIZ, "site", "index.html");
  if (existsSync(idx)) maisNovo = Math.max(maisNovo, (await stat(idx)).mtimeMs);

  return maisNovo > tDist
    ? "site/dist esta mais velho que site/src — rode `npm --prefix site run build`"
    : null;
}

export function subir(porta = 4319) {
  return new Promise((ok) => {
    const s = criarServidor();
    s.listen(porta, "127.0.0.1", () => ok({ servidor: s, base: `http://127.0.0.1:${porta}` }));
  });
}

const executadoDireto =
  process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href;

if (executadoDireto) {
  const porta = Number(process.argv[2] || 4319);
  const { base } = await subir(porta);
  console.log(`servindo em ${base}`);
  console.log(`  /            -> site/dist`);
  console.log(`  /cena/processo.html -> a cena de processo`);
}
