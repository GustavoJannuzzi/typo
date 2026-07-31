/**
 * Frames -> mp4, via ffmpeg.
 *
 * Por que ffmpeg e nao o proprio Chrome: o Chrome tem WebCodecs, mas o
 * `VideoEncoder` headless SEM GPU nao oferece H.264 (medido: avc1=false,
 * vp8/vp9=true). Sairia .webm, e o entregavel e' pra Instagram/WhatsApp, que
 * querem mp4. Entao o binario do ffmpeg e' a unica dependencia real do
 * pipeline — e fica dentro de video/node_modules, sem tocar no PATH.
 *
 * Se o ffmpeg nao estiver instalado, isto NAO quebra: os frames ficam no
 * disco e a funcao devolve o comando exato pra rodar depois.
 */
import { spawn } from "node:child_process";
import { createRequire } from "node:module";
import { existsSync } from "node:fs";
import { join } from "node:path";

const require = createRequire(import.meta.url);

export function acharFfmpeg() {
  if (process.env.TYPO_FFMPEG && existsSync(process.env.TYPO_FFMPEG)) return process.env.TYPO_FFMPEG;
  try {
    return require("@ffmpeg-installer/ffmpeg").path;
  } catch {
    return null; // nao instalado — o chamador decide o que fazer
  }
}

export function montarArgumentos({ pastaFrames, ext, fps, saida, largura, altura, ssaa, crf, preset }) {
  const filtros = [];
  if (ssaa > 1) {
    // reduzir com lanczos DEPOIS de capturar grande e' o que da' antialias de
    // verdade no texto — melhor do que qualquer suavizacao do navegador
    filtros.push(`scale=${largura}:${altura}:flags=lanczos`);
  }
  // yuv420p e' o unico pix_fmt que todo player entende; sem ele, o video abre
  // no VLC e nao abre no celular
  filtros.push("format=yuv420p");

  return [
    "-y",
    "-framerate", String(fps),
    "-start_number", "0",
    "-i", join(pastaFrames, `%06d.${ext}`),
    "-vf", filtros.join(","),
    "-c:v", "libx264",
    "-preset", preset,
    "-crf", String(crf),
    "-movflags", "+faststart",
    "-r", String(fps),
    "-an",
    saida,
  ];
}

export async function encodar(opcoes) {
  const bin = acharFfmpeg();
  const args = montarArgumentos(opcoes);
  const comando = `"${bin || "ffmpeg"}" ${args.map((a) => (a.includes(" ") ? `"${a}"` : a)).join(" ")}`;

  if (!bin) return { ok: false, motivo: "ffmpeg-ausente", comando };

  return new Promise((resolver, rejeitar) => {
    const p = spawn(bin, args, { stdio: ["ignore", "ignore", "pipe"] });
    let erro = "";
    p.stderr.on("data", (d) => (erro += d.toString()));
    p.on("error", rejeitar);
    p.on("close", (codigo) =>
      codigo === 0
        ? resolver({ ok: true, comando })
        : rejeitar(new Error(`ffmpeg saiu com ${codigo}:\n${erro.slice(-2000)}`))
    );
  });
}
