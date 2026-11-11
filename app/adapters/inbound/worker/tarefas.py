"""Funções que o RQ chama no worker (ADR-006). Sem regra de negócio: só chamam os casos de uso.

O container é montado uma vez por processo, no primeiro uso. Os testes trocam o container
com usar().
"""

from types import TracebackType
from typing import Any

from rq.job import Job
from rq.timeouts import JobTimeoutException

from app.application.interromper_run import CausaDaInterrupcao
from app.bootstrap.configuracao import Configuracao
from app.bootstrap.container import Container, montar

_container: Container | None = None


def usar(container: Container | None) -> None:
    """Define o container usado pelas tarefas. None volta a montar pela configuração."""
    global _container
    _container = container


def container() -> Container:
    global _container
    if _container is None:
        _container = montar(Configuracao())
    return _container


def executar_run(run_id: int) -> None:
    container().executar_run.executar(run_id)


def ao_falhar(
    job: Job,
    conexao: Any,
    tipo: type[BaseException],
    valor: BaseException,
    rastro: TracebackType | None,
) -> None:
    """Callback de falha do RQ: o job terminou com exceção (RN-12b e RN-12c).

    Roda no processo que executou o job, depois da exceção. Só traduz a exceção em causa;
    o caso de uso decide se a run muda e qual motivo grava.
    """
    run_id = job.args[0]
    if issubclass(tipo, JobTimeoutException):
        causa = CausaDaInterrupcao.TEMPO_EXCEDIDO
        detalhe = f"limite de {job.timeout}s"
    else:
        causa = CausaDaInterrupcao.ERRO_INTERNO
        detalhe = f"{tipo.__name__}: {valor}"
    container().interromper_run.executar(run_id, causa, detalhe)


def recuperar_runs_presas() -> list[int]:
    """Na subida do worker, antes de pegar jobs (RN-12a)."""
    return container().recuperar_runs_presas.executar()
