"""Normalização da spec e hash (ADR-007, RN-13)."""

import hashlib
import json
import random

import pytest
import yaml
from hypothesis import given, settings
from hypothesis import strategies as st

from app.application.portas import SpecInvalida
from app.application.spec_normalizada import calcular_hash, normalizar

pytestmark = pytest.mark.unit

# Valores que cabem em JSON. Sem NaN e infinito, que não existem em JSON.
_escalares = (
    st.none()
    | st.booleans()
    | st.integers()
    | st.floats(allow_nan=False, allow_infinity=False)
    | st.text(max_size=20)
)
_valores = st.recursive(
    _escalares,
    lambda filhos: st.lists(filhos, max_size=4) | st.dictionaries(st.text(max_size=10), filhos),
    max_leaves=20,
)
_specs = st.dictionaries(st.text(max_size=10), _valores, max_size=6)


def _embaralhar(valor: object, sorteio: random.Random) -> object:
    """Mesmo conteúdo, com as chaves de todos os dicts em outra ordem. Listas mantêm a ordem."""
    if isinstance(valor, dict):
        chaves = list(valor)
        sorteio.shuffle(chaves)
        return {chave: _embaralhar(valor[chave], sorteio) for chave in chaves}
    if isinstance(valor, list):
        return [_embaralhar(item, sorteio) for item in valor]
    return valor


@settings(derandomize=True, database=None)
@given(spec=_specs, semente=st.integers(min_value=0, max_value=2**32 - 1))
def test_rn13_t4_mesma_spec_em_yaml_e_json_com_chaves_em_qualquer_ordem_gera_o_mesmo_hash(
    spec: dict[str, object], semente: int
) -> None:
    sorteio = random.Random(semente)
    em_json = json.dumps(_embaralhar(spec, sorteio)).encode()
    em_yaml = yaml.safe_dump(_embaralhar(spec, sorteio), sort_keys=False).encode()

    assert calcular_hash(normalizar(em_json)) == calcular_hash(normalizar(em_yaml))


@pytest.mark.parametrize(
    ("a", "b"),
    [
        ({"openapi": "3.1.0"}, {"openapi": "3.0.3"}),
        ({"paths": ["/a", "/b"]}, {"paths": ["/b", "/a"]}),
        ({"x": 1}, {"x": "1"}),
    ],
)
def test_rn13_t4_conteudo_diferente_gera_hash_diferente(
    a: dict[str, object], b: dict[str, object]
) -> None:
    # Sem este teste, um hash constante passaria no teste de propriedade acima.
    assert calcular_hash(a) != calcular_hash(b)


def test_rn13_t4_hash_e_sha256_do_json_com_chaves_ordenadas() -> None:
    esperado = hashlib.sha256(b'{"a":1,"b":{"c":true}}').hexdigest()

    assert calcular_hash({"b": {"c": True}, "a": 1}) == esperado


def test_rn13_t4_chave_numerica_do_yaml_vira_texto_como_no_json() -> None:
    em_yaml = b"responses:\n  200:\n    description: ok\n"
    em_json = b'{"responses": {"200": {"description": "ok"}}}'

    assert (
        normalizar(em_yaml) == normalizar(em_json) == {"responses": {"200": {"description": "ok"}}}
    )


def test_rn13_t4_numero_com_expoente_em_json_continua_numero() -> None:
    # Achado pelo teste de propriedade: lido como YAML 1.1, 1e+17 viraria o texto "1e+17".
    assert normalizar(b'{"maximum": 1e+17}') == {"maximum": 1e17}


@pytest.mark.parametrize(
    ("conteudo", "motivo"),
    [
        (b"\xff\xfe", "não é texto UTF-8"),
        (b"openapi: [3.1", "não é JSON nem YAML"),
        (b"- uma\n- lista\n", "não é um objeto JSON ou YAML"),
        (b"", "não é um objeto JSON ou YAML"),
    ],
)
def test_us02_c2_conteudo_que_nao_vira_objeto_e_rejeitado_com_motivo(
    conteudo: bytes, motivo: str
) -> None:
    with pytest.raises(SpecInvalida, match=motivo):
        normalizar(conteudo)
