#!/usr/bin/env python3
"""A peca da Jane, a partir de `arte que eu mais gostei.png`.

Virada de 06/08/2026, segunda parte. O Gustavo olhou o que tinhamos feito com
`referencia-ilustracao.png` (medalhao, anel, palavra na linha do arco) e disse
que ficou ruim. Mandou outra referencia e ela reescreve tudo:

  projects/vovo-jane/arte que eu mais gostei.png

O que essa referencia decide, e que as anteriores erravam:

- **Malha de corpo quase unico.** As linhas dela sao finas, retas e LEGIVEIS, e
  a sombra e hachura de leve. As nossas iam de 1,9 a 6,3 mm — 3,3x de faixa — e
  no escuro os glifos se encostavam e viravam mancha. Aqui a faixa e 1,5x. Essa
  e a correcao principal; o resto e consequencia.
- **Sem anel.** A frase nao circula: sai em quatro blocos, tres na lateral
  esquerda e no pe, e o "AMOR" grande atravessando a altura do peito.
- **O texto e ESCRITO, nao desenhado.** Na referencia o "AMOR" ainda e feito de
  letrinha densa — e justamente o que ele nao quer. Aqui os quatro blocos sao
  tipo de verdade, por `display.marks`, que e a primitiva da casa pra isso.

O que este script faz que o motor nao faz sozinho:

1. **Tira os blocos de tipo da referencia** (cinza dessaturado, solido) e o
   fantasma do "AMOR" (letrinha adensada), reconstruindo o tom por baixo pelo
   vizinho mais proximo. Sem isso o motor redesenharia as letras dela como
   malha e o tipo de verdade cairia por cima, dobrado.
2. **Achata o papel** e **desfaz o halftone dela** antes do nosso: a referencia
   ja e um halftone de letra, e um halftone em cima do outro bate e vira mancha
   de 1 cm. A media e por CELULA do motor (`Image.BOX` ate 167x217), que e a
   conta exata do que ele vai amostrar — nao um borrao gaussiano chutado.
3. **Traduz as posicoes** medidas na referencia pra cm de pagina A1, e resolve o
   corpo de cada bloco de tipo pela LARGURA que ele ocupa la — nao por chute.

RESOLUCAO: a referencia tem 1101 px de largura contra os 3035 que a caixa de
arte de um A1 a 150 dpi pede. Upscale de 2,76x, pior que o da anterior (2,19x).
Vale o mesmo argumento: o motor e um redutor e a sonda dele cobre ~6 px do
arquivo original a 3 mm. O tom passa. E o unico jeito de melhorar isso e ele
conseguir o arquivo maior, que com Gemini quer dizer outro desenho.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import yaml
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy import ndimage as ndi

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from typo.fonts import resolve_family, load as load_font  # noqa: E402

#: Versao da peca. Cada numero vira um PDF proprio em output/, e uma linha em
#: output/VERSOES.md — sem isso nao da pra saber qual PDF e qual depois de meia
#: duzia de rodadas, que foi o que aconteceu.
VERSAO = 5
NOTA = ("conserta o vazamento da mascara de tipo, que abria um buraco na testa "
        "do Gilber (saturacao + crescimento limitado). Tipografia identica a v4.")

RAIZ = Path(__file__).resolve().parents[1]
REF = RAIZ / "projects/vovo-jane/arte que eu mais gostei.png"
LETRA = RAIZ / "projects/vovo-jane/text/como-e-grande.txt"
DESTINO = RAIZ / "projects/vovo-jane-arte"

# ---- pagina A1 COM margem -------------------------------------------------- #
PAG_W, PAG_H = 59.4, 84.1
MARGEM = dict(top=11.0, bottom=8.0, side=4.0)
ART_W = PAG_W - 2 * MARGEM["side"]                 # 51,4 cm
ART_H = PAG_H - MARGEM["top"] - MARGEM["bottom"]   # 65,1 cm
DPI = 150
CANVAS_W = int(round(ART_W / 2.54 * DPI))          # 3035
CANVAS_H = int(round(ART_H / 2.54 * DPI))          # 3844

#: A referencia e 0,7705 de proporcao e a caixa de arte 0,7896 — ela e mais
#: alta. Encaixa pela ALTURA (deformar seria mentir sobre o desenho dele) e
#: sobra 0,6 cm de cada lado, que vira respiro.
ARTE_H = ART_H
ARTE_W = ART_H * 1101 / 1429                       # 50,2 cm
ARTE_X = MARGEM["side"] + (ART_W - ARTE_W) / 2     # 4,6 cm da borda da pagina
ARTE_Y = MARGEM["top"]

# ---- extracao -------------------------------------------------------------- #
#: Duas peneiras, nao uma. NUCLEO pega so o miolo escuro das letras; CORPO e
#: ate onde a reconstrucao pode crescer a partir dele. Uma peneira so nao
#: resolve: em 175 sobravam pedacos claros das letras, e em 215 ela limpava a
#: CAIXA INTEIRA — abria um vazio branco colado no rosto do Gilber, que foi a
#: falha que ele apontou. A letra cresce do nucleo dela; a textura do fundo nao
#: encosta em nucleo nenhum, entao fica.
#: SATURACAO e o que separa a letra do desenho, nao a luminancia. Medido: os
#: blocos de tipo dela sao neutros (sat 0,03-0,04) e o cabelo do Gilber e
#: desenhado em tinta quente (sat 0,205) — mas os dois moram na mesma faixa
#: escura, entao filtrar so por luminancia nao distingue.
#:
#: O bug que isso conserta: a mascara de CRESCIMENTO nao tinha restricao de
#: saturacao nenhuma, so `lum < TIPO_CORPO`. Como o "e" de "grande" encosta no
#: cabelo dele, a reconstrucao pulou da letra pro cabelo e inundou — e o
#: retangulo que sobrou na testa dele era a inundacao batendo na borda da caixa.
#: Foi exatamente a falha que ele marcou de vermelho.
TIPO_NUCLEO, TIPO_CORPO, TIPO_SAT = 172, 232, 0.08
#: e mesmo com a saturacao segurando, o crescimento e LIMITADO. Propagacao sem
#: limite atravessa qualquer ponte de um pixel; 6 passos bastam pra recuperar a
#: borda anti-serrilhada de uma letra e nao chegam em lugar nenhum.
TIPO_CRESCE = 6
#: folga da silhueta do tipo, em px da referencia. A fonte dela nao e a Cambria,
#: entao as duas nao coincidem glifo a glifo; 10 px cobrem a diferenca sem
#: chegar perto do desenho.
TIPO_FOLGA = 4
#: o fantasma do "AMOR": letrinha ADENSADA, nao cor propria. Separa por
#: densidade local — media numa janela do tamanho de uma letra, dentro da caixa
#: onde a palavra mora. Fora dessa caixa nada e tocado.
#: as caixas dos quatro blocos, em px da referencia. Sao elas que limitam a
#: A caixa de tinta de cada LINHA de texto, medida na referencia varrendo
#: COLUNA A COLUNA a tinta solida do tipo (lum<130 e sat<0,08) e parando onde
#: ela some. Uma caixa por linha, nao por bloco: bloco vira retangulo grande, e
#: retangulo grande encosta no desenho.
#:
#: A primeira medida dava "e grande" indo ate x=399 e estava ERRADA — o detector
#: somava o cabelo do Gilber, que comeca logo depois. A varredura por coluna
#: mostra o corte limpo: 73 px de tinta em x=348-353, ZERO em 354-359, e dai pra
#: frente so cabelo, esparso (1 a 5 px por coluna). O fim de verdade e 353.
#:
#: Esses 46 px de erro sao a causa raiz do buraco na testa dele: a caixa entrava
#: no cabelo, a busca achava tinta escura la dentro, e apagava.
TIPO_LINHAS = [
    (64, 339, 209, 400),      # como
    (61, 366, 356, 462),      # e grande
    (75, 1146, 118, 1194),    # o
    (76, 1210, 234, 1265),    # meu
    (593, 1266, 896, 1364),   # por voce
]
AMOR_CAIXA = (255, 1090, 885, 1285)   # px da referencia
AMOR_JANELA, AMOR_LIMIAR = 9, 176
PAPEL_JANELA, PAPEL_PCT, PAPEL_ESCALA = 121, 92, 6
ESTICA_PCT = (1.0, 99.0)   # percentis que viram preto e papel
#: A referencia modula o VALOR da letra, nao o tamanho: texto claro na luz,
#: escuro na sombra, tudo no mesmo corpo. Foi por isso que a primeira tentativa
#: saiu chapada — em monocromatico o motor so tem tamanho, e a testa dele (254)
#: ficava mais clara que o fundo (246), ou seja nao havia silhueta pra mascara
#: achar. Quem faz isso no motor e a `palette`: ela amostra a cor da fonte no
#: centro da sonda de cada glifo e pinta com a tinta do stop mais proximo.
#:
#: Os stops saem da propria referencia — o MATIZ e dela, nao meu. O que eu
#: escolho e so a rampa de valor da tinta, entre PALETA_ESCURO e PALETA_CLARO.
PALETA_N = 9
#: Um glifo nao preenche a celula dele — a 3 mm ele cobre cerca de um terco.
#: Entao pintar a tinta no valor que se quer VER deixa a peca duas vezes mais
#: clara do que o mapa de tom pedia, que e o que estava acontecendo: o mapa lia
#: o casal inteiro e o papel comia dois tercos. A tinta e o inverso da
#: cobertura: pra a celula aparentar V, a tinta tem que ser
#: 255 - (255-V)/COBERTURA. Onde isso passa do preto, e preto e pronto.
COBERTURA = 0.42

#: A paisagem do Rio no fundo dela sai mais clara que o casal, a pedido do
#: Gustavo ("mais claro a paisagem no fundo so. Neles esta bom").
#:
#: Tom sozinho nao separa os dois: a paisagem mede 208-228 e os meios-tons do
#: casal 159-222 — se cruzam. Entao a separacao e ESPACIAL, por densidade
#: local: o casal e uma mancha grande de tinta junta, a paisagem e traco solto e
#: esparso. Media numa janela de FUNDO_JANELA px; o que passa do limiar e casal,
#: e a borda sai borrada pra nao existir recorte visivel.
#: Medido na referencia com media local: o casal denso da 205-217, a agua da
#: esquerda 238, a montanha 245, a palmeira 245, o papel 254. O limiar antigo
#: (244) pegava montanha e agua junto com o casal — era por isso que o lado da
#: Jane continuava escuro. 232 fica no meio do vao de 217 a 238 e separa limpo.
FUNDO_JANELA, FUNDO_LIMIAR = 21, 232
FUNDO_FORCA = 0.35          # 0 = fundo some, 1 = fundo como estava
FUNDO_BORDA = 14            # px de transicao entre casal e fundo
#: A malha cobre a caixa de arte inteira, entao o fundo claro terminava numa
#: borda reta e a peca ficava com um retangulo levissimo desenhado nela. A
#: rampa desvanece o FUNDO nos ultimos BORDA_CM, e so o fundo: o casal encosta
#: na borda de cima (o cabelo dele) e continua encostando.
BORDA_CM = 2.6
PALETA_PAPEL = 252     # acima disto e papel e nao entra na conta das bandas

# ---- malha ----------------------------------------------------------------- #
FAM_MALHA = "Arial Narrow"
TINTA = "#2A2422"
#: 2,0 mm, NAO os 3,0-3,7 que ele aprovou na plotagem do `ainda-estou-aqui-teste`.
#: Aquela plotagem media legibilidade da letra, e continua valendo pra isso. O
#: que ela nao media era RESOLUCAO DE ROSTO, e aqui essa e a conta que manda:
#:
#:   corpo    celulas na cara dele    o olho dele
#:   3,0 mm       70 x 67                12 celulas   -> nao ha rosto
#:   2,4 mm       87 x 84                15
#:   2,0 mm      105 x 100               18 celulas   -> o rosto aparece
#:   1,6 mm      131 x 126               23 celulas   -> nitido
#:
#: Nao e ajuste, e falta de amostra: nao se desenha um olho com 12 pontos. A
#: 3,0 mm o contraste da cara caia pra 31% do que o mapa de tom pedia. Medido
#: em export 1:1, nao em preview. A 2,0 as letras seguem legiveis de perto (ver
#: recorte 1:1) e o corpo fica perto dos ~2,5 mm da propria referencia dele.
CORPO_MM = 3.0
#: O ponto da virada. Antes: 1,9 a 6,3 mm (3,3x) — no escuro os glifos se
#: encostavam e a peca virava mancha, que foi a reclamacao dele. A referencia
#: tem corpo quase unico e a sombra sai de densidade, nao de tamanho. 2,4 a 3,75
#: da 1,5x: ainda modela, nao entope.
#: A LETRA E MENOR QUE O VAO DE LINHA, e e isso que faz a peca ler como texto
#: escrito em vez de grao.
#:
#: No motor os dois nascem do mesmo numero: o vao de linha e 0,9 x corpo e o
#: tamanho da letra e uma fracao do corpo. Com os defaults a letra fica com
#: 80-95% da altura do vao, entao linha encosta em linha e o campo vira massa —
#: foi o que aconteceu quando desci o corpo pra 2,0 pra ganhar rosto, e o
#: Gustavo apontou na hora ("ficou pior ainda").
#:
#: Medindo a referencia dele: vao de ~2,5 mm com a tinta ocupando ~40% dele.
#: Aqui: vao de 2,16 mm (0,9 x 2,4) com letra de 1,1 a 1,7 mm, ou seja tinta em
#: ~35-55% do vao. Sobra papel entre as linhas, que e o ar da peca.
#:
#: De brinde, resolucao horizontal: letra menor avanca menos, entao cabem mais
#: por linha e o rosto ganha amostra sem o campo fechar.
SIZE_MIN_RATIO, SIZE_MAX_RATIO = 0.80, 1.25
BOLD_THRESHOLD = 0.72       # quase nada em bold; na referencia nao ha peso

# ---- tipo (display.marks) --------------------------------------------------- #
#: Cambria. Medindo a razao largura/altura da referencia, "meu" da 3,10 e
#: "AMOR" 3,68; nenhuma serifa do Windows chega la (sao todas mais largas), e a
#: Cambria e a que menos erra no caixa alta (3,97) sem perder a leitura.
FAM_TIPO = "Cambria"
COR_TIPO = "#5C5A5A"        # medido nos blocos de tipo dela
#: (texto, x0, y0, x1) em fracao da REFERENCIA. x1 fecha a largura do bloco, e
#: e dela que sai o corpo — o desenho manda no tamanho, nao o contrario.
BLOCOS = [
    ("como\né grande", 0.063, 0.224, 0.362),
    ("o\nmeu",         0.073, 0.805, 0.272),
    ("AMOR",           0.245, 0.775, 0.790),
    ("por você",       0.540, 0.898, 0.808),
]

TEXT_BLOCKS = {
    "title_size_mm": 24, "title_y_mm": 14,
    "subtitle_size_mm": 4.6, "subtitle_dy_mm": 30,
    "squares_dy_mm": 40, "square_size_mm": 3.4, "square_gap_mm": 7.4,
    "footer_size_mm": 5.0, "footer_dy_mm": 22,
    "frame": False, "accent_squares": True,
}
TITULO = "JANE E GILBER"
SUBTITULO = "COMO É GRANDE O MEU AMOR POR VOCÊ · ROBERTO CARLOS · 1967"
RODAPE = "EXPERIMENTO TIPOGRÁFICO — GUSTAVO JANNUZZI"


# --------------------------------------------------------------------------- #
def achata_papel(lum: np.ndarray) -> np.ndarray:
    """Papel -> 255, sem tocar nas massas de tom. Ponto de branco LOCAL.

    O percentil roda em escala reduzida: o mapa de branco e liso por construcao
    e a janela em tamanho cheio estoura a memoria.
    """
    p = max(3, PAPEL_JANELA // (2 * PAPEL_ESCALA) * 2 + 1)
    peq = np.asarray(Image.fromarray(lum.astype(np.uint8), "L").resize(
        (lum.shape[1] // PAPEL_ESCALA, lum.shape[0] // PAPEL_ESCALA),
        Image.BILINEAR)).astype(np.float32)
    branco = ndi.gaussian_filter(ndi.percentile_filter(peq, PAPEL_PCT, size=p), 5.0)
    branco = np.asarray(Image.fromarray(branco.round().astype(np.uint8), "L").resize(
        (lum.shape[1], lum.shape[0]), Image.BICUBIC)).astype(np.float32)
    return np.clip(lum / np.maximum(branco, 1.0) * 255.0, 0, 255)


def paleta(rgb: np.ndarray) -> list[tuple[str, str]]:
    """Stops (cor_na_fonte -> cor_da_tinta) tirados da propria referencia.

    Quantiza o mapa de tom JA borrado — tem que ser o borrado, porque e nele
    que a `palette` vai amostrar. Cada cor da referencia vira tinta com o mesmo
    matiz, so que afastada do papel por `PALETA_GANHO`, o bastante pra existir
    no papel sem virar o preto chapado que ele reclamou.
    """
    lum = 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]
    # Quantizar a imagem inteira nao serve: ela e quase toda papel, e o
    # MEDIANCUT gastava 9 dos 10 stops em tons de branco. Aqui as bandas saem
    # por PERCENTIL da tinta, entao cada stop cobre a mesma quantidade de peca.
    tinta_px = lum < PALETA_PAPEL
    cortes = np.percentile(lum[tinta_px], np.linspace(0, 100, PALETA_N + 1))
    stops = []
    for i in range(PALETA_N):
        faixa = tinta_px & (lum >= cortes[i]) & (lum <= cortes[i + 1])
        if faixa.sum() < 50:
            continue
        c = rgb[faixa].mean(0)
        # A tinta NAO e a cor da fonte multiplicada: e uma rampa uniforme de
        # valor, com o matiz da fonte preservado. Multiplicar a distancia ao
        # branco deixava a peca lavada — a referencia e clara, entao 8 das 9
        # bandas caiam entre 230 e 250 e nada aparecia. Aqui a banda mais escura
        # cai em PALETA_ESCURO e a mais clara em PALETA_CLARO, e no meio a
        # rampa e reta: cada banda cobre a mesma area da peca e um degrau igual
        # de tinta.
        # A tinta e funcao do TOM, nao do ranking da banda. Distribuir os
        # niveis por igual populacao (i / N) e equalizacao de histograma — por
        # definicao achata a imagem, e foi exatamente o que aconteceu: o mapa de
        # tom lia o casal inteiro e o render saia lavado. Aqui a banda clara sai
        # clara e a escura sai escura, na mesma proporcao que tinham na fonte.
        lc0 = 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]
        alvo = max(0.0, 255.0 - (255.0 - lc0) / COBERTURA)
        t = np.clip(c * (alvo / max(lc0, 1.0)), 0, 255)
        stops.append(("#%02X%02X%02X" % tuple(int(round(v)) for v in c),
                      "#%02X%02X%02X" % tuple(int(round(v)) for v in t)))
    stops.append(("#FFFFFF", "#FFFFFF"))          # o papel, explicito
    return stops


def mascara_do_tipo(rgb: np.ndarray) -> np.ndarray:
    """Os blocos de tipo da referencia, pra sairem e serem reescritos por
    `display.marks` em tipo de verdade.

    A ARMADILHA, que custou tres tentativas. "Escuro e neutro" nao distingue
    letra de desenho: o cabelo do Gilber tambem e escuro e neutro, e o "e" de
    "grande" ENCOSTA nele. Toda peneira por cor vaza da letra pro cabelo, e foi
    isso que abriu o buraco na testa dele — o retangulo que sobrava era a
    inundacao batendo na borda da minha caixa.

    O que resolve nao e uma peneira melhor, e o LUGAR: `TIPO_LINHAS` sao as
    caixas de tinta MEDIDAS na referencia, uma por linha de texto. Elas param em
    x=399 (o "é grande") e a bochecha dele comeca depois — nenhuma peneira
    precisa acertar, porque o desenho dele nao esta dentro da area de busca.

    Tentei antes a silhueta do tipo NOVO desenhada em Cambria: nao serve, a
    fonte dela e outra e as duas nao caem no mesmo lugar glifo a glifo. Medida
    da referencia bate; reconstruida da minha fonte, nao.
    """
    a = rgb.astype(np.float32)
    lum = 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]
    sat = (a.max(2) - a.min(2)) / np.maximum(a.max(2), 1.0)
    dentro = np.zeros(lum.shape, bool)
    for x0, y0, x1, y1 in TIPO_LINHAS:
        dentro[y0:y1, x0:x1] = True
    neutro = sat < TIPO_SAT
    corpo = (lum < TIPO_CORPO) & neutro & dentro
    m = (lum < TIPO_NUCLEO) & neutro & dentro
    for _ in range(TIPO_CRESCE):          # crescimento LIMITADO; propagacao sem
        m = ndi.binary_dilation(m, np.ones((3, 3))) & corpo   # limite atravessa
    print(f"  blocos de tipo: {m.sum()} px em {len(TIPO_LINHAS)} linhas")
    return ndi.binary_dilation(m, np.ones((3, 3)), iterations=TIPO_FOLGA)


def mascara_do_amor(lum: np.ndarray) -> np.ndarray:
    """O "AMOR" fantasma, que na referencia e letrinha adensada.

    Nao tem cor propria — o que o separa da malha em volta e a DENSIDADE. Media
    numa janela do tamanho de uma letra: onde ela cai abaixo do limiar, e traco
    de palavra e nao textura. Restrito a caixa onde a palavra mora, entao a
    sombra do cabelo dela (que tambem e densa) nao entra na conta.
    """
    x0, y0, x1, y1 = AMOR_CAIXA
    dens = ndi.uniform_filter(lum, AMOR_JANELA)
    m = np.zeros(lum.shape, bool)
    m[y0:y1, x0:x1] = dens[y0:y1, x0:x1] < AMOR_LIMIAR
    m = ndi.binary_closing(m, np.ones((5, 5)))
    print(f"  fantasma do AMOR: {m.sum()} px")
    return ndi.binary_dilation(m, np.ones((3, 3)), iterations=3)


def mascara_do_casal(lum: np.ndarray) -> np.ndarray:
    """O casal, separado da paisagem por DENSIDADE e nao por tom.

    Os dois se cruzam em luminancia; o que os separa e que o casal e mancha
    grande e continua de tinta e a paisagem e traco solto. Media local, maior
    componente, buracos preenchidos.
    """
    dens = ndi.uniform_filter(lum, FUNDO_JANELA)
    m = ndi.binary_closing(dens < FUNDO_LIMIAR, np.ones((9, 9)))
    lab, n = ndi.label(m)
    if n:
        sz = ndi.sum(m, lab, range(1, n + 1))
        m = lab == (int(np.argmax(sz)) + 1)
    # preenche buraco antes de dilatar: a testa e a bochecha dele sao quase
    # brancas e ficariam de fora do casal, indo clarear junto com a paisagem.
    m = ndi.binary_dilation(ndi.binary_fill_holes(m), np.ones((3, 3)), iterations=4)
    print(f"  casal: {m.sum()/m.size*100:.0f}% da referencia")
    return m


def extrai_arte() -> np.ndarray:
    """A referencia limpa, EM COR: sem os blocos de tipo, sem o fantasma do
    AMOR, com o papel achatado. Em cor porque e a `palette` que le isto."""
    rgb = np.asarray(Image.open(REF).convert("RGB")).astype(np.float32)
    lum = 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]

    fora = mascara_do_tipo(rgb) | mascara_do_amor(lum)
    # reconstroi por vizinho: apagar pra branco abriria buraco com a forma das
    # letras antigas, e o tipo novo tem outra fonte e outra largura.
    _, ind = ndi.distance_transform_edt(fora, return_indices=True)
    for c in range(3):
        rgb[..., c][fora] = rgb[..., c][ind[0][fora], ind[1][fora]]

    lum = 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]
    casal = ndi.gaussian_filter(
        mascara_do_casal(lum).astype(np.float32), FUNDO_BORDA)
    forca = casal + (1.0 - casal) * FUNDO_FORCA        # 1 nele, FUNDO_FORCA fora

    h, w = lum.shape
    b = max(1.0, BORDA_CM / ARTE_W * w)
    yy, xx = np.mgrid[0:h, 0:w]
    rampa = np.clip(np.minimum.reduce([xx, w - 1 - xx, yy, h - 1 - yy]) / b, 0, 1)
    forca *= np.maximum(casal, rampa)                  # a borda nao toca no casal
    return np.clip(255.0 - (255.0 - rgb) * forca[..., None], 0, 255)


def _corpo_cm(texto: str, larg_cm: float) -> float:
    """Corpo em cm que faz a linha mais larga do bloco medir `larg_cm` de tinta."""
    par = resolve_family(FAM_TIPO)
    linhas = texto.split("\n")
    lo, hi = 0.2, 40.0
    for _ in range(44):
        mid = (lo + hi) / 2
        f = load_font(par.regular, max(4, int(mid / 2.54 * DPI)))
        larg = max(f.getbbox(l)[2] - f.getbbox(l)[0] for l in linhas) / DPI * 2.54
        lo, hi = (mid, hi) if larg <= larg_cm else (lo, mid)
    return round(lo, 2)


def marks() -> list[dict]:
    """Os quatro blocos, em cm de pagina.

    `display.marks` mede da borda da PAGINA, nao da caixa de arte — somar
    ARTE_X/ARTE_Y nao e detalhe, e a diferenca entre o bloco cair no lugar e
    cair 4,6 cm fora.
    """
    saida = []
    for texto, fx, fy, fx1 in BLOCOS:
        larg = (fx1 - fx) * ARTE_W
        corpo = _corpo_cm(texto, larg)
        saida.append({
            "text": texto,
            "size_cm": corpo,
            "x_cm": round(ARTE_X + fx * ARTE_W, 2),
            "y_cm": round(ARTE_Y + fy * ARTE_H, 2),
            "anchor": "lt",
            "family": FAM_TIPO,
            "weight": "regular",
            "color": COR_TIPO,
            "layer": "over",
            "leading": 1.18,
        })
        print(f"  '{texto.replace(chr(10), ' / ')}': corpo {corpo} cm, "
              f"{larg:.1f} cm de largura, em ({saida[-1]['x_cm']},{saida[-1]['y_cm']}) cm")
    return saida


def monta(destino: Path) -> None:
    rgb = extrai_arte()
    alvo_w = int(round(ARTE_W / 2.54 * DPI))
    alvo_h = int(round(ARTE_H / 2.54 * DPI))
    print(f"  upscale {rgb.shape[1]}->{alvo_w} px ({alvo_w/rgb.shape[1]:.2f}x)")

    # DESFAZER O HALFTONE DELA: media exata por CELULA do motor, nao borrao.
    #
    # A celula a 3 mm tem 17,7 px, entao a peca inteira e uma imagem de 167x217
    # amostras — e so isso que o motor vai ler. Reduzir por BOX ate esse tamanho
    # e a media de area exata: nao existe frequencia acima da amostragem, entao
    # nao existe moire, e nada se perde que o motor pudesse ter desenhado.
    # Gaussiana era chute; isto e a conta.
    cel = CORPO_MM / 25.4 * DPI
    nx, ny = int(round(alvo_w / cel)), int(round(alvo_h / cel))
    g = Image.fromarray(rgb.round().astype(np.uint8), "RGB").resize((nx, ny), Image.BOX)
    print(f"  o motor ve {nx} x {ny} celulas de {CORPO_MM} mm")

    # e SO agora estica. A referencia e clara — util de 136 a 255 — e sem
    # esticar o casal sai lavado. Estica na luminancia, preservando o matiz:
    # esticar por canal deslocaria a cor das bandas claras pro cinza.
    a = np.asarray(g).astype(np.float32)
    lum = 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]
    lo, hi = np.percentile(lum, ESTICA_PCT)
    novo = np.clip((lum - lo) / (hi - lo), 0, 1) * 255.0
    a = np.clip(a * (novo / np.maximum(lum, 1.0))[..., None], 0, 255)
    print(f"  estica: {lo:.0f}-{hi:.0f} -> 0-255")

    # NEAREST, nao BILINEAR. Sao 167x217 celulas viradas em 2962x3844 px — uma
    # ampliacao de 17,7x por eixo. Interpolar cria degrade entre celula vizinha
    # e o motor, que amostra um ponto por glifo, herda esse degrade: o cabelo do
    # Gilber virava lavagem sem fio nem silhueta, que foi o "borrado" que ele
    # apontou. Com NEAREST cada celula e um bloco chapado, e o glifo pega
    # exatamente a media daquela celula — que e o que ele deveria pegar.
    g = Image.fromarray(a.round().astype(np.uint8), "RGB").resize(
        (alvo_w, alvo_h), Image.NEAREST)
    stops = paleta(np.asarray(g))

    tela = Image.new("RGB", (CANVAS_W, CANVAS_H), (255, 255, 255))
    tela.paste(g, (int(round((ARTE_X - MARGEM["side"]) / 2.54 * DPI)), 0))

    (destino / "refs").mkdir(parents=True, exist_ok=True)
    (destino / "text").mkdir(parents=True, exist_ok=True)
    (destino / "text/como-e-grande.txt").write_text(LETRA.read_text("utf-8"), "utf-8")
    tela.save(destino / "refs/arte-ref.png")

    doc = {
        "name": destino.name,
        "source": {"image": "refs/arte-ref.png", "crop": [0, 0, CANVAS_W, CANVAS_H]},
        "text": {"file": "text/como-e-grande.txt", "mode": "phrases"},
        "page": {"mode": "fixed", "width_cm": PAG_W, "height_cm": PAG_H,
                 "margins_cm": dict(MARGEM), "dpi_export": DPI,
                 "preview_max_px": 1600},
        # Ficha conferida em 05/08/2026 em duas fontes independentes
        # (pt.wikipedia, faixas do album; letras.mus.br): so Roberto Carlos, 1967.
        "titles": {"title": TITULO, "subtitle": SUBTITULO,
                   "footer": RODAPE, "draw": True},
        # Mascara DESLIGADA de proposito. Nesta referencia nao ha silhueta pra
        # ela achar: a testa dele mede 254 e o fundo 246, ou seja o rosto e mais
        # CLARO que o fundo. Quem separa figura de papel aqui e a paleta — o
        # fundo cai no stop quase-papel e some sozinho.
        "mask": {"enabled": False},
        "landscape": {"enabled": False},
        "accent": {"enabled": False},
        # value_weight 1.0, nao o default 0.25. O default comprime o eixo de
        # brilho pra que as bordas anti-serrilhadas de arte COLORIDA nao
        # sorteiem matiz (ver `palette.py` e `projects/turnstile`). Aqui a
        # paleta E uma rampa de brilho e os matizes sao quase iguais: com 0,25
        # o casamento virava sorteio e a peca saia toda no mesmo cinza.
        "palette": {"enabled": True, "stops": stops, "value_weight": 1.0},
        "display": {"enabled": True, "family": FAM_TIPO, "marks": marks()},
        "style_preset": "magalenha",
        "style_overrides": {
            "colors": {"ink": TINTA},
            "font": {"family": FAM_MALHA, "base_line_mm": CORPO_MM,
                     "size_min_mm": round(CORPO_MM * SIZE_MIN_RATIO, 2),
                     "size_max_ratio": SIZE_MAX_RATIO,
                     "size_gamma": 1.0, "bold_threshold": BOLD_THRESHOLD},
            "flow": {"flex": 0.0},
            "text_blocks": dict(TEXT_BLOCKS),
        },
    }
    (destino / "project.yaml").write_text(
        yaml.safe_dump(doc, allow_unicode=True, sort_keys=False), "utf-8")
    print(f"  -> {destino/'project.yaml'}")


def exporta(destino: Path) -> None:
    """Render de export + PDF, com o numero da versao no nome do arquivo."""
    from typo.config import RenderConfig
    from typo import engine, export as export_mod
    cfg = RenderConfig.from_project(destino / "project.yaml")
    cfg.validate()
    r = engine.render_result(cfg, "export")
    print("  " + r.summary())
    saida = destino / "output"
    saida.mkdir(parents=True, exist_ok=True)
    base = f"vovo_jane_arte_v{VERSAO}_59x84cm_150dpi"
    paths = export_mod.save(r, saida, name=destino.name, basename=base)
    reg = saida / "VERSOES.md"
    linha = f"- **v{VERSAO}** — {NOTA}\n"
    txt = reg.read_text("utf-8") if reg.exists() else "# Versoes da peca\n\n"
    if f"- **v{VERSAO}**" not in txt:
        reg.write_text(txt + linha, "utf-8")
    print(f"  -> {paths.pdf}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--render", action="store_true",
                    help="ja gera o PNG e o PDF versionados depois de montar")
    a = ap.parse_args()
    monta(DESTINO)
    if a.render:
        exporta(DESTINO)
