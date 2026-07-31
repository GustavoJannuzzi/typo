#!/usr/bin/env node
/**
 * O CLI.
 *
 *   node video/render.mjs roteiros/tour-9x16.mjs
 *   node video/render.mjs roteiros/processo-9x16.mjs --rascunho
 *   node video/render.mjs roteiros/tour-9x16.mjs --de 4 --ate 6
 *
 * As opcoes existem pra uma coisa so': encurtar a volta entre "mudei um
 * numero" e "vi o resultado". `--de/--ate` renderiza SO os planos daquele
 * intervalo — afinar o mergulho na obra vira 10 segundos em vez de 4 minutos.
 * Como cada frame e' funcao pura do roteiro, o pedaco renderizado sozinho e'
 * identico ao mesmo pedaco dentro do video inteiro.
 */
import { mkdir } from "node:fs/promises";
import { dirname, isAbsolute, join, resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { subir, RAIZ, distDesatualizado } from "./lib/servidor.mjs";
import { capturar } from "./lib/captura.mjs";
import { encodar, acharFfmpeg } from "./lib/encode.mjs";

const args = process.argv.slice(2);
if (!args[0] || args.includes("--ajuda") || args.includes("-h")) {
  console.log(`
uso: node video/render.mjs <roteiro.mjs> [opcoes]

  --rascunho        jpeg, 30 fps, sem supersample, crf 26 — pra julgar ritmo
  --de N --ate M    renderiza so' os planos N..M (0-based, inclusive)
  --fps N           sobrescreve o fps do roteiro
  --ssaa N          captura N vezes maior e reduz no ffmpeg (1 = desligado)
  --crf N           qualidade do H.264 (17 otimo, 23 padrao, 28 leve)
  --so-frames       captura e para (nao encoda)
  --so-encode       pula a captura e encoda os frames que ja estao no disco
  --porta N         porta do servidor local (default 4320)
  --saida caminho   arquivo mp4 de saida
`);
  process.exit(0);
}

const opt = (nome, alt) => {
  const i = args.indexOf(`--${nome}`);
  return i >= 0 && args[i + 1] && !args[i + 1].startsWith("--") ? args[i + 1] : alt;
};
const tem = (nome) => args.includes(`--${nome}`);

const caminhoRoteiro = isAbsolute(args[0]) ? args[0] : resolve(process.cwd(), args[0]);
const roteiro = (await import(pathToFileURL(caminhoRoteiro).href)).default;

// --- resolucao dos parametros: roteiro -> rascunho -> flags ---------------
const rascunho = tem("rascunho");
const fps = Number(opt("fps", rascunho ? 30 : roteiro.saida.fps));
const ssaa = Number(opt("ssaa", rascunho ? 1 : (roteiro.saida.ssaa ?? 1)));
const crf = Number(opt("crf", rascunho ? 26 : (roteiro.saida.crf ?? 17)));
const preset = rascunho ? "veryfast" : (roteiro.saida.preset ?? "slow");
// jpeg por padrao, e nao png. Medido nesta maquina, a 2160x3840: PNG custa
// ~1,9 s por frame (56 min pra um video de 30 s) porque a compressao sem perda
// de 8,3 MP e' cara. JPEG a 96 custa uma fracao disso, e a perda fica ABAIXO
// da quantizacao do proprio H.264 em crf 17 — some no encode. Use --png se
// quiser o intermediario sem perda mesmo assim.
const formato = tem("png") ? "png" : "jpeg";
const qualidade = Number(opt("q", rascunho ? 82 : 96));
const dePlano = Number(opt("de", 0));
const atePlano = Number(opt("ate", Infinity));

roteiro.saida.fps = fps;

const sufixo = [
  rascunho ? "rascunho" : null,
  Number.isFinite(atePlano) || dePlano > 0 ? `p${dePlano}-${Number.isFinite(atePlano) ? atePlano : "fim"}` : null,
].filter(Boolean).join("-");

const pastaSaida = join(RAIZ, "video", "out");
const pastaFrames = join(pastaSaida, "frames", roteiro.nome + (sufixo ? "-" + sufixo : ""));
const arquivo = opt("saida", join(pastaSaida, `${roteiro.nome}${sufixo ? "-" + sufixo : ""}.mp4`));
await mkdir(dirname(arquivo), { recursive: true });

console.log(`\n  roteiro   ${roteiro.nome}`);
console.log(`  saida     ${roteiro.saida.largura}x${roteiro.saida.altura} @ ${fps}fps` +
            `  ssaa ${ssaa}x  crf ${crf}${rascunho ? "  (RASCUNHO)" : ""}`);
console.log(`  planos    ${roteiro.planos.length}` +
            (dePlano > 0 || Number.isFinite(atePlano) ? `  (renderizando ${dePlano}..${Number.isFinite(atePlano) ? atePlano : roteiro.planos.length - 1})` : ""));

// so' o tour depende do build; a cena de processo le' o CSS do fonte
if (!roteiro.pagina.url.startsWith("/cena/")) {
  const aviso = await distDesatualizado();
  if (aviso) console.log(`\n  ATENCAO   ${aviso}`);
}

const { servidor, base } = await subir(Number(opt("porta", 4320)));

let total = 0;
let ext = formato === "jpeg" ? "jpg" : "png";
const t0 = Date.now();

try {
  if (!tem("so-encode")) {
    const r = await capturar(roteiro, base, {
      pastaFrames, formato, qualidade, ssaa, dePlano, atePlano,
      navegador: opt("navegador"),
      aoProgredir: (i, n, plano) => {
        const pct = ((i / n) * 100).toFixed(0).padStart(3);
        process.stdout.write(`\r  captura   ${pct}%  ${i}/${n}  ${plano.padEnd(24)}`);
      },
    });
    total = r.total;
    ext = r.ext;
    process.stdout.write("\n");
  }

  if (tem("so-frames")) {
    console.log(`\n  frames em ${pastaFrames}`);
  } else {
    const r = await encodar({
      pastaFrames, ext, fps, saida: arquivo,
      largura: roteiro.saida.largura, altura: roteiro.saida.altura,
      ssaa, crf, preset,
    });
    if (!r.ok) {
      console.log(`\n  ffmpeg nao instalado — os frames ficaram em:\n    ${pastaFrames}`);
      console.log(`\n  para encodar depois:\n    ${r.comando}\n`);
      console.log(`  ou instale:  npm --prefix video install\n`);
    } else {
      const seg = ((Date.now() - t0) / 1000).toFixed(1);
      console.log(`\n  pronto    ${arquivo}`);
      console.log(`            ${total} frames · ${(total / fps).toFixed(1)}s de video · ${seg}s de render\n`);
    }
  }
} finally {
  servidor.close();
}

if (!acharFfmpeg() && !tem("so-frames")) process.exitCode = 0;
