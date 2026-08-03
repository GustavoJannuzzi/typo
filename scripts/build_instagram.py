#!/usr/bin/env python3
"""Carrossel de Instagram a partir do PNG já exportado — sem re-render.

    python scripts/build_instagram.py ouro-marrom
    python scripts/build_instagram.py ouro-marrom --formatos feed,story --debug

Escreve, prontos pra postar na ordem do nome do arquivo:

    social/<slug>/feed/01..04.png   o carrossel de quatro cartas
    social/<slug>/story/story.png   o story, numa carta só
    social/<slug>/avulsas/*.png     material solto, pra montar à mão

O **story é uma carta só** porque lá não existe passar o dedo pra próxima: o
mergulho que o carrossel faz em quatro tempos ele faz de uma vez, com o macro
sangrando no fundo e a peça inteira numa placa de papel por cima. `--story
carrossel` volta pras mesmas quatro cartas do feed.

As **avulsas** não são cartas: são o título em PNG com alfa e N recortes 1:1 da
malha, sem placa, sem etiqueta e sem moldura. É matéria-prima pra montagem à
mão, não peça fechada. `--avulsas 0` desliga.

O motor **não roda aqui**. A única coisa que este script lê do `typo` é
metadado (título, corpo da fonte, tamanho da página) e a geometria de onde a
arte pura mora dentro da página exportada — a mesma conta que o
`build_site_assets.py` já faz. Pixel nenhum é redesenhado.

## O problema

De longe, no feed, a arte parece um retrato comum: a malha de letras só
aparece a partir de umas poucas dezenas de centímetros. O carrossel resolve
isso com narrativa em vez de filtro — quatro cartas que vão de longe pra
perto:

    01  a peça inteira, com o título
    02  a malha começando a virar letra   (2,6× mais perto)
    03  o macro, onde se lê a palavra     (1:1, pixel do export)
    04  a ficha de espécime

O zoom é **encaixado**: o macro é escolhido primeiro e o corte intermediário é
centrado no mesmo ponto. Passar o dedo de uma carta pra outra vira um mergulho
contínuo no mesmo lugar da peça, não três recortes avulsos.

## Onde cortar o macro — o critério

O jeito óbvio é procurar a região mais escura (é o que o `build_site_assets.py`
faz pro recorte do site). Está errado pro macro, e erra dos dois lados: no
escuro extremo os glifos grandes se encostam e viram uma mancha preta; no claro
extremo sobra papel. Nenhum dos dois deixa ler uma palavra.

O que se lê é outra coisa: **traço grosso o suficiente pra resolver, com o
branco entre as letras ainda aberto**. Isso é medível sem saber nada do texto:

- `t_tinta` — espessura média do traço. Erode a máscara de tinta em degraus e
  conta em quantos degraus cada pixel sobrevive. Letra grande sobrevive muito;
  letra de 1,5 mm morre no primeiro.
- `t_branco` — a mesma conta no negativo: a folga entre as letras.

E o critério é `min(t_tinta, t_branco)`, que rejeita os dois extremos de uma
vez só, sem precisar de limiar de cobertura:

    mancha preta chapada   t_tinta alto,  t_branco ~0   -> min baixo
    papel quase vazio      t_tinta ~0,    t_branco alto -> min baixo
    palavra legível        os dois médios/altos         -> min alto

Foi calibrado contra os recortes que já existem em `site/public/art`: o de
`garota-de-ipanema` tem 11% de cobertura e é o mais legível de todos, enquanto
o de `debret-antropofagia` tem 45% e é o mais fechado. Qualquer critério que
fosse "mais escuro é melhor" ou "cobertura perto de X" premiaria o segundo.

A cobertura entra só como desempate suave (uma gaussiana larga em volta de
`COBERTURA_IDEAL`), pra não escolher um canto com três letras enormes e o resto
branco quando existe uma opção igualmente nítida e mais cheia.

O custo é O(1) por janela candidata: os mapas de espessura são reduzidos por
blocos e a média por janela sai de um `uniform_filter` — o mesmo truque de soma
acumulada que o `image_prep.Field` usa no motor. Rodar em 37 MP leva poucos
segundos.

`--debug` escreve o mapa do critério e as janelas escolhidas por cima da arte,
em `social/<slug>/debug/`. É o jeito de conferir a escolha em vez de acreditar.

## O título por cima da arte — como não virar selo de banco de imagem

O que denuncia o selo genérico é sempre a mesma coisa: um véu preto
semitransparente, ou um degradê, e o texto centralizado por cima. É o gesto de
quem precisa esconder a imagem pra conseguir escrever nela.

A identidade daqui já resolveu isso de outro jeito, e a regra está no próprio
pôster: **na ficha de espécime nada se cruza**. Título, arte e rodapé têm cada
um a sua faixa. Então:

1. **Nenhuma opacidade, nunca.** Nem véu, nem degradê, nem sombra. Se precisar
   de fundo, é papel chapado com corte reto — que é a margem do pôster, um
   gesto editorial, não um filtro.
2. **O título procura o silêncio da própria arte.** Estas peças têm papel de
   sobra em volta da figura (a máscara recorta a figura e o resto fica branco).
   O script varre a arte atrás da faixa mais vazia e assenta o título ali, em
   tinta sólida sobre o branco que já existia. Sem véu porque não precisa —
   "a arte de fundo aguenta o texto" vira uma medida, não uma esperança.
3. **Só quando não há silêncio** (`COBERTURA_TITULO` de teto) entra a placa de
   papel de corte reto, encostada na borda de baixo.
4. **O vocabulário é o do site, não um genérico.** Archivo 800 na largura
   condensada de 68%, etiqueta em JetBrains Mono com 0,14em de entreletra, o
   quadradinho de destaque na frente da etiqueta, os quatro quadradinhos do
   rodapé do pôster como assinatura. Tudo lido de `base.css` em runtime.

O resultado é o oposto do selo: o texto não está *sobre* a arte, está *dentro*
da composição — no lugar que a arte deixou vago.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import uniform_filter

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import social_kit as kit  # noqa: E402

Image.MAX_IMAGE_PIXELS = None

ROOT = kit.ROOT
OUT_ROOT = ROOT / "social"
WORKS_JSON = ROOT / "site" / "src" / "data" / "works.json"

# --- critério do macro -----------------------------------------------------

#: um pixel conta como tinta abaixo deste valor de luminância
LUM_TINTA = 168
#: quantos degraus de erosão medir. Traço mais grosso que isso satura — não
#: faz diferença pro que estamos decidindo.
DEGRAUS = 6
#: redução por blocos antes de varrer as janelas. 8 px de passo é mais fino
#: que qualquer diferença visível no enquadramento.
BLOCO = 8
#: desempate suave: cobertura de tinta confortável numa janela de macro
COBERTURA_IDEAL = 0.28
COBERTURA_LARGURA = 0.24
#: margem morta em volta da arte, em fração do lado — evita cortar na moldura
MARGEM_BORDA = 0.04

# --- escalas do mergulho ---------------------------------------------------

#: quanto o corte intermediário é mais largo que o macro. O macro é 1:1 com o
#: pixel do export (é o mais nítido que existe sem re-render); 2,6× é o ponto
#: em que a malha ainda mostra que é feita de letra sem já ser legível.
ZOOM_MEIO = 2.6

#: teto de cobertura de tinta pra uma faixa ser considerada "silêncio" e
#: receber o título direto sobre a arte
COBERTURA_TITULO = 0.045
#: tolerância pra considerar duas faixas igualmente silenciosas
EMPATE_FAIXA = 0.02


@dataclass(frozen=True)
class Obra:
    """Tudo que as peças precisam saber sobre a arte — nada além de metadado."""
    slug: str
    art: Image.Image
    dpi: float
    titulo: str
    subtitulo: str
    rodape: str
    fonte: str
    corpo_mm: float
    pagina_cm: tuple[float, float]
    glifos: int | None
    camadas: list[str]
    versos: list[str]
    degradado: bool  # True = veio do webp do site, não do export de 150 dpi

    @property
    def cm_por_px(self) -> float:
        return 2.54 / self.dpi


def num(v: float, casas: int = 0) -> str:
    """Número em pt-BR: vírgula decimal, ponto de milhar."""
    return f"{v:,.{casas}f}".replace(",", "\x00").replace(".", ",").replace("\x00", ".")


# --------------------------------------------------------------------------
# carregar a arte
# --------------------------------------------------------------------------

def _bbox_sem_referencia(cfg, dpi: float) -> tuple[int, int, int, int] | None:
    """O bbox da arte quando a imagem de referência sumiu.

    O `art_bbox_px` abre a referência por um motivo só: saber o tamanho do
    crop. E quando `source.crop` é explícito — que é o caso de todo projeto que
    recorta — esse tamanho é a diferença das próprias coordenadas. Então a
    geometria inteira da página sai do `project.yaml`, sem a foto.

    É o que devolve o `magalenha` à fila: a referência dele se perdeu (ver
    "Estado" no CLAUDE.md), o motor não roda mais, mas o PNG exportado existe —
    e as peças de divulgação são pós-processamento do PNG, não do motor.

    Sem crop explícito devolve `None`: aí o tamanho vem mesmo da imagem, e
    chutar daria um recorte errado sem avisar.
    """
    crop = cfg.source.crop
    if not crop:
        return None
    from typo.config import Scale

    art_w, art_h = cfg.art_size(crop[2] - crop[0], crop[3] - crop[1], dpi)
    pw, _ph = cfg.page_size(art_w, art_h, dpi)
    ox = (pw - art_w) // 2
    oy = int(Scale(dpi).cm(cfg.page.margin_top_cm))
    return ox, oy, ox + art_w, oy + art_h


def _works_meta(slug: str) -> dict:
    if not WORKS_JSON.exists():
        return {}
    for entry in json.loads(WORKS_JSON.read_text(encoding="utf-8")):
        if entry.get("slug") == slug:
            return entry
    return {}


def carregar(slug: str) -> Obra:
    """Abre o export de 150 dpi e recorta a arte pura (sem título/moldura).

    Se o export não existir, cai no `-full.webp` do site — que dá pra montar as
    cartas 01 e 04, mas **não** dá macro de verdade (1600 px no lado maior é
    menos que uma carta do Instagram). O aviso é explícito; não existe modo
    silencioso que entrega um macro borrado como se fosse o certo.
    """
    from typo.project import load_project

    project = load_project(slug)
    cfg = project.config()
    meta = _works_meta(slug)
    dpi = float(cfg.page.dpi_export)

    pngs = sorted((ROOT / "projects" / slug / "output").glob("*150dpi.png"))
    degradado = False
    if pngs:
        with Image.open(pngs[0]) as raw:
            page = raw.convert("RGB")
        try:
            from build_site_assets import art_bbox_px

            art = page.copy() if cfg.display.enabled else page.crop(art_bbox_px(cfg, dpi))
        except Exception as exc:  # imagem de referência sumiu, etc.
            bbox = None if cfg.display.enabled else _bbox_sem_referencia(cfg, dpi)
            if bbox:
                print(f"  ! sem a imagem de referência; bbox da arte derivado do "
                      f"source.crop do project.yaml")
                art = page.crop(bbox)
            else:
                print(f"  ! não deu pra localizar a arte dentro da página ({exc});"
                      " usando a página inteira")
                art = page
    else:
        webp = ROOT / "site" / "public" / "art" / f"{slug}-full.webp"
        if not webp.exists():
            raise SystemExit(
                f"não achei export de 150 dpi em projects/{slug}/output/ nem "
                f"{webp.relative_to(ROOT)}.\n"
                f"Rode primeiro:  python scripts/render.py {slug}"
            )
        with Image.open(webp) as raw:
            art = raw.convert("RGB")
        degradado = True
        print(f"  ! sem export de 150 dpi — caindo em {webp.name} ({art.width}px).\n"
              f"    As cartas 01 e 04 saem certas; o macro sai BORRADO.\n"
              f"    Pra valer:  python scripts/render.py {slug}")

    if degradado:
        # o webp do site é a arte REDUZIDA. Manter os 150 dpi aqui faria a
        # etiqueta do macro anunciar um recorte de 18 cm que na verdade é de
        # 90 — número errado é pior que número ausente.
        real_px = (meta.get("px") or [0])[0]
        if real_px:
            dpi = dpi * art.width / real_px
        else:
            print("  ! sem 'px' em works.json: as medidas em cm vão sair erradas")

    if meta.get("widthCm") and meta.get("heightCm"):
        pagina_cm = (float(meta["widthCm"]), float(meta["heightCm"]))
    else:
        # a página é maior que a arte (margens + título + rodapé) — é o
        # tamanho que a pessoa recebe impresso, então é o que a ficha diz
        pagina_cm = cfg.page_cm(art.width, art.height, dpi)

    return Obra(
        slug=slug,
        art=art,
        dpi=dpi,
        titulo=cfg.text_blocks.title or slug.replace("-", " ").upper(),
        subtitulo=cfg.text_blocks.subtitle or "",
        rodape=cfg.text_blocks.footer or "",
        fonte=cfg.font.family,
        corpo_mm=round(cfg.font.base_line_mm, 1),
        pagina_cm=pagina_cm,
        glifos=meta.get("glyphs"),
        camadas=meta.get("layers") or _camadas(cfg),
        versos=_versos(cfg),
        degradado=degradado,
    )


def _versos(cfg, limite: int = 8) -> list[str]:
    """As primeiras frases do texto que virou a imagem.

    A ficha ganha muito com elas: é o que separa "arte feita de letras" de
    "arte feita DESTA letra". `#` é comentário no formato do projeto.
    """
    caminho = Path(getattr(cfg.text, "text_path", "") or "")
    if not caminho.is_absolute():
        caminho = ROOT / caminho
    if not caminho.exists():
        return []
    out = []
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if linha and not linha.startswith("#"):
            out.append(linha)
            if len(out) >= limite:
                break
    return out


def _camadas(cfg) -> list[str]:
    out = ["máscara" if cfg.mask.enabled else "halftone puro"]
    if cfg.landscape.enabled:
        out.append("paisagem")
    if cfg.accent.enabled:
        out.append("accent")
    if cfg.palette.enabled:
        out.append("paleta")
    return out


# --------------------------------------------------------------------------
# o critério: espessura do traço x folga do branco
# --------------------------------------------------------------------------

def _reduz(a: np.ndarray, r: int) -> np.ndarray:
    h, w = (a.shape[0] // r) * r, (a.shape[1] // r) * r
    return a[:h, :w].reshape(h // r, r, w // r, r).mean(axis=(1, 3))


def _espessura(mascara: np.ndarray, degraus: int, r: int) -> np.ndarray:
    """Mapa reduzido de "em quantos degraus de erosão o pixel sobrevive".

    Erosão por quadrado de lado `2k+1` é `uniform_filter(...) == 1`: separável,
    O(N) por degrau, e evita montar a transformada de distância inteira em
    float64 (que em 37 MP passa de 300 MB).
    """
    f = mascara.astype(np.float32)
    acc = np.zeros(((mascara.shape[0] // r), (mascara.shape[1] // r)), dtype=np.float32)
    for k in range(1, degraus + 1):
        sobrevive = uniform_filter(f, size=2 * k + 1, mode="constant", cval=0.0) > 1 - 1e-4
        acc += _reduz(sobrevive, r)
        del sobrevive
    return acc


@dataclass
class Criterio:
    """Os campos que decidem o recorte, todos na grade reduzida."""
    legibilidade: np.ndarray  # min(t_tinta, t_branco) por pixel reduzido
    cobertura: np.ndarray
    bloco: int


def medir(art: Image.Image, bloco: int = BLOCO, degraus: int = DEGRAUS) -> Criterio:
    lum = np.asarray(art.convert("L"))
    tinta = lum < LUM_TINTA
    del lum
    esp_tinta = _espessura(tinta, degraus, bloco)
    esp_branco = _espessura(~tinta, degraus, bloco)
    cobertura = _reduz(tinta.astype(np.float32), bloco)
    del tinta
    # `esp_*` já é a soma dos degraus por bloco; dividir pela fração de área
    # correspondente devolve a espessura média *entre os pixels daquele tipo*
    eps = 1e-3
    t_tinta = esp_tinta / np.maximum(cobertura, eps)
    t_branco = esp_branco / np.maximum(1.0 - cobertura, eps)
    return Criterio(np.minimum(t_tinta, t_branco), cobertura, bloco)


def _bump(v: np.ndarray, ideal: float, largura: float) -> np.ndarray:
    return np.exp(-(((v - ideal) / largura) ** 2))


def _campo_de_score(crit: Criterio, art_size: tuple[int, int],
                    win_w: int, win_h: int) -> np.ndarray:
    """O score de cada posição de janela, na grade reduzida.

    É a legibilidade média da janela, temperada pela gaussiana larga de
    cobertura. Fora da região válida (janela inteira dentro da arte, menos a
    margem morta) o score é -inf.
    """
    r = crit.bloco
    aw, ah = art_size
    kw, kh = max(3, round(win_w / r)), max(3, round(win_h / r))

    leg = uniform_filter(crit.legibilidade, size=(kh, kw), mode="constant", cval=0.0)
    cob = uniform_filter(crit.cobertura, size=(kh, kw), mode="constant", cval=0.0)
    score = leg * _bump(cob, COBERTURA_IDEAL, COBERTURA_LARGURA)

    margem_x = int(aw * MARGEM_BORDA)
    margem_y = int(ah * MARGEM_BORDA)
    lo_x = (margem_x + win_w // 2) // r
    hi_x = (aw - margem_x - win_w // 2) // r
    lo_y = (margem_y + win_h // 2) // r
    hi_y = (ah - margem_y - win_h // 2) // r
    valido = np.full(score.shape, False)
    if hi_x <= lo_x or hi_y <= lo_y:  # arte menor que a janela + margem
        lo_x, hi_x = 0, score.shape[1]
        lo_y, hi_y = 0, score.shape[0]
    valido[lo_y:hi_y, lo_x:hi_x] = True
    return np.where(valido, score, -np.inf)


def escolher_janela(crit: Criterio, art_size: tuple[int, int],
                    win_w: int, win_h: int) -> tuple[int, int]:
    """Centro da melhor janela `win_w × win_h`, em pixels da arte."""
    return escolher_janelas(crit, art_size, win_w, win_h, 1)[0]


def escolher_janelas(crit: Criterio, art_size: tuple[int, int],
                     win_w: int, win_h: int, quantas: int) -> list[tuple[int, int]]:
    """As `quantas` melhores janelas que **não se sobrepõem**.

    Pegar os `quantas` maiores do score direto não serve: o campo é suave, e os
    três maiores seriam três deslocamentos de um bloco da mesma janela — as
    avulsas sairiam praticamente iguais. Depois de escolher uma, a vizinhança do
    tamanho da própria janela é zerada antes da próxima rodada, então cada
    recorte vem de um lugar diferente da peça.

    Se a arte não comporta `quantas` janelas disjuntas, devolve menos — repetir
    a mesma região com outro nome seria pior que entregar três em vez de quatro.
    """
    r = crit.bloco
    aw, ah = art_size
    score = _campo_de_score(crit, art_size, win_w, win_h)
    kw, kh = max(1, round(win_w / r)), max(1, round(win_h / r))

    centros: list[tuple[int, int]] = []
    for _ in range(quantas):
        if not np.isfinite(score).any():
            break
        iy, ix = np.unravel_index(int(np.argmax(score)), score.shape)
        cx = int(np.clip(ix * r + r // 2, win_w // 2, max(win_w // 2, aw - win_w // 2)))
        cy = int(np.clip(iy * r + r // 2, win_h // 2, max(win_h // 2, ah - win_h // 2)))
        centros.append((cx, cy))
        score[max(0, iy - kh):iy + kh + 1, max(0, ix - kw):ix + kw + 1] = -np.inf
    return centros or [(aw // 2, ah // 2)]


def recortar(art: Image.Image, centro: tuple[int, int], win_w: int, win_h: int,
             saida: tuple[int, int]) -> Image.Image:
    """Recorta `win_w × win_h` em volta do centro e ajusta pra `saida`."""
    cx, cy = centro
    left = int(np.clip(cx - win_w // 2, 0, max(0, art.width - win_w)))
    top = int(np.clip(cy - win_h // 2, 0, max(0, art.height - win_h)))
    box = (left, top, min(left + win_w, art.width), min(top + win_h, art.height))
    corte = art.crop(box)
    if corte.size != saida:
        corte = kit.cover(corte, *saida)
    return corte


def faixa_silenciosa(crit: Criterio, faixa_h: int,
                     x0: int, x1: int) -> tuple[int, float]:
    """Topo da faixa mais vazia da arte, e a cobertura de tinta dela.

    Mede só entre `x0` e `x1` — a pegada real do bloco de título. Medir na
    largura inteira reprovaria uma faixa perfeitamente limpa à esquerda só
    porque a figura passa pelo lado direito, que é justamente onde o título não
    vai. É assim que o título encontra o branco que a peça já tem, em vez de
    fabricar um véu por cima dela.
    """
    r = crit.bloco
    kh = max(2, round(faixa_h / r))
    col0, col1 = max(0, x0 // r), min(crit.cobertura.shape[1], max(x0 // r + 1, x1 // r))
    perfil = crit.cobertura[:, col0:col1].mean(axis=1)
    if len(perfil) <= kh:
        return 0, float(perfil.mean() if len(perfil) else 1.0)
    janela = np.convolve(perfil, np.ones(kh) / kh, mode="valid")
    # entre faixas empatadas, fica com a **mais baixa**: título embaixo é a
    # leitura natural do pôster, e o topo destas peças costuma ser onde mora o
    # que não se pode tampar (a auréola, o chapéu, o rosto)
    empate = janela <= janela.min() + EMPATE_FAIXA
    i = int(np.max(np.flatnonzero(empate)))
    return i * r, float(janela[i])


# --------------------------------------------------------------------------
# peças
# --------------------------------------------------------------------------

def _assinatura(draw: ImageDraw.ImageDraw, fmt: kit.Format, y: int,
                gutter: int, ink=None) -> None:
    """Os quatro quadradinhos + o @ — o rodapé do pôster virado assinatura."""
    c = kit.colors()
    ink = c["ink"] if ink is None else ink
    lado = round(fmt.w * 0.0165)
    largura = kit.mark_squares(draw, gutter, y, lado, ink=ink, anchor="lm")
    f = kit.mono(round(fmt.w * 0.0205), 500)
    kit.draw_tracked(draw, (gutter + largura + lado * 1.6, y),
                     kit.brand()["INSTAGRAM"], f, ink, tracking=f.size * 0.06,
                     anchor="lm")


def _placa_pe(draw: ImageDraw.ImageDraw, fmt: kit.Format, escala: str) -> None:
    """A etiqueta de espécime no pé de um corte sangrado.

    Papel chapado com corte reto — **sem opacidade, sem degradê, sem sombra**.
    É a única maneira de escrever sobre uma malha cheia sem cair no véu
    semitransparente que denuncia o selo de banco de imagem. E é o mesmo gesto
    da margem do pôster, só que reduzido a um chip.

    A assinatura mora dentro da placa. Solta sobre a malha ela some — foi o que
    aconteceu na primeira versão.
    """
    c = kit.colors()
    gutter = round(fmt.w * 0.055)
    base_livre = kit.STORY_SAFE_BOTTOM if fmt is kit.STORY else round(fmt.h * 0.045)
    f = kit.mono(round(fmt.w * 0.019), 500)
    lado = round(fmt.w * 0.0165)
    pad = round(fmt.w * 0.019)
    linha_h = round(f.size * 2.1)

    largura_marca = lado * 4 + round(lado * 0.645) * 3
    f_at = kit.mono(round(fmt.w * 0.0205), 500)
    w_assinatura = largura_marca + lado * 1.6 + kit.text_width(
        kit.brand()["INSTAGRAM"], f_at, f_at.size * 0.06)
    w_escala = kit.text_width(escala, f, f.size * 0.14)
    w = max(w_assinatura, w_escala) + pad * 2

    y1 = fmt.h - base_livre
    y0 = y1 - linha_h * 2 - pad * 0.6
    draw.rectangle([gutter, y0, gutter + w, y1], fill=c["paper"])
    kit.draw_tracked(draw, (gutter + pad, y0 + pad * 0.3 + linha_h / 2), escala, f,
                     c["footer-grey"], f.size * 0.14, anchor="lm")
    _assinatura(draw, fmt, int(y0 + pad * 0.3 + linha_h * 1.5), gutter + pad)


def carta_arte(obra: Obra, crit: Criterio, fmt: kit.Format,
               modo: str = "auto") -> Image.Image:
    """01 — a peça inteira, com o título.

    `modo` decide onde o título mora, e é uma escolha de gosto, não de medida:

    - `auto` (padrão) — o título vai **sobre a arte** se existir uma faixa
      silenciosa que o comporte, e desce pro papel se não existir. Na coleção
      de hoje quase nunca existe: o bloco de título ocupa perto de 19% da
      altura da carta, e nessas peças a figura preenche a página quase inteira.
      Então o resultado normal é a ficha de espécime — título no papel, arte
      com moldura, nada se cruzando. Que é exatamente o que o pôster faz.
    - `sobre` — força o título por cima. Se houver silêncio, escreve direto na
      tinta; se não houver, entra uma placa de papel de **corte reto** dentro
      da área da arte. Continua sem véu e sem degradê: o que muda é que a
      placa tampa um pedaço da peça em vez de ficar embaixo dela.
    - `papel` — sempre embaixo, mesmo que caiba em cima.

    O bloco de título é dimensionado **antes** da arte. Assim o enquadramento
    não muda de peça pra peça, e o story não abre o buraco que abriria se a
    arte fosse centrada sozinha num quadro muito mais alto que ela.
    """
    c = kit.colors()
    img, draw = kit.canvas(fmt)
    gutter = round(fmt.w * 0.072)
    margem_arte = round(fmt.w * 0.042)
    topo_livre = kit.STORY_SAFE_TOP if fmt is kit.STORY else round(fmt.h * 0.03)
    base_livre = (kit.STORY_SAFE_BOTTOM if fmt is kit.STORY else round(fmt.h * 0.03))
    assinatura_h = round(fmt.h * 0.082)

    titulo = obra.titulo.upper()
    caixa_w = fmt.w - margem_arte * 2
    f_tit = kit.fit_display(titulo, fmt.w - gutter * 2, max_size=round(fmt.w * 0.125))
    f_lab = kit.mono(round(fmt.w * 0.0195), 500)
    sub = kit.mono(round(fmt.w * 0.0185), 400)
    bloco_h = round(f_lab.size * 2.6 + f_tit.size * 1.15
                    + (sub.size * 2.0 if obra.subtitulo else 0))
    folga = round(fmt.h * 0.028)

    # em `sobre` o título não pede espaço embaixo, então a arte cresce
    reserva = 0 if modo == "sobre" else bloco_h + folga
    caixa_h = fmt.h - topo_livre - base_livre - assinatura_h - reserva
    escala = min(caixa_w / obra.art.width, caixa_h / obra.art.height)
    aw, ah = round(obra.art.width * escala), round(obra.art.height * escala)
    ax = (fmt.w - aw) // 2
    ay = topo_livre + max(
        0, (fmt.h - topo_livre - base_livre - assinatura_h - ah - reserva) // 2)
    img.paste(obra.art.resize((aw, ah), Image.LANCZOS), (ax, ay))
    kit.hairline(draw, [ax, ay, ax + aw - 1, ay + ah - 1])

    # onde o título cabe sem véu: a faixa mais vazia da arte, medida só na
    # pegada horizontal que o título realmente ocupa
    x = gutter
    tx0 = int(max(0, (x - ax) / escala))
    tx1 = int(min(obra.art.width, (x - ax + f_tit.getlength(titulo)) / escala))
    faixa_y, cobertura = faixa_silenciosa(crit, round(bloco_h / escala), tx0, tx1)
    tem_silencio = cobertura <= COBERTURA_TITULO

    if modo != "papel" and tem_silencio:
        # o branco já existe na arte: escreve direto, em tinta sólida, sem véu
        y = int(np.clip(ay + round(faixa_y * escala),
                        ay + round(fmt.h * 0.015), ay + ah - bloco_h))
    elif modo == "sobre":
        # placa de papel de corte reto DENTRO da arte — sem opacidade nenhuma.
        # A placa fica presa às bordas da arte: escapando por cima ela cortaria
        # a moldura e a carta perderia o enquadramento de espécime.
        recuo = round(fmt.h * 0.018)
        alto = bloco_h + round(fmt.h * 0.03)
        topo = int(np.clip(ay + round(faixa_y * escala) - recuo,
                           ay, max(ay, ay + ah - alto)))
        y = topo + recuo
        draw.rectangle([ax, topo, ax + aw - 1, min(topo + alto, ay + ah - 1)],
                       fill=c["paper"])
        if topo > ay:
            draw.line([ax, topo, ax + aw - 1, topo], fill=c["rule"])
    else:
        # sem silêncio na arte: o título desce pro papel, embaixo da moldura
        y = ay + ah + folga

    kit.eyebrow(draw, x, y + f_lab.size, "espécime", f_lab)
    kit.draw_tracked(draw, (x, y + f_lab.size * 2.6 + f_tit.size * 0.92),
                     titulo, f_tit, c["ink"], anchor="ls")
    if obra.subtitulo:
        kit.draw_tracked(draw, (x, y + f_lab.size * 2.6 + f_tit.size * 1.35),
                         obra.subtitulo.upper(), sub, c["footer-grey"],
                         tracking=sub.size * 0.1, anchor="la")

    _assinatura(draw, fmt, fmt.h - base_livre - assinatura_h // 2, gutter)
    return img


def carta_corte(obra: Obra, centro: tuple[int, int], win_w: int, win_h: int,
                fmt: kit.Format, etiqueta: str) -> tuple[Image.Image, Image.Image]:
    """02 e 03 — corte sangrado. Devolve (carta, recorte cru).

    O recorte cru serve à ficha: colar a *carta* na faixa da 04 levaria a placa
    junto, e a placa apareceria duas vezes na mesma peça.
    """
    cru = recortar(obra.art, centro, win_w, win_h, fmt.size)
    img = cru.copy()
    _placa_pe(ImageDraw.Draw(img), fmt, etiqueta)
    return img, cru


def carta_ficha(obra: Obra, macro: Image.Image, fmt: kit.Format) -> Image.Image:
    """04 — a ficha de espécime, no vocabulário do pôster."""
    c = kit.colors()
    img, draw = kit.canvas(fmt)
    gutter = round(fmt.w * 0.072)
    y = (kit.STORY_SAFE_TOP if fmt is kit.STORY else round(fmt.h * 0.075))

    f_lab = kit.mono(round(fmt.w * 0.0195), 500)
    kit.eyebrow(draw, gutter, y, "ficha de espécime", f_lab)
    y += round(fmt.h * 0.035)

    f_tit = kit.fit_display(obra.titulo.upper(), fmt.w - gutter * 2,
                            max_size=round(fmt.w * 0.115))
    kit.draw_tracked(draw, (gutter, y + f_tit.size * 0.82), obra.titulo.upper(),
                     f_tit, c["ink"], anchor="ls")
    y += round(f_tit.size * 1.02)

    if obra.subtitulo:
        f_sub = kit.mono(round(fmt.w * 0.019), 400)
        for linha in kit.wrap(obra.subtitulo.upper(), f_sub, fmt.w - gutter * 2,
                              f_sub.size * 0.1):
            kit.draw_tracked(draw, (gutter, y), linha, f_sub, c["footer-grey"],
                             tracking=f_sub.size * 0.1, anchor="la")
            y += round(f_sub.size * 1.5)

    y += round(fmt.h * 0.022)
    draw.line([gutter, y, fmt.w - gutter, y], fill=c["rule"])
    y += round(fmt.h * 0.028)

    linhas = [
        ("impressão", f"{num(obra.pagina_cm[0])} × {num(obra.pagina_cm[1])} cm"),
        ("glifos", num(obra.glifos) if obra.glifos else "—"),
        ("fonte", obra.fonte),
        ("corpo", f"{num(obra.corpo_mm, 1)} mm"),
        ("camadas", " · ".join(obra.camadas)),
        ("resolução", f"{num(obra.dpi)} dpi"),
    ]
    f_key = kit.mono(round(fmt.w * 0.0185), 500)
    f_val = kit.mono(round(fmt.w * 0.0215), 400)
    col = round(fmt.w * 0.30)
    for chave, valor in linhas:
        kit.draw_tracked(draw, (gutter, y), chave.upper(), f_key, c["grey"],
                         tracking=f_key.size * 0.14, anchor="la")
        for i, linha in enumerate(kit.wrap(valor, f_val, fmt.w - gutter - col)):
            kit.draw_tracked(draw, (gutter + col, y + i * f_val.size * 1.4), linha,
                             f_val, c["ink"], anchor="la")
        y += round(f_val.size * 1.95)

    # a faixa de macro no pé: a ficha mostra o material, não só descreve
    faixa_h = round(fmt.h * 0.20)
    base_livre = (kit.STORY_SAFE_BOTTOM if fmt is kit.STORY else round(fmt.h * 0.085))
    faixa_y = fmt.h - base_livre - faixa_h

    # os versos que viraram imagem — é o que separa "arte feita de letras" de
    # "arte feita DESTA letra". Entram tantos quantos couberem entre a tabela e
    # a faixa de macro, então a ficha nunca sai com um buraco no meio.
    if obra.versos:
        y += round(fmt.h * 0.018)
        draw.line([gutter, y, fmt.w - gutter, y], fill=c["rule"])
        y += round(fmt.h * 0.030)
        kit.draw_tracked(draw, (gutter, y), "O TEXTO", f_key, c["grey"],
                         tracking=f_key.size * 0.14, anchor="la")
        y += round(fmt.h * 0.026)
        f_verso = kit.display(round(fmt.w * 0.042), wght=500, wdth=88)
        passo = round(f_verso.size * 1.18)
        limite = faixa_y - round(fmt.h * 0.035)
        for verso in obra.versos:
            for linha in kit.wrap(verso, f_verso, fmt.w - gutter * 2):
                if y + passo > limite:
                    break
                kit.draw_tracked(draw, (gutter, y + f_verso.size * 0.82), linha,
                                 f_verso, c["ink-warm"], anchor="ls")
                y += passo
            else:
                continue
            break
    img.paste(kit.cover(macro, fmt.w - gutter * 2, faixa_h), (gutter, faixa_y))
    kit.hairline(draw, [gutter, faixa_y, fmt.w - gutter - 1, faixa_y + faixa_h - 1])

    _assinatura(draw, fmt, faixa_y + faixa_h + round(fmt.h * 0.035), gutter)
    site = kit.site_label()
    if site:
        f_site = kit.mono(round(fmt.w * 0.019), 400)
        kit.draw_tracked(draw, (fmt.w - gutter, faixa_y + faixa_h + round(fmt.h * 0.035)),
                         site, f_site, c["grey"], tracking=f_site.size * 0.06, anchor="rm")
    return img


def carta_story_unica(obra: Obra, crit: Criterio,
                      fmt: kit.Format = kit.STORY) -> Image.Image:
    """O story inteiro numa carta só — a peça e o macro na mesma tela.

    O carrossel do feed conta em quatro passos porque o dedo passa de uma carta
    pra outra, e o salto de escala acontece no tempo. No story não passa: é uma
    tela e alguns segundos. Subir a carta 01 sozinha entrega um retrato, e o que
    a peça tem de próprio — que ela é *escrita* — fica de fora; subir só o macro
    entrega textura sem obra.

    Então esta põe os dois planos na mesma tela, um dentro do outro: o macro
    1:1 sangrando nos quatro lados, e a peça inteira numa **placa de papel de
    corte reto** por cima. As letras do fundo cercam o retrato — que é
    literalmente o que a peça faz.

    Empilhar (peça em cima, faixa de macro embaixo) foi a primeira tentativa e
    saiu errada: num quadro 9:16 sobra tão pouca altura pro retrato que ele vira
    selo no meio do branco. O fundo sangrado resolve porque a arte não disputa
    espaço com o macro — ela mora em cima dele.

    Continua **sem véu, sem degradê e sem sombra**: a placa é opaca e de corte
    reto, o mesmo gesto da margem do pôster. E o fundo não é textura decorativa,
    é a própria peça no tamanho de impressão.
    """
    c = kit.colors()
    img = Image.new("RGB", fmt.size, c["paper"])

    # --- o fundo: a própria peça, 1:1 com o arquivo de impressão -------------
    centro = escolher_janela(crit, obra.art.size, fmt.w, fmt.h)
    img.paste(recortar(obra.art, centro, fmt.w, fmt.h, fmt.size), (0, 0))
    draw = ImageDraw.Draw(img)

    # --- a placa: dimensionada pela altura livre entre as zonas seguras ------
    topo = kit.STORY_SAFE_TOP
    base = fmt.h - kit.STORY_SAFE_BOTTOM
    pad = round(fmt.w * 0.038)
    f_lab = kit.mono(round(fmt.w * 0.0195), 500)
    f_sub = kit.mono(round(fmt.w * 0.0185), 400)
    f_nota = kit.mono(round(fmt.w * 0.017), 400)

    titulo = obra.titulo.upper()
    tit_max = round(fmt.w * 0.085)
    subs = (kit.wrap(obra.subtitulo.upper(), f_sub, fmt.w * 0.62, f_sub.size * 0.1)
            if obra.subtitulo else [])
    # tudo que a placa carrega além da arte — some antes de sobrar altura pra ela
    fora_da_arte = round(
        pad * 2 + f_lab.size * 2.6 + tit_max * 1.06 + len(subs) * f_sub.size * 1.5
        + fmt.h * 0.014 + f_nota.size * 1.9 + fmt.h * 0.012 + fmt.w * 0.0165 * 1.9
    )
    art_h = max(1, (base - topo) - fora_da_arte)
    art_w = min(round(art_h * obra.art.width / obra.art.height),
                round(fmt.w * 0.80) - pad * 2)
    art_h = round(art_w * obra.art.height / obra.art.width)

    placa_w = art_w + pad * 2
    placa_h = art_h + fora_da_arte
    px = (fmt.w - placa_w) // 2
    py = topo + max(0, (base - topo - placa_h) // 2)
    draw.rectangle([px, py, px + placa_w - 1, py + placa_h - 1], fill=c["paper"])

    y = py + pad
    kit.eyebrow(draw, px + pad, y + f_lab.size, "espécime", f_lab)
    y += round(f_lab.size * 2.6)
    f_tit = kit.fit_display(titulo, art_w, max_size=tit_max)
    kit.draw_tracked(draw, (px + pad, y + f_tit.size * 0.92), titulo, f_tit,
                     c["ink"], anchor="ls")
    y += round(tit_max * 1.06)
    for linha in subs:
        kit.draw_tracked(draw, (px + pad, y), linha, f_sub, c["footer-grey"],
                         tracking=f_sub.size * 0.1, anchor="la")
        y += round(f_sub.size * 1.5)

    y += round(fmt.h * 0.014)
    img.paste(obra.art.resize((art_w, art_h), Image.LANCZOS), (px + pad, y))
    kit.hairline(draw, [px + pad, y, px + pad + art_w - 1, y + art_h - 1])
    y += art_h

    # diz o que é o fundo. Sem esta linha ele lê como textura de enfeite, que é
    # justamente o contrário do que ele é.
    kit.draw_tracked(draw, (px + pad, y + f_nota.size * 1.5),
                     f"O FUNDO É ESTA MESMA PEÇA · 1:1 · "
                     f"{num(fmt.w * obra.cm_por_px)} × {num(fmt.h * obra.cm_por_px)} CM",
                     f_nota, c["grey"], tracking=f_nota.size * 0.1, anchor="ls")
    y += round(f_nota.size * 1.9 + fmt.h * 0.012)
    _assinatura(draw, fmt, y + round(fmt.w * 0.0165 * 0.95), px + pad)
    return img


# --------------------------------------------------------------------------
# avulsas — material solto, pra montar à mão
# --------------------------------------------------------------------------

def avulsa_titulo(obra: Obra, largura: int = 2400) -> Image.Image:
    """O bloco de título isolado, em PNG com **alfa**.

    Sem carta, sem papel e sem moldura: quem escolhe o fundo é a montagem, não
    este script. Com o papel chapado embutido o bloco só serviria sobre papel —
    com alfa ele assenta sobre a arte, sobre tinta ou sobre o que for.

    O desenho é o mesmo da carta 01 (etiqueta com quadradinho, título em Archivo
    condensada, subtítulo em mono) porque a peça avulsa e a carta têm que
    parecer a mesma marca quando aparecem no mesmo feed.
    """
    c = kit.colors()
    titulo = obra.titulo.upper()
    margem = round(largura * 0.015)
    util = largura - margem * 2

    f_tit = kit.fit_display(titulo, util, max_size=round(largura * 0.20))
    f_lab = kit.mono(round(largura * 0.0175), 500)
    f_sub = kit.mono(round(largura * 0.0165), 400)
    subs = kit.wrap(obra.subtitulo.upper(), f_sub, util, f_sub.size * 0.1) if obra.subtitulo else []

    alto = round(margem * 2 + f_lab.size * 2.6 + f_tit.size * 1.06
                 + len(subs) * f_sub.size * 1.5 + f_lab.size * 2.2)
    img = Image.new("RGBA", (largura, alto), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    y = margem
    kit.eyebrow(draw, margem, y + f_lab.size, "espécime", f_lab)
    y += round(f_lab.size * 2.6)
    kit.draw_tracked(draw, (margem, y + f_tit.size * 0.92), titulo, f_tit,
                     c["ink"], anchor="ls")
    y += round(f_tit.size * 1.06)
    for linha in subs:
        kit.draw_tracked(draw, (margem, y), linha, f_sub, c["footer-grey"],
                         tracking=f_sub.size * 0.1, anchor="la")
        y += round(f_sub.size * 1.5)
    kit.mark_squares(draw, margem, y + f_lab.size * 0.9, round(largura * 0.014),
                     anchor="lm")
    return img


def avulsa_peca(obra: Obra, lado: int = 1800) -> Image.Image:
    """A peça inteira, crua — sem carta, sem moldura, sem título.

    É a carta 01 menos tudo que a carta 01 acrescenta. Serve pra montagem à mão
    (o fundo é escolha de quem monta) e é a única fonte de arte limpa que
    funciona pra **toda** obra: o `site/public/art/<slug>-full.webp` depende do
    `build_site_assets.py`, que precisa da imagem de referência — e a do
    `magalenha` se perdeu. Aqui a arte já veio recortada do export.

    Não amplia: obra menor que `lado` sai no tamanho que tem.
    """
    escala = min(1.0, lado / max(obra.art.size))
    if escala >= 1.0:
        return obra.art.copy()
    return obra.art.resize((max(1, round(obra.art.width * escala)),
                            max(1, round(obra.art.height * escala))), Image.LANCZOS)


def avulsas_malha(obra: Obra, crit: Criterio, quantas: int = 3,
                  lado: int = 1400) -> list[tuple[str, Image.Image]]:
    """Recortes 1:1 da malha, crus — sem placa, sem etiqueta, sem moldura.

    São `lado × lado` pixels tirados direto do export, então cada um é material
    de impressão em tamanho real, não uma imagem reamostrada. As janelas são
    escolhidas pelo mesmo critério das cartas e **não se sobrepõem**: três
    recortes da mesma região seriam a mesma imagem três vezes.

    Se a arte for menor que `lado`, o recorte sai do tamanho que couber, em vez
    de ampliar — ampliar entregaria borrão anunciado como 1:1.
    """
    lado = min(lado, obra.art.width, obra.art.height)
    centros = escolher_janelas(crit, obra.art.size, lado, lado, quantas)
    saida = []
    for i, centro in enumerate(centros, 1):
        saida.append((f"malha-{i:02d}.png",
                      recortar(obra.art, centro, lado, lado, (lado, lado))))
    return saida


# --------------------------------------------------------------------------
# debug
# --------------------------------------------------------------------------

def chapa_carrossel(obra: Obra, cartas: list[tuple[str, Image.Image]],
                    fmt: kit.Format, largura: int = 1800) -> Image.Image:
    """As quatro cartas em sequência — é assim que se julga a narrativa.

    Uma carta boa sozinha não quer dizer nada: o que tem que funcionar é o
    salto de uma pra outra, de longe pra perto.
    """
    c = kit.colors()
    pad, gap = 44, 26
    cell_w = (largura - pad * 2 - gap * 3) // 4
    cell_h = round(cell_w * fmt.h / fmt.w)
    img = Image.new("RGB", (largura, pad * 2 + 150 + cell_h + 56), c["paper"])
    draw = ImageDraw.Draw(img)
    kit.eyebrow(draw, pad, pad + 16, f"{obra.slug} · carrossel {fmt.name}", kit.mono(19, 500))
    kit.draw_tracked(draw, (pad, pad + 60), "DE LONGE PRA PERTO", kit.display(38),
                     c["ink"], anchor="la")
    for i, (nome, carta) in enumerate(cartas):
        x = pad + i * (cell_w + gap)
        y = pad + 150
        img.paste(carta.resize((cell_w, cell_h), Image.LANCZOS), (x, y))
        draw.rectangle([x, y, x + cell_w - 1, y + cell_h - 1], outline=c["rule"])
        kit.draw_tracked(draw, (x, y + cell_h + 24), nome.upper(), kit.mono(16, 500),
                         c["grey"], tracking=16 * 0.14, anchor="la")
    return img


def chapa_debug(obra: Obra, crit: Criterio, janelas: list[tuple[str, tuple[int, int], int, int]],
                largura: int = 1500) -> Image.Image:
    """Mapa do critério + as janelas escolhidas, pra conferir a decisão."""
    c = kit.colors()
    leg = crit.legibilidade
    norm = leg / max(leg.max(), 1e-6)
    mapa = Image.fromarray((np.clip(norm, 0, 1) * 255).astype(np.uint8), "L").convert("RGB")
    mapa = mapa.resize(obra.art.size, Image.BILINEAR)

    lado = largura // 2 - 30
    esq = kit.contain(obra.art, lado, lado)
    dir_ = kit.contain(mapa, lado, lado)

    escala = min(lado / obra.art.width, lado / obra.art.height)
    off_x = (lado - round(obra.art.width * escala)) // 2
    off_y = (lado - round(obra.art.height * escala)) // 2
    for painel in (esq, dir_):
        d = ImageDraw.Draw(painel)
        for nome, (cx, cy), w, h in janelas:
            x0 = off_x + (cx - w // 2) * escala
            y0 = off_y + (cy - h // 2) * escala
            d.rectangle([x0, y0, x0 + w * escala, y0 + h * escala],
                        outline=c["accent"], width=3)
            kit.draw_tracked(d, (x0 + 8, y0 + 8), nome.upper(), kit.mono(15, 500),
                             c["accent"], tracking=2, anchor="la")

    img = Image.new("RGB", (largura, lado + 230), c["paper"])
    draw = ImageDraw.Draw(img)
    kit.eyebrow(draw, 30, 42, f"{obra.slug} · escolha do recorte", kit.mono(19, 500))
    kit.draw_tracked(draw, (30, 84), "MIN(ESPESSURA DA TINTA, FOLGA DO BRANCO)",
                     kit.display(34), c["ink"], anchor="la")
    img.paste(esq, (30, 140))
    img.paste(dir_, (largura // 2 + 15, 140))
    for texto, x in (("arte", 30), ("critério — claro = mais legível", largura // 2 + 15)):
        kit.draw_tracked(draw, (x, lado + 158), texto.upper(), kit.mono(16, 500),
                         c["grey"], tracking=16 * 0.14, anchor="la")
    return img


# --------------------------------------------------------------------------

def montar(slug: str, formatos: list[kit.Format], debug: bool,
           titulo: str = "auto", story: str = "unico",
           avulsas: int = 3) -> list[Path]:
    obra = carregar(slug)
    print(f"  arte {obra.art.width}×{obra.art.height}px "
          f"({num(obra.art.width * obra.cm_por_px)}×"
          f"{num(obra.art.height * obra.cm_por_px)}cm) · "
          f"página {num(obra.pagina_cm[0])}×{num(obra.pagina_cm[1])}cm @ {num(obra.dpi)}dpi")
    crit = medir(obra.art)

    escritos: list[Path] = []
    if avulsas:
        destino = OUT_ROOT / slug / "avulsas"
        escritos.append(kit.save(avulsa_titulo(obra), destino / "titulo.png"))
        escritos.append(kit.save(avulsa_peca(obra), destino / "peca.png"))
        for nome, corte in avulsas_malha(obra, crit, avulsas):
            escritos.append(kit.save(corte, destino / nome))

    for fmt in formatos:
        # o story sai numa carta só por padrão: lá não existe "passar o dedo
        # pra próxima", então o mergulho tem que caber numa tela
        if fmt is kit.STORY and story == "unico":
            destino = OUT_ROOT / slug / fmt.name
            # obra gerada antes do story único deixou as quatro cartas aqui.
            # Não apago (é arquivo de saída de outra rodada, e apagar por conta
            # própria é pior que avisar), mas o `publish_media.py` publicaria as
            # cinco e o cartão do /admin ficaria com um story de quatro imagens.
            velhas = sorted(p.name for p in destino.glob("0*.png"))
            if velhas:
                print(f"  ! sobraram {len(velhas)} cartas do story antigo em "
                      f"{destino.relative_to(ROOT)}: {', '.join(velhas)}\n"
                      f"    apague antes de publicar, ou o cartão do /admin sai "
                      f"com story de {len(velhas) + 1} imagens")
            escritos.append(kit.save(carta_story_unica(obra, crit, fmt),
                                     destino / "story.png"))
            continue
        # o macro é 1:1 com o pixel do export — nítido por construção
        win_w, win_h = fmt.w, fmt.h
        centro = escolher_janela(crit, obra.art.size, win_w, win_h)
        meio_w, meio_h = round(win_w * ZOOM_MEIO), round(win_h * ZOOM_MEIO)
        # o corte do meio é centrado no MESMO ponto: o carrossel vira um
        # mergulho contínuo, não três recortes avulsos
        meio_c = (int(np.clip(centro[0], meio_w // 2, max(meio_w // 2, obra.art.width - meio_w // 2))),
                  int(np.clip(centro[1], meio_h // 2, max(meio_h // 2, obra.art.height - meio_h // 2))))

        macro, macro_cru = carta_corte(
            obra, centro, win_w, win_h, fmt,
            f"1:1 · recorte de {num(win_w * obra.cm_por_px)} × "
            f"{num(win_h * obra.cm_por_px)} cm da peça")
        meio, _ = carta_corte(
            obra, meio_c, meio_w, meio_h, fmt,
            f"1:{num(ZOOM_MEIO, 1)} · {num(meio_w * obra.cm_por_px)} × "
            f"{num(meio_h * obra.cm_por_px)} cm da peça")

        destino = OUT_ROOT / slug / fmt.name
        pares = [
            ("01-arte.png", carta_arte(obra, crit, fmt, titulo)),
            ("02-malha.png", meio),
            ("03-macro.png", macro),
            ("04-ficha.png", carta_ficha(obra, macro_cru, fmt)),
        ]
        for nome, img in pares:
            escritos.append(kit.save(img, destino / nome))

        if debug:
            janelas = [("meio", meio_c, meio_w, meio_h), ("macro", centro, win_w, win_h)]
            debug_dir = OUT_ROOT / slug / "debug"
            escritos.append(kit.save(chapa_debug(obra, crit, janelas),
                                     debug_dir / f"recorte-{fmt.name}.png"))
            escritos.append(kit.save(
                chapa_carrossel(obra, [(Path(n).stem.split("-", 1)[1], i) for n, i in pares], fmt),
                debug_dir / f"carrossel-{fmt.name}.png"))

    if obra.degradado:
        print("  ! saída DEGRADADA (fonte foi o webp do site, não o export)")
    return escritos


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("slugs", nargs="+", help="nome do projeto em projects/")
    ap.add_argument("--formatos", default="feed,story",
                    help="feed (1080×1350), story (1080×1920), quadrado (1080×1080)")
    ap.add_argument("--titulo", default="auto", choices=("auto", "sobre", "papel"),
                    help="onde o título da carta 01 mora: auto (sobre a arte se "
                         "houver faixa silenciosa, senão no papel), sobre (força "
                         "por cima, com placa de corte reto quando precisar) ou "
                         "papel (sempre embaixo)")
    ap.add_argument("--story", default="unico", choices=("unico", "carrossel"),
                    help="unico (padrão): uma carta só, com a peça e o macro na "
                         "mesma tela. carrossel: as mesmas quatro cartas do feed")
    ap.add_argument("--avulsas", type=int, default=3, metavar="N",
                    help="N recortes 1:1 da malha + o título com alfa, em "
                         "social/<slug>/avulsas/ (0 desliga)")
    ap.add_argument("--debug", action="store_true",
                    help="escreve o mapa do critério e as janelas escolhidas")
    args = ap.parse_args()

    tabela = {"feed": kit.FEED, "story": kit.STORY, "quadrado": kit.SQUARE}
    try:
        formatos = [tabela[n.strip()] for n in args.formatos.split(",") if n.strip()]
    except KeyError as exc:
        raise SystemExit(f"formato desconhecido: {exc}. Use {', '.join(tabela)}")

    total = 0
    for slug in args.slugs:
        print(f"\n{slug}")
        for path in montar(slug, formatos, args.debug, args.titulo,
                           args.story, args.avulsas):
            print(f"  ok {path.relative_to(ROOT)}")
            total += 1
    print(f"\n{total} imagens -> {OUT_ROOT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
