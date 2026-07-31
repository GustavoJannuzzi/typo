/**
 * A camera: transforma a lista de planos do roteiro numa lista de frames, cada
 * um com o estado exato (x, y, zoom, sobreposicao) que a pagina deve mostrar.
 *
 * Duas decisoes que valem a explicacao:
 *
 * 1. ZOOM INTERPOLA EM LOG. Ir de 1x a 6x linearmente parece que acelera no
 *    fim: o que o olho le como "velocidade de aproximacao" e' a taxa
 *    RELATIVA de mudanca, nao a absoluta. Interpolando log(z), 1->2 leva o
 *    mesmo tempo que 2->4, que e' o que a percepcao espera. Da' pra desligar
 *    com `zoomLinear: true` num plano especifico.
 *
 * 2. O PONTO DE FOCO ANDA EM COORDENADAS DE DOCUMENTO, nao de tela. O plano
 *    diz "o rosto da obra X" e a camera resolve onde isso esta na pagina
 *    inteira. Mudar a altura da viewport nao estraga o enquadramento.
 *
 * A pagina nao rola: `window.scrollTo` fica em 0 e TODO o movimento vertical
 * e' a translacao do palco. Um sistema de coordenadas so' — sem somar scroll
 * com transform e sem descobrir, no frame 800, que os dois brigaram.
 */
import { resolverEase } from "./easing.mjs";

/** resolve um alvo do roteiro em { x, y, z } no espaco do documento */
export function resolverAlvo(alvo, medidas, vp) {
  const t = alvo || {};
  const r = t.alvo
    ? medidas[t.alvo] || (() => { throw new Error(`seletor nao encontrado na pagina: ${t.alvo}`); })()
    : { x: 0, y: 0, w: vp.largura, h: vp.altura };

  const fx = r.x + r.w * (t.foco?.[0] ?? 0.5);
  const fy = r.y + r.h * (t.foco?.[1] ?? 0.5);

  let z;
  if (typeof t.zoom === "number") {
    z = t.zoom;
  } else {
    const m = 1 - 2 * (t.margem ?? 0.06);
    const porLargura = (vp.largura * m) / r.w;
    const porAltura = (vp.altura * m) / r.h;
    z =
      t.zoom === "largura" ? porLargura
      : t.zoom === "altura" ? porAltura
      : Math.min(porLargura, porAltura); // "conter" (default)
  }

  return {
    x: fx + (t.desloca?.[0] ?? 0),
    y: fy + (t.desloca?.[1] ?? 0),
    z,
  };
}

const misturar = (a, b, t) => a + (b - a) * t;

export function interpolar(de, para, t, { zoomLinear = false } = {}) {
  return {
    x: misturar(de.x, para.x, t),
    y: misturar(de.y, para.y, t),
    z: zoomLinear
      ? misturar(de.z, para.z, t)
      : Math.exp(misturar(Math.log(de.z), Math.log(para.z), t)),
  };
}

/** os seletores que um plano cita — o que precisa ser medido antes dele rodar */
export function seletoresDoPlano(plano) {
  return [plano.de?.alvo, plano.para?.alvo].filter(Boolean);
}

/**
 * Expande um plano nos seus frames. O plano NAO resolve a camera aqui: quem
 * resolve e' o laco de captura, no instante em que o plano comeca.
 *
 * Isso nao e' preciosismo. Um plano de acao pode REVELAR um elemento (o
 * overlay da galeria abre com `hidden`), e medir tudo de uma vez no comeco
 * daria retangulo zerado justamente pro alvo mais importante do video. Medir
 * na hora e' a unica forma de a camera enxergar o que a acao anterior criou.
 */
export function montarFramesDoPlano(plano, iPlano, fps) {
  const dur = plano.dur ?? 1;
  const n = Math.max(1, Math.round(dur * fps));
  const ease = resolverEase(plano.ease);
  const tipo = plano.tipo || (plano.ato ? "cena" : "camera");
  const frames = [];

  for (let i = 0; i < n; i++) {
    // (i+1)/n e nao i/n: o ultimo frame do plano chega EXATAMENTE no destino,
    // senao cada corte perde um frame e a emenda de dois planos treme
    const bruto = n === 1 ? 1 : (i + 1) / n;
    const t = ease(bruto);

    const frame = {
      plano: iPlano,
      nomePlano: plano.nome || `${tipo}-${iPlano}`,
      tipo,
      u: bruto,
      tEase: t,
    };

    if (tipo === "cena") frame.cena = { ato: plano.ato, u: t };
    if (tipo === "acao" && i === 0) frame.acao = { faz: plano.faz, args: plano.args ?? [] };

    // sobreposicao de texto: vale pra qualquer tipo de plano, entra e sai
    // dentro da duracao do proprio plano
    if (plano.titulo) {
      const entra = plano.titulo.entra ?? 0.18;
      const sai = plano.titulo.sai ?? 0.18;
      const dentro = Math.min(1, bruto / Math.max(1e-6, entra));
      const fora = 1 - Math.max(0, (bruto - (1 - sai)) / Math.max(1e-6, sai));
      frame.titulo = {
        texto: plano.titulo.texto ?? "",
        sub: plano.titulo.sub ?? "",
        posicao: plano.titulo.posicao ?? "baixo",
        fundo: plano.titulo.fundo ?? "placa",
        progresso: Math.max(0, Math.min(dentro, fora)),
      };
    }

    frames.push(frame);
  }

  return { tipo, frames };
}
