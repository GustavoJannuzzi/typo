/**
 * Cliente CDP minimo — fala direto com o Chrome que ja esta na maquina.
 *
 * Por que existe, se o Playwright faz isso: o Playwright pesa ~13 MB e traz um
 * modelo de execucao inteiro (contextos, auto-waiting, protocolo proprio) do
 * qual a captura frame a frame usa quatro comandos. O Node 22 ja tem
 * `WebSocket` global, e o Chrome 147 ja esta instalado. Entao o unico peso
 * novo do projeto vira o binario do ffmpeg.
 *
 * Os quatro comandos que a captura usa:
 *   Page.navigate            abre a pagina
 *   Runtime.evaluate         mede, prepara e move a camera
 *   Page.captureScreenshot   o frame (com optimizeForSpeed, que e' o que
 *                            torna PNG por frame viavel)
 *   Emulation.setDeviceMetricsOverride   viewport CSS + densidade de pixel
 *
 * Nada aqui espera relogio: a captura so avanca quando o comando anterior
 * respondeu. E' o que garante que rodar de novo sai igual.
 */
import { spawn } from "node:child_process";
import { existsSync, mkdtempSync } from "node:fs";
import { rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

const CANDIDATOS_WIN = [
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
  process.env.LOCALAPPDATA + "\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
  "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
];
const CANDIDATOS_MAC = [
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
];
const CANDIDATOS_LINUX = [
  "/usr/bin/google-chrome",
  "/usr/bin/chromium",
  "/usr/bin/chromium-browser",
  "/usr/bin/microsoft-edge",
];

export function acharNavegador(explicito) {
  if (explicito && existsSync(explicito)) return explicito;
  if (process.env.TYPO_CHROME && existsSync(process.env.TYPO_CHROME)) return process.env.TYPO_CHROME;
  const lista =
    process.platform === "win32" ? CANDIDATOS_WIN
    : process.platform === "darwin" ? CANDIDATOS_MAC
    : CANDIDATOS_LINUX;
  const achado = lista.find((p) => p && existsSync(p));
  if (!achado) {
    throw new Error(
      "Nao achei Chrome nem Edge. Passe o caminho em TYPO_CHROME=... ou --navegador."
    );
  }
  return achado;
}

/**
 * Sobe um Chrome headless isolado (perfil temporario, sem extensao, sem
 * restauracao de sessao) e devolve a URL do WebSocket de depuracao.
 */
export async function abrirNavegador({ navegador, escala = 1, largura = 1080, altura = 1920 } = {}) {
  const exe = acharNavegador(navegador);
  const perfil = mkdtempSync(join(tmpdir(), "typo-video-"));

  const args = [
    "--headless=new",
    "--remote-debugging-port=0",
    `--user-data-dir=${perfil}`,
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-extensions",
    "--disable-background-networking",
    "--disable-sync",
    "--mute-audio",
    "--hide-scrollbars",
    "--force-color-profile=srgb",
    // determinismo de raster: sem isso o compositor pode entregar um frame
    // com camada ainda nao rasterizada, e um frame do meio sai borrado
    "--run-all-compositor-stages-before-draw",
    "--disable-new-content-rendering-timeout",
    "--disable-lcd-text", // subpixel muda com o fundo; cinza e' estavel
    `--window-size=${Math.round(largura / escala)},${Math.round(altura / escala)}`,
    "about:blank",
  ];

  const proc = spawn(exe, args, { stdio: ["ignore", "pipe", "pipe"] });

  const ws = await new Promise((ok, erro) => {
    let buf = "";
    const prazo = setTimeout(() => erro(new Error("Chrome nao anunciou o DevTools em 20 s")), 20000);
    proc.stderr.on("data", (d) => {
      buf += d.toString();
      const m = buf.match(/ws:\/\/[^\s]+/);
      if (m) {
        clearTimeout(prazo);
        ok(m[0]);
      }
    });
    proc.on("exit", (c) => {
      clearTimeout(prazo);
      erro(new Error(`Chrome saiu antes de subir (codigo ${c})`));
    });
  });

  // Ctrl-C nao roda o `finally` da captura: sem isto, interromper um render
  // deixava o navegador inteiro rodando pra tras.
  const naMarra = () => {
    if (proc.exitCode !== null || proc.signalCode !== null) return;
    if (process.platform === "win32") {
      spawn("taskkill", ["/pid", String(proc.pid), "/f", "/t"], { stdio: "ignore" });
    } else {
      proc.kill("SIGKILL");
    }
  };
  process.once("SIGINT", () => { naMarra(); process.exit(130); });
  process.once("SIGTERM", () => { naMarra(); process.exit(143); });
  process.once("exit", naMarra);

  return { proc, ws, perfil, exe };
}

/** conexao CDP: envia comando, casa a resposta pelo id */
export class Sessao {
  constructor(socket) {
    this.socket = socket;
    this.id = 0;
    this.pendentes = new Map();
    this.ouvintes = new Map();
    socket.addEventListener("message", (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.id != null && this.pendentes.has(msg.id)) {
        const { ok, erro } = this.pendentes.get(msg.id);
        this.pendentes.delete(msg.id);
        msg.error ? erro(new Error(`${msg.error.message} (${JSON.stringify(msg.error.data ?? "")})`)) : ok(msg.result);
      } else if (msg.method) {
        (this.ouvintes.get(msg.method) || []).forEach((f) => f(msg.params));
      }
    });
  }

  static async conectar(wsUrl) {
    const socket = new WebSocket(wsUrl);
    await new Promise((ok, erro) => {
      socket.addEventListener("open", ok, { once: true });
      socket.addEventListener("error", () => erro(new Error("falha ao conectar no CDP")), { once: true });
    });
    return new Sessao(socket);
  }

  envia(method, params = {}, sessionId) {
    const id = ++this.id;
    return new Promise((ok, erro) => {
      this.pendentes.set(id, { ok, erro });
      this.socket.send(JSON.stringify(sessionId ? { id, method, params, sessionId } : { id, method, params }));
    });
  }

  quando(method, fn) {
    if (!this.ouvintes.has(method)) this.ouvintes.set(method, []);
    this.ouvintes.get(method).push(fn);
  }

  fecha() {
    try { this.socket.close(); } catch { /* ja fechado */ }
  }
}

/**
 * Abre uma aba, aplica as metricas e devolve um punhado de metodos com a
 * ergonomia que a captura precisa. `sessionId` de aba: tudo passa por ele.
 */
export async function abrirAba(sessao, { largura, altura, escala }) {
  const { targetId } = await sessao.envia("Target.createTarget", { url: "about:blank" });
  const { sessionId } = await sessao.envia("Target.attachToTarget", { targetId, flatten: true });
  const cmd = (m, p) => sessao.envia(m, p, sessionId);

  await cmd("Page.enable");
  await cmd("Runtime.enable");
  await cmd("Emulation.setDeviceMetricsOverride", {
    width: Math.round(largura),
    height: Math.round(altura),
    deviceScaleFactor: escala,
    mobile: false,
  });

  return {
    sessionId,
    cmd,

    async ir(url) {
      const carregou = new Promise((ok) => sessao.quando("Page.loadEventFired", ok));
      await cmd("Page.navigate", { url });
      await carregou;
    },

    /** avalia uma expressao (com await de promessa) e devolve o valor puro */
    async avaliar(expr, arg) {
      const fonte = typeof expr === "function" ? `(${expr})(${JSON.stringify(arg ?? null)})` : expr;
      const r = await cmd("Runtime.evaluate", {
        expression: fonte,
        awaitPromise: true,
        returnByValue: true,
      });
      if (r.exceptionDetails) {
        throw new Error("erro na pagina: " + (r.exceptionDetails.exception?.description || r.exceptionDetails.text));
      }
      return r.result.value;
    },

    /** espera uma condicao virar verdadeira na pagina — sem sleep cego */
    async esperar(exprBooleana, { tentativas = 400, intervalo = 25 } = {}) {
      for (let i = 0; i < tentativas; i++) {
        if (await this.avaliar(`Boolean(${exprBooleana})`)) return true;
        await new Promise((r) => setTimeout(r, intervalo));
      }
      throw new Error(`condicao nunca ficou verdadeira: ${exprBooleana}`);
    },

    /** um frame. `optimizeForSpeed` troca compressao por tempo — vale muito. */
    async frame({ formato = "png", qualidade = 92 } = {}) {
      const r = await cmd("Page.captureScreenshot", {
        format: formato,
        ...(formato === "jpeg" ? { quality: qualidade } : {}),
        optimizeForSpeed: formato === "png",
        captureBeyondViewport: false,
        fromSurface: true,
      });
      return Buffer.from(r.data, "base64");
    },
  };
}

/**
 * Encerra o navegador de verdade.
 *
 * `proc.kill()` sozinho NAO basta no Windows: o chrome.exe pai e' so' o
 * coordenador, e os processos de renderizacao/GPU sao filhos que sobrevivem —
 * cada rodada interrompida deixava oito processos e um punhado de GB pra
 * tras, e a maquina ia ficando lenta sem motivo aparente.
 *
 * A ordem e': `Browser.close` (desligamento limpo, o proprio Chrome derruba a
 * arvore), e so' se isso falhar, matar a arvore na marra.
 */
export async function encerrar({ proc, perfil }, sessao) {
  const morreu = new Promise((r) => proc.once("exit", r));

  try {
    await Promise.race([
      sessao?.envia("Browser.close"),
      new Promise((_, rej) => setTimeout(() => rej(new Error("timeout")), 3000)),
    ]);
    await Promise.race([morreu, new Promise((r) => setTimeout(r, 3000))]);
  } catch {
    /* cai no plano B */
  }
  sessao?.fecha();

  if (proc.exitCode === null && proc.signalCode === null) {
    if (process.platform === "win32") {
      // /T derruba a arvore inteira; /F sem cerimonia
      spawn("taskkill", ["/pid", String(proc.pid), "/f", "/t"], { stdio: "ignore" });
    } else {
      try { process.kill(-proc.pid, "SIGKILL"); } catch { proc.kill("SIGKILL"); }
    }
    await Promise.race([morreu, new Promise((r) => setTimeout(r, 2000))]);
  }

  await rm(perfil, { recursive: true, force: true }).catch(() => {});
}
