"""`build_payload` — regressao do bug de case-sensitivity.

A primeira versao maiusculizava a URL inteira pra ganhar o modo alfanumerico
do QR. Hospedagem estatica e' case-sensitive: `/CERTIFICADO/` deu 404 de
verdade contra a pasta `certificado/` em disco (confirmado ao vivo em
typo-jet.vercel.app). Este teste existe pra essa regressao nao voltar — nao
maiusculize o path de novo puxando `build_payload` pra fora do texto do
script sem olhar aqui primeiro.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import make_seal  # noqa: E402


def test_payload_path_stays_lowercase_matching_the_dist_folder():
    payload = make_seal.build_payload("https://typo-jet.vercel.app", "XCEXWR")
    assert f"/{make_seal.CERT_PATH}/" in payload
    assert "/CERTIFICADO/" not in payload
    assert make_seal.CERT_PATH == make_seal.CERT_PATH.lower()


def test_payload_code_matches_the_actual_output_folder_casing():
    """dist/certificado/<CODE>/ e' escrito com o codigo tal como o registro
    guarda (maiuscula, ver ALPHABET) — o path precisa bater exato, nao so' em
    case-insensitive-compare, porque em producao nao ha normalizacao."""
    payload = make_seal.build_payload("https://typo-jet.vercel.app", "XCEXWR")
    assert "/XCEXWR/" in payload


def test_payload_ends_with_trailing_slash():
    """Sem a barra final, o navegador do celular sofre um redirect 308 entre
    o scan e a pagina abrir — um passo a mais que pode falhar sem rede."""
    payload = make_seal.build_payload("https://typo-jet.vercel.app", "XCEXWR")
    assert payload.endswith("/")


def test_payload_strips_trailing_slash_from_base_url():
    a = make_seal.build_payload("https://typo-jet.vercel.app", "XCEXWR")
    b = make_seal.build_payload("https://typo-jet.vercel.app/", "XCEXWR")
    assert a == b
