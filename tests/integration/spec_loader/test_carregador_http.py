"""Carregador de spec: download, leitura e validação (ADR-007, RN-02)."""

import json

import httpx
import pytest
import respx

from app.adapters.outbound.spec_loader.carregador_http import CarregadorDeSpecHttp
from app.application.portas import SpecInvalida

pytestmark = pytest.mark.integration

URL = "http://specs.exemplo/openapi.yaml"
SPEC_YAML = b"""
openapi: "3.1.0"
info: {title: Exemplo, version: "1"}
paths:
  /itens:
    get:
      responses:
        200:
          description: ok
"""


@pytest.fixture
def carregador() -> CarregadorDeSpecHttp:
    return CarregadorDeSpecHttp(timeout_s=2.0)


def test_us02_c3_spec_valida_da_api_alvo_e_baixada_e_aceita(
    api_alvo: str, carregador: CarregadorDeSpecHttp
) -> None:
    spec = carregador.baixar(f"{api_alvo}/openapi.json")

    assert spec == httpx.get(f"{api_alvo}/openapi.json").json()
    caminhos = spec["paths"]
    assert isinstance(caminhos, dict) and "/tarefas/{id}" in caminhos


def test_us02_c3_spec_yaml_e_convertida_para_json(carregador: CarregadorDeSpecHttp) -> None:
    spec = carregador.ler(SPEC_YAML)

    # `200:` sem aspas é int no YAML. Na spec convertida, vira texto, como no JSON.
    assert spec["paths"] == {"/itens": {"get": {"responses": {"200": {"description": "ok"}}}}}
    assert json.loads(json.dumps(spec)) == spec


@pytest.mark.parametrize(
    ("resposta", "motivo"),
    [
        (httpx.Response(404), f"{URL} respondeu 404"),
        (httpx.Response(500), f"{URL} respondeu 500"),
        (httpx.ConnectError("Connection refused"), "Connection refused"),
        (httpx.ReadTimeout("timed out"), "timed out"),
    ],
    ids=["404", "500", "conexao-recusada", "tempo-esgotado"],
)
def test_us04_c5_falha_no_download_levanta_spec_invalida_com_o_motivo(
    carregador: CarregadorDeSpecHttp, resposta: httpx.Response | Exception, motivo: str
) -> None:
    with respx.mock:
        respx.get(URL).mock(side_effect=[resposta])
        with pytest.raises(SpecInvalida, match="Falha ao baixar a spec") as erro:
            carregador.baixar(URL)

    assert motivo in str(erro.value)


def test_us04_c5_url_invalida_levanta_spec_invalida(carregador: CarregadorDeSpecHttp) -> None:
    with pytest.raises(SpecInvalida, match="Falha ao baixar a spec de ftp://"):
        carregador.baixar("ftp://specs.exemplo/openapi.yaml")


@pytest.mark.parametrize(
    ("conteudo", "motivo"),
    [
        (b"\xff\xfe\x00", "não é texto UTF-8"),
        (b"a: [1, 2\n", "não é JSON nem YAML"),
        (b"- 1\n- 2\n", "não é um objeto JSON ou YAML"),
        (b'{"titulo": "sem openapi"}', "versão OpenAPI não identificada"),
        (
            b'{"openapi": "3.1.0", "paths": {}}',
            'Spec inválida em raiz: "info" is a required property',
        ),
        (
            SPEC_YAML.replace(b"description: ok", b"$ref: '#/components/responses/Nada'"),
            "referência não encontrada: /components/responses/Nada",
        ),
    ],
    ids=["binario", "yaml-quebrado", "lista", "sem-versao", "sem-info", "ref-quebrado"],
)
def test_us02_c2_conteudo_invalido_levanta_spec_invalida_com_o_motivo(
    carregador: CarregadorDeSpecHttp, conteudo: bytes, motivo: str
) -> None:
    with pytest.raises(SpecInvalida, match="Spec inválida") as erro:
        carregador.ler(conteudo)

    assert motivo in str(erro.value)


@pytest.mark.parametrize(
    "paths",
    ["{}", "{/itens: {parameters: [], summary: sem operações}}"],
    ids=["paths-vazio", "path-sem-metodo"],
)
def test_rn02_t1_spec_sem_endpoint_e_invalida(carregador: CarregadorDeSpecHttp, paths: str) -> None:
    conteudo = f'openapi: "3.0.3"\ninfo: {{title: x, version: "1"}}\npaths: {paths}\n'.encode()

    with pytest.raises(SpecInvalida, match="nenhum endpoint declarado"):
        carregador.ler(conteudo)


def test_rn02_t1_spec_baixada_sem_endpoint_e_invalida(carregador: CarregadorDeSpecHttp) -> None:
    # Mesma validação no download (início da run) e no arquivo (cadastro): US02-C5.
    sem_endpoint = b'{"openapi": "3.0.3", "info": {"title": "x", "version": "1"}, "paths": {}}'
    with respx.mock:
        respx.get(URL).mock(return_value=httpx.Response(200, content=sem_endpoint))
        with pytest.raises(SpecInvalida, match="nenhum endpoint declarado"):
            carregador.baixar(URL)
