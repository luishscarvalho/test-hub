"""Worker real do RQ, no mesmo processo, com Redis, PostgreSQL e API alvo reais (ADR-006).

O SimpleWorker executa o job sem fork, então as tarefas usam o container da fixture. O
tempo máximo do job e o callback de falha são os mesmos do worker do Compose.
"""

import socket
from collections.abc import Iterator
from dataclasses import replace

import httpx
import pytest
from rq import Queue, SimpleWorker
from sqlalchemy import Engine, text

from app.adapters.inbound.worker import tarefas
from app.adapters.outbound.persistence.repositorio_apis import RepositorioDeApisSQL
from app.adapters.outbound.persistence.repositorio_runs import RepositorioDeRunsSQL
from app.adapters.outbound.persistence.repositorio_specs import RepositorioDeSpecsSQL
from app.adapters.outbound.spec_loader.carregador_http import CarregadorDeSpecHttp
from app.application.executar_run import ExecutarRun
from app.bootstrap.configuracao import Configuracao
from app.bootstrap.container import Container, agora, montar
from app.domain.resultado_teste import ResultadoDoTeste
from app.domain.run import Run
from app.domain.status_run import StatusRun
from tests.integration.conftest import SEED

pytestmark = pytest.mark.integration

# Operações da spec da API alvo (ADR-008).
OPERACOES = {
    ("/saude", "GET"),
    ("/tarefas", "GET"),
    ("/tarefas", "POST"),
    ("/tarefas/{id}", "GET"),
    ("/tarefas/{id}", "PUT"),
    ("/tarefas/{id}", "DELETE"),
}


def _spec(base_url: str) -> bytes:
    return httpx.get(f"{base_url}/openapi.json").content


def _disparar(container: Container, base_url: str, spec: bytes) -> int:
    api = container.cadastrar_api.executar(nome="tarefas", base_url=base_url, spec_arquivo=spec)
    assert api.id is not None
    run = container.disparar_run.executar(api.id)
    assert run.id is not None
    return run.id


def _processar_fila(fila: Queue) -> None:
    SimpleWorker([fila], connection=fila.connection).work(burst=True)


def _run(engine: Engine, run_id: int) -> tuple[Run, list[ResultadoDoTeste]]:
    runs = RepositorioDeRunsSQL(engine)
    run = runs.buscar(run_id)
    assert run is not None
    return run, runs.buscar_resultados(run_id)


@pytest.fixture
def porta_fechada() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        porta: int = s.getsockname()[1]
    return porta


@pytest.fixture
def api_que_nao_responde() -> Iterator[str]:
    """Aceita a conexão e nunca responde: toda requisição espera até o timeout."""
    with socket.socket() as servidor:
        servidor.bind(("127.0.0.1", 0))
        servidor.listen(64)
        yield f"http://127.0.0.1:{servidor.getsockname()[1]}"


def _trocar_container(configuracao: Configuracao) -> Container:
    """Container com outra configuração, também usado pelas tarefas do worker."""
    novo = montar(configuracao)
    tarefas.usar(novo)
    return novo


def test_us04_c2_worker_executa_todos_os_testes_contra_a_base_url(
    container: Container, engine: Engine, fila: Queue, api_alvo: str
) -> None:
    run_id = _disparar(container, api_alvo, _spec(api_alvo))

    _processar_fila(fila)

    run, resultados = _run(engine, run_id)
    assert run.status == StatusRun.PASSOU, [r.mensagem_erro for r in resultados]
    assert {(r.endpoint, r.metodo) for r in resultados} == OPERACOES
    assert (run.total_passou, run.total_falhou) == (len(OPERACOES), 0)
    assert run.seed == SEED
    assert run.spec_versao_id is not None


def test_us04_c3_com_modo_falha_a_run_termina_falhou_apontando_os_endpoints(
    container: Container, engine: Engine, fila: Queue, api_alvo_com_falha: str
) -> None:
    run_id = _disparar(container, api_alvo_com_falha, _spec(api_alvo_com_falha))

    _processar_fila(fila)

    run, resultados = _run(engine, run_id)
    falhas = {(r.endpoint, r.metodo): r.mensagem_erro for r in resultados if r.mensagem_erro}
    assert run.status == StatusRun.FALHOU
    assert set(falhas) == {("/tarefas", "GET"), ("/tarefas/{id}", "GET")}
    assert run.total_falhou == 2


def test_us04_c5_spec_por_url_inacessivel_na_run_termina_falhou_sem_versao(
    container: Container, engine: Engine, fila: Queue, api_alvo: str, porta_fechada: int
) -> None:
    api = container.cadastrar_api.executar(
        nome="tarefas", base_url=api_alvo, spec_url=f"{api_alvo}/openapi.json"
    )
    # A spec sai do ar depois do cadastro.
    with engine.begin() as conexao:
        conexao.execute(
            text("UPDATE api_alvo SET spec_url = :url"),
            {"url": f"http://127.0.0.1:{porta_fechada}/openapi.json"},
        )
    assert api.id is not None
    run = container.disparar_run.executar(api.id)
    assert run.id is not None

    _processar_fila(fila)

    final, resultados = _run(engine, run.id)
    assert final.status == StatusRun.FALHOU
    assert final.mensagem_erro is not None
    assert final.mensagem_erro.startswith("Falha ao baixar a spec")
    assert (final.spec_versao_id, resultados) == (None, [])


def test_rn12_t1_subida_do_worker_interrompe_runs_presas(
    container: Container, engine: Engine, api_alvo: str
) -> None:
    run_id = _disparar(container, api_alvo, _spec(api_alvo))
    runs = RepositorioDeRunsSQL(engine)
    presa = runs.buscar(run_id)
    assert presa is not None
    presa.iniciar(agora())
    runs.salvar(presa, [])

    assert tarefas.recuperar_runs_presas() == [run_id]

    run, resultados = _run(engine, run_id)
    assert run.status == StatusRun.INTERROMPIDA
    assert run.fim is not None
    assert run.mensagem_erro == "Run interrompida: o worker reiniciou durante a execução"
    assert resultados == []


def test_rn12_t2_run_que_excede_o_tempo_maximo_termina_interrompida(
    configuracao: Configuracao,
    engine: Engine,
    fila: Queue,
    api_alvo: str,
    api_que_nao_responde: str,
) -> None:
    lento = _trocar_container(configuracao.model_copy(update={"tempo_maximo_run_s": 1}))
    run_id = _disparar(lento, api_que_nao_responde, _spec(api_alvo))

    _processar_fila(fila)
    lento.engine.dispose()

    run, resultados = _run(engine, run_id)
    assert run.status == StatusRun.INTERROMPIDA
    assert run.inicio is not None and run.fim is not None
    assert run.mensagem_erro == (
        "Run interrompida: tempo máximo de execução excedido: limite de 1s"
    )
    assert (resultados, run.total_passou, run.total_falhou) == ([], 0, 0)


class GeradorQueQuebra:
    def gerar_e_executar(
        self, spec: dict[str, object], base_url: str, seed: int
    ) -> list[ResultadoDoTeste]:
        raise RuntimeError("bug simulado no hub")


def test_rn12_t3_erro_inesperado_termina_interrompida_e_nunca_falhou(
    container: Container, engine: Engine, fila: Queue, api_alvo: str
) -> None:
    quebrado = replace(
        container,
        executar_run=ExecutarRun(
            apis=RepositorioDeApisSQL(engine),
            specs=RepositorioDeSpecsSQL(engine),
            runs=RepositorioDeRunsSQL(engine),
            carregador=CarregadorDeSpecHttp(timeout_s=5),
            gerador=GeradorQueQuebra(),
            relogio=agora,
        ),
    )
    tarefas.usar(quebrado)
    run_id = _disparar(quebrado, api_alvo, _spec(api_alvo))

    _processar_fila(fila)

    run, resultados = _run(engine, run_id)
    assert run.status == StatusRun.INTERROMPIDA
    assert run.fim is not None
    assert run.mensagem_erro == (
        "Run interrompida por erro interno do hub: RuntimeError: bug simulado no hub"
    )
    assert resultados == []
