"""Caso de uso de cadastro da API alvo (US-01 e US-02)."""

import pytest

from app.application.cadastrar_api import CadastrarApi
from app.application.portas import CadastroInvalido, SpecInvalida
from app.application.spec_normalizada import calcular_hash
from app.domain.spec_versao import OrigemSpec
from tests.unit.application.fakes import (
    CarregadorDeSpecFalso,
    RelogioFalso,
    RepositorioDeApisFalso,
)

pytestmark = pytest.mark.unit

URL = "http://alvo:8000/openapi.json"
ARQUIVO = b"openapi: 3.1.0"
SPEC: dict[str, object] = {"openapi": "3.1.0", "paths": {"/tarefas": {"get": {}}}}


@pytest.fixture
def apis() -> RepositorioDeApisFalso:
    return RepositorioDeApisFalso()


@pytest.fixture
def carregador() -> CarregadorDeSpecFalso:
    carregador = CarregadorDeSpecFalso()
    carregador.por_url[URL] = SPEC
    carregador.por_arquivo[ARQUIVO] = SPEC
    return carregador


@pytest.fixture
def cadastrar(apis: RepositorioDeApisFalso, carregador: CarregadorDeSpecFalso) -> CadastrarApi:
    return CadastrarApi(apis=apis, carregador=carregador, relogio=RelogioFalso())


def test_us01_c3_cadastro_devolve_a_api_com_identificador(cadastrar: CadastrarApi) -> None:
    api = cadastrar.executar(nome="tarefas", base_url="http://alvo:8000", spec_url=URL)

    assert api.id == 1
    assert (api.nome, api.base_url) == ("tarefas", "http://alvo:8000")


def test_us01_c2_spec_por_url_guarda_a_url_e_a_origem(
    cadastrar: CadastrarApi, apis: RepositorioDeApisFalso
) -> None:
    api = cadastrar.executar(nome="tarefas", base_url="http://alvo:8000", spec_url=URL)

    assert api.spec_url == URL
    assert apis.specs_do_cadastro[1].origem == OrigemSpec.URL


def test_us01_c2_spec_por_arquivo_fica_sem_url_e_com_origem_arquivo(
    cadastrar: CadastrarApi, apis: RepositorioDeApisFalso
) -> None:
    api = cadastrar.executar(nome="tarefas", base_url="http://alvo:8000", spec_arquivo=ARQUIVO)

    assert api.spec_url is None
    assert apis.specs_do_cadastro[1].origem == OrigemSpec.ARQUIVO


def test_us02_c4_spec_valida_e_gravada_com_o_hash_do_conteudo(
    cadastrar: CadastrarApi, apis: RepositorioDeApisFalso
) -> None:
    cadastrar.executar(nome="tarefas", base_url="http://alvo:8000", spec_url=URL)

    spec = apis.specs_do_cadastro[1]
    assert spec.conteudo == SPEC
    assert spec.hash == calcular_hash(SPEC)


@pytest.mark.parametrize("fonte", ["url", "arquivo"])
def test_us02_c1_spec_invalida_e_rejeitada_e_nada_e_gravado(
    cadastrar: CadastrarApi,
    apis: RepositorioDeApisFalso,
    carregador: CarregadorDeSpecFalso,
    fonte: str,
) -> None:
    carregador.por_url[URL] = SpecInvalida("Spec inválida: nenhum endpoint")
    carregador.por_arquivo[ARQUIVO] = SpecInvalida("Spec inválida: nenhum endpoint")
    spec_url = URL if fonte == "url" else None
    spec_arquivo = ARQUIVO if fonte == "arquivo" else None

    with pytest.raises(SpecInvalida, match="nenhum endpoint"):
        cadastrar.executar(
            nome="tarefas",
            base_url="http://alvo:8000",
            spec_url=spec_url,
            spec_arquivo=spec_arquivo,
        )

    assert apis.apis == {}


@pytest.mark.parametrize(
    ("spec_url", "spec_arquivo"),
    [(None, None), (URL, ARQUIVO)],
    ids=["sem-spec", "url-e-arquivo"],
)
def test_us01_c1_exige_exatamente_uma_fonte_de_spec(
    cadastrar: CadastrarApi,
    apis: RepositorioDeApisFalso,
    spec_url: str | None,
    spec_arquivo: bytes | None,
) -> None:
    with pytest.raises(CadastroInvalido, match="exatamente um entre spec_url e spec_arquivo"):
        cadastrar.executar(
            nome="tarefas",
            base_url="http://alvo:8000",
            spec_url=spec_url,
            spec_arquivo=spec_arquivo,
        )

    assert apis.apis == {}
