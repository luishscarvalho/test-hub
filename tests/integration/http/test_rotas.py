"""Rotas do hub com banco e Redis reais (ERS 10.3, US-01, US-02, US-04, US-07 e US-08).

A execução das runs pelo worker fica em tests/integration/worker. Aqui as runs são levadas
ao status desejado pelo repositório, para testar só a tradução HTTP.
"""

import socket
from collections.abc import Iterator

import httpx
import pytest
from fastapi.testclient import TestClient
from rq import Queue
from sqlalchemy import Engine, text

from app.adapters.outbound.persistence.repositorio_runs import RepositorioDeRunsSQL
from app.application.spec_normalizada import calcular_hash, normalizar
from app.bootstrap.api import criar_app
from app.bootstrap.configuracao import Configuracao
from app.bootstrap.container import Container, montar
from app.domain.resultado_teste import ResultadoDoTeste, StatusResultado
from tests.integration.conftest import SEED

pytestmark = pytest.mark.integration

OK = ResultadoDoTeste("/tarefas", "GET", StatusResultado.PASSOU, 12, None)
ERRO = ResultadoDoTeste("/tarefas/{id}", "GET", StatusResultado.FALHOU, 30, "schema violado")


@pytest.fixture
def cliente(container: Container) -> Iterator[TestClient]:
    with TestClient(criar_app(container)) as cliente:
        yield cliente


@pytest.fixture
def spec_da_api_alvo(api_alvo: str) -> bytes:
    return httpx.get(f"{api_alvo}/openapi.json").content


def _contar(engine: Engine, tabela: str) -> int:
    with engine.connect() as conexao:
        return int(conexao.execute(text(f"SELECT count(*) FROM {tabela}")).scalar_one())


def _cadastrar(cliente: TestClient, spec: bytes) -> int:
    resposta = cliente.post(
        "/apis",
        data={"nome": "tarefas", "base_url": "http://alvo:8000"},
        files={"spec_arquivo": ("openapi.json", spec, "application/json")},
    )
    assert resposta.status_code == 201, resposta.text
    api_id: int = resposta.json()["id"]
    return api_id


def _disparar(cliente: TestClient, api_id: int) -> int:
    resposta = cliente.post("/runs", json={"api_alvo_id": api_id})
    assert resposta.status_code == 202, resposta.text
    run_id: int = resposta.json()["id"]
    return run_id


def _finalizar(engine: Engine, run_id: int, resultados: list[ResultadoDoTeste]) -> None:
    """Faz pelo repositório o que o worker faria, sem executar testes."""
    runs = RepositorioDeRunsSQL(engine)
    run = runs.buscar(run_id)
    assert run is not None
    run.iniciar(run.criado_em)
    runs.salvar(run, [])
    run.spec_versao_id = 1
    run.finalizar(run.criado_em, resultados)
    runs.salvar(run, resultados)


# POST /apis


def test_us01_c3_cadastro_responde_201_com_identificador(
    cliente: TestClient, spec_da_api_alvo: bytes
) -> None:
    resposta = cliente.post(
        "/apis",
        data={"nome": "tarefas", "base_url": "http://alvo:8000"},
        files={"spec_arquivo": ("openapi.json", spec_da_api_alvo, "application/json")},
    )

    assert resposta.status_code == 201
    assert resposta.json() == {"id": 1}


@pytest.mark.parametrize("fonte", ["url", "arquivo"])
def test_us01_c2_spec_aceita_por_url_e_por_arquivo(
    cliente: TestClient, engine: Engine, api_alvo: str, spec_da_api_alvo: bytes, fonte: str
) -> None:
    dados = {"nome": "tarefas", "base_url": api_alvo}
    if fonte == "url":
        resposta = cliente.post("/apis", data={**dados, "spec_url": f"{api_alvo}/openapi.json"})
    else:
        arquivo = {"spec_arquivo": ("openapi.yaml", spec_da_api_alvo, "application/yaml")}
        resposta = cliente.post("/apis", data=dados, files=arquivo)

    assert resposta.status_code == 201, resposta.text
    assert _contar(engine, "api_alvo") == 1


@pytest.mark.parametrize("faltante", ["nome", "base_url"])
def test_us01_c1_campo_obrigatorio_faltante_responde_422_indicando_o_campo(
    cliente: TestClient, engine: Engine, spec_da_api_alvo: bytes, faltante: str
) -> None:
    dados = {"nome": "tarefas", "base_url": "http://alvo:8000"}
    del dados[faltante]

    resposta = cliente.post(
        "/apis",
        data=dados,
        files={"spec_arquivo": ("openapi.json", spec_da_api_alvo, "application/json")},
    )

    assert resposta.status_code == 422
    assert faltante in resposta.text
    assert _contar(engine, "api_alvo") == 0


def test_us01_c1_spec_faltante_responde_422(cliente: TestClient) -> None:
    resposta = cliente.post("/apis", data={"nome": "tarefas", "base_url": "http://alvo:8000"})

    assert resposta.status_code == 422
    assert "spec_url e spec_arquivo" in resposta.json()["detail"]


def test_us02_c1_spec_invalida_responde_422_e_nada_e_gravado(
    cliente: TestClient, engine: Engine
) -> None:
    resposta = cliente.post(
        "/apis",
        data={"nome": "tarefas", "base_url": "http://alvo:8000"},
        files={"spec_arquivo": ("spec.json", b'{"openapi": "3.1.0"}', "application/json")},
    )

    assert resposta.status_code == 422
    assert (_contar(engine, "api_alvo"), _contar(engine, "spec_versao")) == (0, 0)


def test_us02_c2_mensagem_de_erro_informa_o_motivo(cliente: TestClient) -> None:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        porta_fechada = s.getsockname()[1]

    resposta = cliente.post(
        "/apis",
        data={
            "nome": "tarefas",
            "base_url": "http://alvo:8000",
            "spec_url": f"http://127.0.0.1:{porta_fechada}/openapi.json",
        },
    )

    assert resposta.status_code == 422
    assert resposta.json()["detail"].startswith("Falha ao baixar a spec de http://127.0.0.1")


def test_us02_c4_spec_valida_e_salva_como_versao_com_hash(
    cliente: TestClient, engine: Engine, spec_da_api_alvo: bytes
) -> None:
    api_id = _cadastrar(cliente, spec_da_api_alvo)

    with engine.connect() as conexao:
        linha = conexao.execute(text("SELECT api_alvo_id, hash, origem FROM spec_versao")).one()
    assert tuple(linha) == (api_id, calcular_hash(normalizar(spec_da_api_alvo)), "arquivo")


# POST /runs


def test_us04_c4_disparo_responde_202_na_fila_sem_executar(
    cliente: TestClient, fila: Queue, spec_da_api_alvo: bytes
) -> None:
    api_id = _cadastrar(cliente, spec_da_api_alvo)

    resposta = cliente.post("/runs", json={"api_alvo_id": api_id})

    assert resposta.status_code == 202
    assert resposta.json() == {"id": 1, "status": "na_fila"}
    assert fila.count == 1
    assert fila.jobs[0].args == (1,)


def test_us04_c1_api_inexistente_responde_404_e_nada_e_enfileirado(
    cliente: TestClient, engine: Engine, fila: Queue
) -> None:
    resposta = cliente.post("/runs", json={"api_alvo_id": 99})

    assert resposta.status_code == 404
    assert fila.count == 0
    assert _contar(engine, "run") == 0


def test_us04_c6_fila_indisponivel_responde_503_e_a_run_nao_fica_registrada(
    configuracao: Configuracao, engine: Engine, spec_da_api_alvo: bytes
) -> None:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        porta_fechada = s.getsockname()[1]
    sem_redis = montar(
        configuracao.model_copy(update={"redis_url": f"redis://127.0.0.1:{porta_fechada}/0"})
    )
    with TestClient(criar_app(sem_redis)) as cliente:
        api_id = _cadastrar(cliente, spec_da_api_alvo)

        resposta = cliente.post("/runs", json={"api_alvo_id": api_id})

    sem_redis.engine.dispose()
    assert resposta.status_code == 503
    assert _contar(engine, "run") == 0


def test_us04_c4_disparo_sem_api_alvo_id_responde_422(cliente: TestClient) -> None:
    resposta = cliente.post("/runs", json={})

    assert resposta.status_code == 422
    assert "api_alvo_id" in resposta.text


def test_rn11_t1_nenhuma_rota_altera_a_run(cliente: TestClient, spec_da_api_alvo: bytes) -> None:
    run_id = _disparar(cliente, _cadastrar(cliente, spec_da_api_alvo))

    for metodo in ("PUT", "PATCH", "DELETE"):
        resposta = cliente.request(metodo, f"/runs/{run_id}", json={"status": "passou"})
        assert resposta.status_code == 405, metodo
    assert cliente.get(f"/runs/{run_id}").json()["status"] == "na_fila"


# GET /apis/{id}/runs


def test_us07_c3_api_sem_runs_retorna_lista_vazia(
    cliente: TestClient, spec_da_api_alvo: bytes
) -> None:
    api_id = _cadastrar(cliente, spec_da_api_alvo)

    resposta = cliente.get(f"/apis/{api_id}/runs")

    assert (resposta.status_code, resposta.json()) == (200, [])


def test_us07_c3_api_inexistente_responde_404(cliente: TestClient) -> None:
    assert cliente.get("/apis/99/runs").status_code == 404


def test_us07_c1_lista_da_mais_recente_para_a_mais_antiga(
    cliente: TestClient, spec_da_api_alvo: bytes
) -> None:
    api_id = _cadastrar(cliente, spec_da_api_alvo)
    ids = [_disparar(cliente, api_id) for _ in range(3)]

    resposta = cliente.get(f"/apis/{api_id}/runs")

    assert [item["id"] for item in resposta.json()] == list(reversed(ids))


def test_us07_c2_item_traz_data_status_e_totais(
    cliente: TestClient, engine: Engine, spec_da_api_alvo: bytes
) -> None:
    run_id = _disparar(cliente, api_id := _cadastrar(cliente, spec_da_api_alvo))
    _finalizar(engine, run_id, [OK, ERRO])

    [item] = cliente.get(f"/apis/{api_id}/runs").json()

    assert set(item) == {"id", "criado_em", "status", "total_passou", "total_falhou"}
    assert (item["status"], item["total_passou"], item["total_falhou"]) == ("falhou", 1, 1)


def test_us07_c4_run_nao_finalizada_aparece_com_status_atual_e_sem_totais(
    cliente: TestClient, spec_da_api_alvo: bytes
) -> None:
    api_id = _cadastrar(cliente, spec_da_api_alvo)
    _disparar(cliente, api_id)

    [item] = cliente.get(f"/apis/{api_id}/runs").json()

    assert (item["status"], item["total_passou"], item["total_falhou"]) == ("na_fila", None, None)


# GET /runs/{id}


def test_us08_c1_detalhe_traz_a_run_e_cada_resultado(
    cliente: TestClient, engine: Engine, spec_da_api_alvo: bytes
) -> None:
    run_id = _disparar(cliente, _cadastrar(cliente, spec_da_api_alvo))
    _finalizar(engine, run_id, [OK, ERRO])

    detalhe = cliente.get(f"/runs/{run_id}").json()

    assert (detalhe["id"], detalhe["status"]) == (run_id, "falhou")
    assert detalhe["inicio"] is not None and detalhe["fim"] is not None
    assert [(r["endpoint"], r["metodo"], r["status"]) for r in detalhe["resultados"]] == [
        ("/tarefas", "GET", "passou"),
        ("/tarefas/{id}", "GET", "falhou"),
    ]


def test_us08_c2_teste_que_falhou_traz_a_mensagem_de_erro(
    cliente: TestClient, engine: Engine, spec_da_api_alvo: bytes
) -> None:
    run_id = _disparar(cliente, _cadastrar(cliente, spec_da_api_alvo))
    _finalizar(engine, run_id, [ERRO])

    [resultado] = cliente.get(f"/runs/{run_id}").json()["resultados"]

    assert resultado["mensagem_erro"] == "schema violado"


def test_us08_c3_run_inexistente_responde_404(cliente: TestClient) -> None:
    resposta = cliente.get("/runs/99")

    assert resposta.status_code == 404
    assert resposta.json() == {"detail": "Run 99 não existe"}


def test_us08_c4_run_nao_finalizada_retorna_status_atual_sem_resultados(
    cliente: TestClient, spec_da_api_alvo: bytes
) -> None:
    run_id = _disparar(cliente, _cadastrar(cliente, spec_da_api_alvo))

    detalhe = cliente.get(f"/runs/{run_id}").json()

    assert (detalhe["status"], detalhe["resultados"]) == ("na_fila", [])
    assert (detalhe["total_passou"], detalhe["total_falhou"]) == (None, None)


def test_us08_c5_detalhe_traz_a_seed_e_a_versao_da_spec_nula_antes_de_resolver(
    cliente: TestClient, spec_da_api_alvo: bytes
) -> None:
    run_id = _disparar(cliente, _cadastrar(cliente, spec_da_api_alvo))

    detalhe = cliente.get(f"/runs/{run_id}").json()

    assert (detalhe["seed"], detalhe["spec_versao_id"]) == (SEED, None)
