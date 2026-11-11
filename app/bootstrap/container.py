"""Monta os casos de uso com os adapters reais (ADR-003). Único lugar que liga os dois."""

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import Engine, create_engine

from app.adapters.outbound.generator.gerador_schemathesis import GeradorSchemathesis
from app.adapters.outbound.persistence.repositorio_apis import RepositorioDeApisSQL
from app.adapters.outbound.persistence.repositorio_runs import RepositorioDeRunsSQL
from app.adapters.outbound.persistence.repositorio_specs import RepositorioDeSpecsSQL
from app.adapters.outbound.queue.executor_rq import ExecutorDeRunRQ
from app.adapters.outbound.spec_loader.carregador_http import CarregadorDeSpecHttp
from app.application.cadastrar_api import CadastrarApi
from app.application.consultar_runs import ConsultarRun, ListarRuns
from app.application.disparar_run import DispararRun
from app.application.executar_run import ExecutarRun
from app.application.interromper_run import InterromperRun, RecuperarRunsPresas
from app.bootstrap.configuracao import Configuracao

# Funções que o worker executa, por caminho pontilhado: o executor RQ não importa a
# entrada do worker (ADR-003).
TAREFA_EXECUTAR_RUN = "app.adapters.inbound.worker.tarefas.executar_run"
CALLBACK_DE_FALHA = "app.adapters.inbound.worker.tarefas.ao_falhar"


def agora() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True)
class Container:
    engine: Engine
    cadastrar_api: CadastrarApi
    disparar_run: DispararRun
    executar_run: ExecutarRun
    interromper_run: InterromperRun
    recuperar_runs_presas: RecuperarRunsPresas
    listar_runs: ListarRuns
    consultar_run: ConsultarRun


def montar(configuracao: Configuracao) -> Container:
    # pool_pre_ping: o worker reusa o engine entre jobs, e o banco pode ter reiniciado.
    engine = create_engine(configuracao.database_url, pool_pre_ping=True)
    apis = RepositorioDeApisSQL(engine)
    specs = RepositorioDeSpecsSQL(engine)
    runs = RepositorioDeRunsSQL(engine)
    carregador = CarregadorDeSpecHttp(timeout_s=configuracao.timeout_download_spec_s)
    gerador = GeradorSchemathesis(
        limite_de_casos=configuracao.limite_de_casos,
        timeout_s=configuracao.timeout_requisicao_s,
    )
    executor = ExecutorDeRunRQ(
        redis_url=configuracao.redis_url,
        tarefa=TAREFA_EXECUTAR_RUN,
        callback_de_falha=CALLBACK_DE_FALHA,
        tempo_maximo_s=configuracao.tempo_maximo_run_s,
        timeout_conexao_s=configuracao.timeout_conexao_s,
        fila=configuracao.fila_das_runs,
    )
    return Container(
        engine=engine,
        cadastrar_api=CadastrarApi(apis=apis, carregador=carregador, relogio=agora),
        disparar_run=DispararRun(
            apis=apis, runs=runs, executor=executor, relogio=agora, seed=configuracao.seed
        ),
        executar_run=ExecutarRun(
            apis=apis,
            specs=specs,
            runs=runs,
            carregador=carregador,
            gerador=gerador,
            relogio=agora,
        ),
        interromper_run=InterromperRun(runs=runs, relogio=agora),
        recuperar_runs_presas=RecuperarRunsPresas(runs=runs, relogio=agora),
        listar_runs=ListarRuns(apis=apis, runs=runs),
        consultar_run=ConsultarRun(runs=runs),
    )
