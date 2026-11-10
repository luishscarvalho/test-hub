"""Executor de runs com RQ contra Redis real (ADR-006)."""

import os
import socket
import time
import uuid
from collections.abc import Iterator

import pytest
from redis import Redis
from rq import Queue, SimpleWorker
from rq.job import JobStatus

from app.adapters.outbound.queue.executor_rq import ExecutorDeRunRQ
from app.application.portas import FilaIndisponivel

pytestmark = pytest.mark.integration

# Mesmo valor do .env.example. No CI, REDIS_URL vem do job test.
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
# Qualquer função importável serve de tarefa. str devolve o argumento como texto, o que
# prova que o run_id chegou ao job. A tarefa real é a entrada do worker, que ainda não existe.
TAREFA = "builtins.str"
TEMPO_MAXIMO_S = 123
RUN_ID = 42


@pytest.fixture
def fila() -> Iterator[Queue]:
    """Fila com nome único, apagada no fim, para não misturar com a fila real `runs`."""
    fila = Queue(f"teste-{uuid.uuid4().hex}", connection=Redis.from_url(REDIS_URL))
    try:
        yield fila
    finally:
        fila.delete(delete_jobs=True)


def _executor(fila: str, redis_url: str = REDIS_URL) -> ExecutorDeRunRQ:
    return ExecutorDeRunRQ(
        redis_url=redis_url,
        tarefa=TAREFA,
        tempo_maximo_s=TEMPO_MAXIMO_S,
        timeout_conexao_s=1.0,
        fila=fila,
    )


def test_us04_c4_enfileirar_deixa_a_run_na_fila_sem_executar(fila: Queue) -> None:
    _executor(fila.name).enfileirar(RUN_ID)

    # Nada executou ainda: o disparo não espera a execução.
    assert fila.count == 1
    job = fila.jobs[0]
    assert job.get_status() == JobStatus.QUEUED
    assert (job.func_name, job.args) == (TAREFA, (RUN_ID,))

    # Um worker real, no mesmo processo, pega o job da fila e executa a tarefa com o run_id.
    SimpleWorker([fila], connection=fila.connection).work(burst=True)

    assert job.get_status() == JobStatus.FINISHED
    assert job.return_value() == str(RUN_ID)
    assert fila.count == 0


def test_rn12_t2_job_recebe_o_tempo_maximo_configurado(fila: Queue) -> None:
    _executor(fila.name).enfileirar(RUN_ID)

    assert fila.jobs[0].timeout == TEMPO_MAXIMO_S


def test_us04_c6_redis_fora_do_ar_levanta_fila_indisponivel(fila: Queue) -> None:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        porta_fechada = s.getsockname()[1]
    executor = _executor(fila.name, redis_url=f"redis://127.0.0.1:{porta_fechada}/0")

    inicio = time.monotonic()
    with pytest.raises(FilaIndisponivel, match=f"Não foi possível enfileirar a run {RUN_ID}"):
        executor.enfileirar(RUN_ID)

    # A rota responde 503 com base nisto: não pode ficar presa esperando o Redis.
    assert time.monotonic() - inicio < 10
    # E nada foi parar na fila do Redis que está de pé.
    assert fila.count == 0
