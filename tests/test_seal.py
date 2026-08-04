"""Selo tipografico: o QR desenhado com letras ainda le?

O teste que importa e' de VOLTA: renderiza o selo e manda um decodificador
independente (`zxing-cpp`, linhagem da implementacao de referencia) ler o que
saiu. Comparar a matriz que desenhei com a matriz que gerei seria tautologia —
provaria que sei copiar um array, nao que um celular le o papel.

**Contra um controle.** Em cada degradacao o selo e' comparado com um QR LISO do
mesmo payload, no mesmo tamanho. Assim o teste mede o custo da estilizacao, e
nao o limite do decodificador: se nem o controle le a 120px, o selo falhar ali
nao diz nada sobre as letras.

O que este arquivo NAO cobre, e nenhum teste automatico cobre: ler com o celular,
impresso, de longe e de perto. Isso e' do Gustavo. Aqui esta' a condicao
necessaria — a suficiente sai no papel.
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fixtures import make_text_file  # noqa: E402

from typo import seal  # noqa: E402

segno = pytest.importorskip("segno", reason='pip install -e ".[seal]"')
zxingcpp = pytest.importorskip("zxingcpp", reason='pip install -e ".[dev]"')

PAYLOAD = "HTTPS://ONDEMORAMASPALAVRAS.COM/S/7QK4M2"


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def decode(img: Image.Image) -> str | None:
    """Texto lido, ou None. Aceita PIL direto."""
    result = zxingcpp.read_barcode(img.convert("L"))
    if result is None or not result.valid:
        return None
    return result.text


def control(px: int) -> Image.Image:
    """QR liso do mesmo payload, no mesmo tamanho — a linha de base."""
    buf = io.BytesIO()
    qr = segno.make_qr(PAYLOAD, error="h")  # make_qr: nunca Micro QR, ver seal.py
    qr.save(buf, kind="png", scale=10, border=4, dark="#111111", light="#FFFFFF")
    buf.seek(0)
    return Image.open(buf).convert("RGB").resize((px, px), Image.LANCZOS)


@pytest.fixture(scope="module")
def text_file(tmp_path_factory) -> str:
    return str(make_text_file(tmp_path_factory.mktemp("seal") / "letra.txt"))


@pytest.fixture(scope="module")
def spec(text_file) -> seal.SealSpec:
    return seal.SealSpec(payload=PAYLOAD, text_path=text_file)


@pytest.fixture(scope="module")
def result(spec) -> seal.SealResult:
    return seal.render(spec)


# --------------------------------------------------------------------------- #
# leitura de volta
# --------------------------------------------------------------------------- #
def test_seal_decodes_back(result):
    """O basico: o selo em resolucao nativa le, e le o payload certo."""
    assert decode(result.image) == PAYLOAD


@pytest.mark.parametrize("px", [1200, 800, 600, 400, 300, 200])
def test_seal_decodes_at_distance(result, px):
    """Reduzir a imagem imita afastar o celular.

    So' exige do selo o que o QR liso entrega no mesmo tamanho.
    """
    if decode(control(px)) != PAYLOAD:
        pytest.skip(f"nem o QR liso le a {px}px — limite do decodificador")
    small = result.image.resize((px, px), Image.LANCZOS)
    assert decode(small) == PAYLOAD, f"o selo nao leu a {px}px e o liso leu"


@pytest.mark.parametrize("radius", [0.8, 1.6, 2.4])
def test_seal_survives_blur(result, radius):
    """Foco imperfeito de camera de mao."""
    img = result.image.resize((800, 800), Image.LANCZOS).filter(
        ImageFilter.GaussianBlur(radius)
    )
    if decode(control(800).filter(ImageFilter.GaussianBlur(radius))) != PAYLOAD:
        pytest.skip(f"nem o QR liso le com blur {radius}")
    assert decode(img) == PAYLOAD


@pytest.mark.parametrize("angle", [5, 15, 45, 90])
def test_seal_survives_rotation(result, angle):
    """Celular torto. 90 graus e' de graca, 15 e' o caso real."""
    img = result.image.resize((800, 800), Image.LANCZOS).rotate(
        angle, expand=True, resample=Image.BICUBIC, fillcolor=(255, 255, 255)
    )
    assert decode(img) == PAYLOAD


def test_seal_survives_jpeg(result):
    """Compressao de app de mensagem, que e' como o selo costuma circular."""
    img = result.image.resize((800, 800), Image.LANCZOS)
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=40)
    buf.seek(0)
    assert decode(Image.open(buf)) == PAYLOAD


def test_seal_survives_inverted_contrast(result):
    """Foto de tela com brilho baixo: menos contraste, nao menos resolucao."""
    arr = np.asarray(result.image.resize((800, 800), Image.LANCZOS), dtype=float)
    washed = (arr * 0.55 + 100).clip(0, 255).astype(np.uint8)
    assert decode(Image.fromarray(washed)) == PAYLOAD


# --------------------------------------------------------------------------- #
# a grade (independente do decodificador)
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def pixels(result) -> np.ndarray:
    """A imagem como array uma vez so': sao ~1000 consultas de modulo por teste."""
    return np.asarray(result.image)


@pytest.fixture(scope="module")
def matrix(spec) -> list[list[int]]:
    qr = segno.make_qr(spec.payload, error=spec.ecc)
    return [list(r) for r in qr.matrix_iter(scale=1, border=0, verbose=True)]


def module_block(pixels, result: seal.SealResult, mx: int, my: int, quiet: int = 4):
    """O bloco de pixels de um modulo, em coordenadas de codigo."""
    m = result.module_px
    x0 = (quiet + mx) * m
    y0 = (quiet + my) * m
    return pixels[y0 : y0 + m, x0 : x0 + m]


def test_no_glyph_crosses_a_module_boundary(result, spec, pixels, matrix):
    """A garantia central: nenhum modulo CLARO tem um pingo de tinta.

    Se um glifo vazasse da celula dele, ele sujaria o vizinho — e o vizinho
    claro e' onde isso apareceria. Testar o modulo claro e' testar o clipe sem
    precisar acreditar nele.
    """
    dark_types, _, _ = seal._type_sets()
    sujos = []
    for my, row in enumerate(matrix):
        for mx, kind in enumerate(row):
            if kind in dark_types:
                continue
            block = module_block(pixels, result, mx, my, spec.quiet_modules)
            if block.min() < 250:  # fundo e' #FFFFFF
                sujos.append((mx, my, int(block.min())))
    assert not sujos, f"{len(sujos)} modulos claros com tinta: {sujos[:5]}"


def test_quiet_zone_is_clean(result, spec):
    """4 modulos de papel em volta, sem excecao."""
    arr = np.asarray(result.image)
    q = spec.quiet_modules * result.module_px
    for name, band in (
        ("topo", arr[:q, :]),
        ("base", arr[-q:, :]),
        ("esquerda", arr[:, :q]),
        ("direita", arr[:, -q:]),
    ):
        assert band.min() >= 250, f"quiet zone suja em {name}"


def test_function_patterns_are_solid(result, spec, pixels, matrix):
    """Finder, timing, alignment e format saem chapados, nunca tipografados."""
    dark_types, data_types, _ = seal._type_sets()
    _, consts = seal._segno()
    vistos = set()
    for my, row in enumerate(matrix):
        for mx, kind in enumerate(row):
            if kind not in dark_types or kind in data_types:
                continue
            block = module_block(pixels, result, mx, my, spec.quiet_modules)
            assert block.max() <= 20, (
                f"modulo de funcao ({mx},{my}) tipo {kind} nao esta solido "
                f"(max={block.max()})"
            )
            vistos.add(kind)

    # o que importa nao e' a contagem (que muda com a versao do QR) e sim que
    # NENHUMA categoria protegida ficou de fora da classificacao
    esperadas = {
        "finder": consts.TYPE_FINDER_PATTERN_DARK,
        "timing": consts.TYPE_TIMING_DARK,
        "alignment": consts.TYPE_ALIGNMENT_PATTERN_DARK,
        "format": consts.TYPE_FORMAT_DARK,
        "darkmodule": consts.TYPE_DARKMODULE,
    }
    faltando = [nome for nome, tipo in esperadas.items() if tipo not in vistos]
    assert not faltando, f"categoria protegida ausente do selo: {faltando}"


def test_dark_data_modules_have_ink_at_the_centre(result, spec, pixels, matrix):
    """O ponto que o decodificador amostra esta' escuro em todo modulo escuro.

    A janela e' o RAIO DO NUCLEO, nao um pedaco arbitrario do modulo. O
    decodificador amostra o centro do modulo (um ponto, com meio pixel de
    folga); o nucleo e' um disco desse raio ali. Medir mais largo que o nucleo
    seria testar outra coisa — "o quarto central e' majoritariamente escuro" —
    que o desenho nao garante de proposito: letra redonda deixa papel logo fora
    do nucleo, e e' justamente isso que mantem o 'o' legivel como 'o'.
    """
    _, consts = seal._segno()
    m = result.module_px
    raio = max(1, int(m * spec.core_ratio / 2))
    lo, hi = m // 2 - raio, m // 2 + raio
    claros = 0
    total = 0
    for my, row in enumerate(matrix):
        for mx, kind in enumerate(row):
            if kind != consts.TYPE_DATA_DARK:
                continue
            total += 1
            centro = module_block(pixels, result, mx, my, spec.quiet_modules)[lo:hi, lo:hi]
            if centro.mean() > 128:
                claros += 1
    assert total > 300
    assert claros == 0, f"{claros}/{total} modulos escuros com centro claro"


# --------------------------------------------------------------------------- #
# geometria e texto
# --------------------------------------------------------------------------- #
def test_physical_size_is_reported_not_promised(spec):
    """O modulo e' pixel inteiro; o tamanho real sai disso e e' o que se diz."""
    r = seal.render(spec)
    total = r.modules + 2 * spec.quiet_modules
    assert r.image.size == (total * r.module_px, total * r.module_px)
    assert r.size_cm == pytest.approx(total * r.module_px / spec.dpi * 2.54)
    # o alvo era 7 cm: o arredondamento nao pode custar mais que meio modulo
    assert abs(r.size_cm - spec.size_cm) <= r.module_mm / 10


def test_uppercase_payload_uses_alphanumeric_mode(spec):
    """A URL em maiuscula cai em modo alfanumerico e economiza modulos."""
    alto = seal.render(spec)
    baixo = seal.render(
        seal.SealSpec(
            payload="https://ondemoramaspalavras.com/selo/7qk4m2",
            text_path=spec.text_path,
        )
    )
    assert alto.mode == "alphanumeric"
    assert baixo.mode == "byte"
    assert alto.modules < baixo.modules
    assert alto.module_mm > baixo.module_mm  # menos modulos = letra maior


def test_letters_come_from_the_work_text(result, text_file):
    """As letras do selo sao as da obra, em ordem (pulos permitidos)."""
    from typo import text_source
    from typo.config import TextCfg

    fonte = "".join(
        text_source.build_stream_cached(TextCfg(text_path=text_file, mode="chars", repeat=1))
    )
    assert result.letters > 300
    assert len(result.text) == result.letters

    # o stream cicla quando o texto e' menor que o numero de modulos (aqui a
    # letra da fixture da' ~100 caracteres para ~380 modulos), entao a fonte de
    # comparacao e' o texto repetido — a ORDEM e' que esta sob teste
    voltas = len(result.text) // max(1, len(fonte)) + 2
    ciclado = fonte * voltas
    i = 0
    for ch in result.text:
        i = ciclado.find(ch, i)
        assert i >= 0, f"{ch!r} nao veio do texto da obra"
        i += 1


def test_protect_format_frees_modules_for_letters(spec):
    """Desligar a protecao do format info troca solido por letra."""
    protegido = seal.render(spec)
    solto = seal.render(
        seal.SealSpec(
            payload=spec.payload, text_path=spec.text_path, protect_format=False
        )
    )
    assert solto.solid < protegido.solid
    assert solto.letters > protegido.letters
    # e continua legivel — que e' o ponto de oferecer a chave
    assert decode(solto.image) == PAYLOAD


def test_default_core_is_at_or_above_the_measured_floor():
    """0.18 e' o menor nucleo que empata com o QR liso; abaixo disso o selo cai.

    Medido, nao estimado — a varredura esta' na docstring de `SealSpec`. Este
    teste existe para que baixar o default (o que e' tentador, porque o nucleo
    e' a unica coisa que "suja" a letra) falhe alto em vez de virar um selo
    bonito que so' nao escaneia no papel.
    """
    assert seal.SealSpec.core_ratio >= 0.18


def test_seal_refuses_a_quiet_zone_below_spec(spec):
    with pytest.raises(seal.SealError, match="zona silenciosa"):
        seal.render(
            seal.SealSpec(
                payload=spec.payload, text_path=spec.text_path, quiet_modules=2
            )
        )
