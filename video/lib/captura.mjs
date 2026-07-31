/**
 * A captura: abre a pagina, prepara o palco, e anda frame a frame.
 *
 * O laco e' sincrono de proposito. Para cada frame:
 *   1. manda o estado (camera, sobreposicao, ato da cena) pra pagina
 *   2. ESPERA a pagina confirmar que aplicou
 *   3. so' entao pede o screenshot
 *
 * Nao ha `sleep`, nao ha "espera 16ms e torce". Se a maquina estiver lenta, o
 * video demora mais pra sair — mas sai IGUAL. E' toda a tese do metodo: o
 * tempo do video e' o `fps` do roteiro, nao o relogio da maquina.
 */
import { mkdir, rm, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { abrirNavegador, abrirAba, encerrar, Sessao } from "./cdp.mjs";
import { fontePalco } from "./palco.mjs";
import { interpolar, montarFramesDoPlano, resolverAlvo, seletoresDoPlano } from "./camera.mjs";

export async function capturar(roteiro, base, opcoes = {}) {
  const {
    pastaFrames,
    formato = "png",
    qualidade = 92,
    ssaa = 1,
    dePlano = 0,
    atePlano = Infinity,
    aoProgredir = () => {},
  } = opcoes;

  const vp = { largura: roteiro.pagina.largura, altura: roteiro.pagina.altura };
  // a densidade de pixel sai da conta entre o tamanho de SAIDA e o tamanho de
  // LAYOUT: o roteiro pede "renderiza como um celular de 430 px" e "entrega
  // 1080 px de largura", e o resto e' aritmetica. Com ssaa > 1 captura maior
  // e o ffmpeg reduz — texto com antialias de verdade, sem serrilha.
  const escala = (roteiro.saida.largura * ssaa) / vp.largura;

  const nav = await abrirNavegador({
    escala,
    largura: vp.largura * escala,
    altura: vp.altura * escala,
    navegador: opcoes.navegador,
  });
  const sessao = await Sessao.conectar(nav.ws);
  const aba = await abrirAba(sessao, { largura: vp.largura, altura: vp.altura, escala });

  try {
    await aba.ir(base + roteiro.pagina.url);
    await aba.esperar(`document.readyState === "complete"`);

    if (roteiro.pagina.esperar) await aba.esperar(roteiro.pagina.esperar);

    await aba.avaliar(`${fontePalco()}(${JSON.stringify(roteiro.pagina.palco ?? {})})`);
    await aba.esperar(`document.documentElement.dataset.palcoPronto === "1"`);

    await rm(pastaFrames, { recursive: true, force: true });
    await mkdir(pastaFrames, { recursive: true });

    const ext = formato === "jpeg" ? "jpg" : "png";
    const aRodar = roteiro.planos
      .map((plano, i) => ({ plano, i }))
      .filter(({ i }) => i >= dePlano && i <= atePlano);
    if (!aRodar.length) throw new Error("nenhum plano no intervalo pedido");

    // total previsto so' para a barra de progresso
    const previsto = aRodar.reduce(
      (s, { plano }) => s + Math.max(1, Math.round((plano.dur ?? 1) * roteiro.saida.fps)), 0
    );

    // Os planos de ACAO anteriores ao recorte rodam mesmo assim, sem capturar.
    // Sem isso `--de 6 --ate 6` renderizaria o mergulho com o modal da galeria
    // ainda fechado — e o recorte serve justamente pra afinar UM plano, entao
    // ele tem que ver a pagina no estado em que aquele plano de fato acontece.
    for (const plano of roteiro.planos.slice(0, dePlano)) {
      if ((plano.tipo || (plano.ato ? "cena" : "camera")) !== "acao") continue;
      await aba.avaliar(`window.__typo.faz(${JSON.stringify(plano.faz)}, ${JSON.stringify(plano.args ?? [])})`);
    }

    let camera = null;
    let i = 0;

    for (const { plano, i: iPlano } of aRodar) {
      const { tipo, frames } = montarFramesDoPlano(plano, iPlano, roteiro.saida.fps);

      // 1. a ACAO primeiro: ela pode revelar o alvo que a camera vai medir
      if (tipo === "acao") {
        await aba.avaliar(`window.__typo.faz(${JSON.stringify(plano.faz)}, ${JSON.stringify(plano.args ?? [])})`);
      }

      // 2. so' agora mede, com a pagina no estado em que o plano de fato roda
      let de = camera;
      let para = camera;
      if (tipo === "camera" || tipo === "corte") {
        const medidas = await aba.avaliar(
          `window.__typo.medir(${JSON.stringify(seletoresDoPlano(plano))})`
        );
        para = resolverAlvo(plano.para ?? plano.de, medidas, vp);
        de = plano.de ? resolverAlvo(plano.de, medidas, vp) : (camera ?? para);
        if (tipo === "corte") de = para;
      }

      for (const f of frames) {
        const cam =
          tipo === "camera" ? interpolar(de, para, f.tEase, { zoomLinear: plano.zoomLinear })
          : tipo === "corte" ? para
          : camera;

        // as tres mudancas de estado vao numa chamada so'. Cada ida ao CDP tem
        // latencia propria, e sao milhares de frames — tres viagens viram uma.
        const passos = [];
        if (f.cena) passos.push(`window.__cena.seek(${JSON.stringify(f.cena.ato)},${f.cena.u})`);
        if (cam) passos.push(`window.__typo.camera(${cam.x},${cam.y},${cam.z})`);
        passos.push(`window.__typo.titulo(${JSON.stringify(f.titulo ?? null)})`);
        await aba.avaliar(passos.join(";"));

        const buf = await aba.frame({ formato, qualidade });
        await writeFile(join(pastaFrames, `${String(i).padStart(6, "0")}.${ext}`), buf);
        i++;
        if (i % 15 === 0 || i === previsto) aoProgredir(i, previsto, f.nomePlano);
      }

      if (tipo === "camera" || tipo === "corte") camera = para;
    }

    return { total: i, ext };
  } finally {
    await encerrar(nav, sessao);
  }
}
