/**
 * Chapa: tira N fotos paradas de um roteiro sem gerar video nenhum.
 *
 *   node video/lib/chapa.mjs cena --obra ouro-marrom
 *   node video/lib/chapa.mjs cena --cena obra --obra emicida
 *   node video/lib/chapa.mjs site
 *
 * `--cena` escolhe qual cena de video/cena/ abrir (sem o `.html`). Vale pra
 * qualquer uma que cumpra o contrato `__cena.atos` / `__cena.seek(ato, u)`.
 *
 * Serve pra duas coisas:
 *   1. afinar a cena sem esperar um encode inteiro;
 *   2. deixar o resultado visivel pra quem NAO consegue assistir ao video —
 *      um frame parado eu consigo olhar, um mp4 nao.
 */
import { mkdir, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { subir, RAIZ } from "./servidor.mjs";
import { abrirNavegador, abrirAba, encerrar, Sessao } from "./cdp.mjs";

const args = process.argv.slice(2);
const alvo = args[0] || "cena";
const opt = (nome, alt) => {
  const i = args.indexOf(`--${nome}`);
  return i >= 0 ? args[i + 1] : alt;
};

const obra = opt("obra", "ouro-marrom");
const cena = opt("cena", "processo");
const largura = Number(opt("largura", 430));
const altura = Number(opt("altura", 764));
const escala = Number(opt("escala", 2));
const destino = opt("saida", join(RAIZ, "video", "out", "chapas"));

const { servidor, base } = await subir(Number(opt("porta", 4321)));
await mkdir(destino, { recursive: true });

const nav = await abrirNavegador({ escala, largura: largura * escala, altura: altura * escala });
const sessao = await Sessao.conectar(nav.ws);
const aba = await abrirAba(sessao, { largura, altura, escala });

try {
  if (alvo === "cena") {
    await aba.ir(`${base}/cena/${cena}.html?obra=${obra}`);
    await aba.esperar(`document.documentElement.dataset.cenaPronta === "1"`);
    const atos = await aba.avaliar(`window.__cena.atos`);
    for (const ato of atos) {
      for (const u of [0.55, 1]) {
        await aba.avaliar(`window.__cena.seek(${JSON.stringify(ato)}, ${u})`);
        const png = await aba.frame();
        const nome = `${cena}-${obra}-${String(atos.indexOf(ato) + 1).padStart(2, "0")}-${ato}-u${String(u).replace(".", "")}.png`;
        await writeFile(join(destino, nome), png);
        console.log("  ", nome, `${(png.length / 1024).toFixed(0)} KB`);
      }
    }
  } else {
    await aba.ir(`${base}/`);
    await aba.esperar(`document.readyState === "complete"`);
    const png = await aba.frame();
    await writeFile(join(destino, "site-topo.png"), png);
    console.log("  site-topo.png");
  }
  console.log(`\nchapas em ${destino}`);
} finally {
  await encerrar(nav, sessao);
  servidor.close();
}
