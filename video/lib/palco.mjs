/**
 * O palco: o codigo que roda DENTRO da pagina capturada.
 *
 * Ele e' injetado como string (a funcao vai stringificada pro
 * `Runtime.evaluate`), entao nao pode importar nada e nao pode fechar sobre
 * variaveis daqui. E' auto-contido de proposito.
 *
 * O que ele faz, e por que cada coisa importa pra captura:
 *
 *  - EMBRULHA o conteudo num `#__palco`. A camera transforma o palco, e a
 *    sobreposicao de texto fica FORA dele — senao o titulo escalaria junto com
 *    a arte, que e' exatamente o que nao se quer.
 *
 *  - MATA transicao e animacao de CSS. A pagina nao pode se mexer sozinha: se
 *    ela se mexer, dois frames capturados no mesmo estado de camera saem
 *    diferentes, e a reprodutibilidade morre.
 *
 *  - FORCA as imagens `loading="lazy"` a carregar. A camera nunca ROLA a
 *    pagina (todo o movimento e' transform), entao o navegador acha que segue
 *    no topo e as imagens de baixo nunca entrariam — buracos brancos no meio
 *    do video, so' que so' no export.
 *
 *  - NAO promove nada com `will-change`. Camada promovida e' rasterizada uma
 *    vez e escalada como textura: otimo pra animacao em tempo real, pessimo
 *    aqui. Sem promover, cada frame re-rasteriza no zoom em que esta, e um
 *    zoom de 5x sai NITIDO em vez de borrado. E' a vantagem de qualidade que
 *    a captura quadro a quadro ganha de brinde sobre gravar em tempo real.
 */

export function fontePalco() {
  return `(${preparar.toString()})`;
}

/* eslint-disable */
function preparar(opcoes) {
  const cfg = opcoes || {};
  const raiz = document.documentElement;

  // --- 1. congelar tudo que se mexe sozinho --------------------------------
  const estilo = document.createElement("style");
  estilo.textContent = `
    *, *::before, *::after {
      transition: none !important;
      animation: none !important;
      scroll-behavior: auto !important;
    }
    html, body { overflow: hidden !important; }
    ::-webkit-scrollbar { width: 0 !important; height: 0 !important; }
    #__palco { transform-origin: 0 0; }
    #__sobrepor {
      position: fixed; inset: 0; z-index: 2147483647; pointer-events: none;
      display: flex; padding: 6vmin; box-sizing: border-box;
    }
    #__sobrepor[data-pos="baixo"]  { align-items: flex-end;  justify-content: flex-start; }
    #__sobrepor[data-pos="alto"]   { align-items: flex-start; justify-content: flex-start; }
    #__sobrepor[data-pos="centro"] { align-items: center;     justify-content: center; text-align: center; }
    #__sobrepor .__caixa { max-width: 88%; }
    /* fundo do rotulo — o roteiro escolhe em titulo.fundo:
       "placa"  etiqueta de especime em papel (legivel sobre qualquer arte)
       "brilho" so' um halo de papel atras do texto (mais leve, menos seguro)
       "nenhum" tinta crua                                                */
    #__sobrepor[data-fundo="placa"] .__caixa {
      background: var(--paper, #fff);
      border-top: 1px solid var(--ink, #111);
      padding: 0.65em 0.85em 0.75em;
    }
    #__sobrepor[data-fundo="brilho"] .__sub,
    #__sobrepor[data-fundo="brilho"] .__titulo {
      text-shadow: 0 0 14px var(--paper, #fff), 0 0 34px var(--paper, #fff),
                   0 0 60px var(--paper, #fff);
    }
    #__sobrepor .__sub { margin: 0 0 0.4em; color: var(--grey, #696969); }
    #__sobrepor .__titulo {
      margin: 0; line-height: 0.92; text-transform: uppercase;
      font-size: clamp(2rem, 9vmin, 7rem); color: var(--ink, #111);
    }
    #__sobrepor .__titulo .__p { display: inline-block; white-space: nowrap; }
    #__sobrepor .__titulo .__p > span { display: inline-block; }
  `;
  document.head.appendChild(estilo);

  // --- 2. embrulhar o conteudo no palco -----------------------------------
  let palco = document.getElementById("__palco");
  if (!palco) {
    palco = document.createElement("div");
    palco.id = "__palco";
    while (document.body.firstChild) palco.appendChild(document.body.firstChild);
    document.body.appendChild(palco);
  }
  // O palco tem transform SEMPRE, mesmo parado na identidade. Um elemento com
  // transform vira bloco de contencao pra `position: fixed` dos filhos; sem
  // transform, nao vira. Se a identidade virasse `none`, todo elemento fixed
  // (o modal da galeria, o cabecalho) pularia de lugar entre um plano e o
  // seguinte — e a medida de um plano nao valeria pro outro.
  palco.style.transform = "translate(0px,0px) scale(1)";

  const sobrepor = document.createElement("div");
  sobrepor.id = "__sobrepor";
  sobrepor.dataset.pos = "baixo";
  sobrepor.innerHTML =
    '<div class="__caixa"><p class="label __sub"></p><p class="display __titulo"></p></div>';
  document.body.appendChild(sobrepor);
  const elSub = sobrepor.querySelector(".__sub");
  const elTitulo = sobrepor.querySelector(".__titulo");

  // --- 3. matar o que a pagina anima em JS ---------------------------------
  // a intro cobre a tela ate' alguem clicar; o hero desenha em rAF
  document.querySelectorAll("[data-intro]").forEach((n) => n.remove());
  try { window.cancelAnimationFrame && window.__heroRaf && cancelAnimationFrame(window.__heroRaf); } catch (e) {}

  // --- 4. carregar o que so' carregaria rolando ----------------------------
  const prontas = [];
  document.querySelectorAll("img").forEach((img) => {
    img.loading = "eager";
    if (img.decode) prontas.push(img.decode().catch(function () {}));
  });

  const ruido = function (i, s) {
    const x = Math.sin(i * 127.1 + s * 311.7) * 43758.5453;
    return x - Math.floor(x);
  };

  let cam = null; // camera aplicada agora — medir() precisa dela pra inverter

  window.__typo = {
    /**
     * Rect de cada seletor no espaco do PALCO (que e' o do documento).
     *
     * Mede com a camera APLICADA e inverte a matriz, em vez de zerar o
     * transform e medir. Zerar parece mais simples e esta' errado: sem
     * transform o palco deixa de ser bloco de contencao, e todo elemento
     * `position: fixed` la' dentro pula de volta pra viewport. O overlay da
     * galeria e' fixed — medido assim ele devolvia um retangulo la' no topo
     * da pagina, e a camera mergulhava no hero em vez de na obra.
     *
     * screen = doc*z + t   =>   doc = (screen - t)/z
     */
    medir: function (seletores) {
      const z = cam ? cam.z : 1;
      const tx = cam ? window.innerWidth / 2 - cam.x * cam.z : 0;
      const ty = cam ? window.innerHeight / 2 - cam.y * cam.z : 0;
      const saida = {};
      (seletores || []).forEach(function (sel) {
        const n = document.querySelector(sel);
        if (!n) return;
        const r = n.getBoundingClientRect();
        saida[sel] = {
          x: (r.left + window.scrollX - tx) / z,
          y: (r.top + window.scrollY - ty) / z,
          w: r.width / z,
          h: r.height / z,
        };
      });
      saida.__documento = {
        x: 0, y: 0,
        w: document.documentElement.scrollWidth,
        h: document.documentElement.scrollHeight,
      };
      return saida;
    },

    /** coloca o ponto (x,y) do documento no centro da viewport, com zoom z */
    camera: function (x, y, z) {
      if (x == null) return;
      cam = { x: x, y: y, z: z };
      const tx = window.innerWidth / 2 - x * z;
      const ty = window.innerHeight / 2 - y * z;
      palco.style.transform =
        "translate(" + tx.toFixed(3) + "px," + ty.toFixed(3) + "px) scale(" + z.toFixed(6) + ")";
    },

    /** o texto por cima, montando letra a letra por PROGRESSO (nunca por relogio) */
    titulo: function (t) {
      if (!t || !t.progresso) {
        sobrepor.style.opacity = "0";
        return;
      }
      sobrepor.style.opacity = "1";
      sobrepor.dataset.pos = t.posicao || "baixo";
      sobrepor.dataset.fundo = t.fundo || "placa";
      if (elTitulo.dataset.txt !== t.texto) {
        elTitulo.dataset.txt = t.texto;
        // agrupa por PALAVRA: com cada letra num inline-block solto, a quebra
        // de linha cai em qualquer lugar e "de perto" vira "de p" / "erto"
        elTitulo.innerHTML = String(t.texto)
          .split(" ")
          .map(function (palavra) {
            return (
              '<span class="__p">' +
              palavra.split("").map(function (c) { return "<span>" + c + "</span>"; }).join("") +
              "</span>"
            );
          })
          .join('<span class="__p"><span>&nbsp;</span></span>');
      }
      elSub.textContent = t.sub || "";
      elSub.style.opacity = String(Math.max(0, (t.progresso - 0.3) / 0.7));

      const spans = elTitulo.querySelectorAll(".__p > span");
      const n = spans.length;
      for (let i = 0; i < n; i++) {
        const inicio = 0.45 * (n <= 1 ? 0 : i / (n - 1));
        let p = (t.progresso - inicio) / 0.55;
        p = p < 0 ? 0 : p > 1 ? 1 : p;
        p = p * p * (3 - 2 * p);
        const dx = (ruido(i, 3) * 2 - 1) * 30 * (1 - p);
        const dy = (ruido(i, 7) * 2 - 1) * 26 * (1 - p);
        const rot = (ruido(i, 11) * 2 - 1) * 20 * (1 - p);
        spans[i].style.opacity = p.toFixed(3);
        spans[i].style.transform =
          "translate(" + dx.toFixed(2) + "px," + dy.toFixed(2) + "px) rotate(" + rot.toFixed(2) + "deg)";
      }
    },

    /**
     * Acoes nomeadas — o roteiro chama pelo nome, nunca escreve JS.
     * Adicionar um gesto novo ao vocabulario e' acrescentar uma entrada aqui.
     */
    acoes: {
      abrirObra: function (slug) {
        const cartao = document.querySelector('.gallery-card[data-slug="' + slug + '"]');
        if (cartao) cartao.click();
      },
      fecharObra: function () {
        const b = document.querySelector("[data-gallery-close]");
        if (b) b.click();
      },
      verDePerto: function () {
        const b = document.querySelector("[data-gallery-toggle]");
        if (b) b.click();
      },
      comparar: function (pct) {
        const r = document.querySelector("[data-compare-range]");
        if (!r) return;
        r.value = String(pct);
        r.dispatchEvent(new Event("input", { bubbles: true }));
      },
      abrirMenu: function () {
        const b = document.querySelector("[data-nav-toggle]");
        if (b) b.click();
      },
    },

    faz: function (nome, args) {
      const f = window.__typo.acoes[nome];
      if (!f) throw new Error("acao desconhecida no roteiro: " + nome);
      f.apply(null, args || []);
      // a acao pode ter revelado imagem nova (o overlay da galeria troca o src)
      const pend = [];
      document.querySelectorAll("img").forEach(function (img) {
        img.loading = "eager";
        if (img.decode) pend.push(img.decode().catch(function () {}));
      });
      return Promise.all(pend).then(function () { return true; });
    },
  };

  window.scrollTo(0, 0);
  sobrepor.style.opacity = "0";

  return Promise.all([document.fonts ? document.fonts.ready : null].concat(prontas)).then(function () {
    raiz.dataset.palcoPronto = "1";
    return true;
  });
}
