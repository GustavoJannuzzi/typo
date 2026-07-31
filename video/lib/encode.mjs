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
  // O scale entra SEMPRE, nao so' quando ha supersample. A densidade de pixel
  // sai de uma divisao (1080/430 = 2,5116...) e quase nunca fecha redonda: a
  // captura de 1080x1920 chegava com 1080x1919, e o libx264 em yuv420p recusa
  // altura impar. Forcar o tamanho aqui resolve os dois casos de uma vez —
  // e com lanczos, que e' o que da' antialias de verdade no texto quando a
  // captura foi maior que a saida.
  // setsar=1 porque o scale herda a razao de amostra da origem: sem ele o mp4
  // sai 1080x1920 com SAR 1920:1919 e o player exibe 1080x1919 de novo.
  const filtros = [`scale=${largura}:${altura}:flags=lanczos`, "setsar=1"];
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
