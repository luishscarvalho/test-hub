"""Enfileiramento da run no Redis com RQ (porta ExecutorDeRun, ADR-006)."""

from redis import Redis
from redis.exceptions import RedisError
from rq import Callback, Queue

from app.application.portas import FilaIndisponivel

# Mesmo nome que o serviço worker escuta no docker-compose.yml (`rq worker ... runs`).
FILA_DAS_RUNS = "runs"


class ExecutorDeRunRQ:
    def __init__(
        self,
        *,
        redis_url: str,
        tarefa: str,
        callback_de_falha: str,
        tempo_maximo_s: int,
        timeout_conexao_s: float,
        fila: str = FILA_DAS_RUNS,
    ) -> None:
        """tarefa: caminho pontilhado da função que o worker executa com o run_id.

        É texto, não a função, para que este adapter não importe a entrada do worker
        (ADR-003). Quem decide o caminho é o bootstrap.

        callback_de_falha: caminho pontilhado da função que o RQ chama no worker quando o job
        termina com exceção, inclusive por tempo excedido (RN-12b e RN-12c).

        tempo_maximo_s: tempo máximo do job no RQ. Excedido, o worker encerra o job (RN-12).
        timeout_conexao_s: espera máxima pelo Redis antes de considerar a fila indisponível.
        """
        conexao = Redis.from_url(
            redis_url,
            socket_connect_timeout=timeout_conexao_s,
            socket_timeout=timeout_conexao_s,
        )
        self._fila = Queue(fila, connection=conexao)
        self._tarefa = tarefa
        self._ao_falhar = Callback(callback_de_falha)
        self._tempo_maximo_s = tempo_maximo_s

    def enfileirar(self, run_id: int) -> None:
        try:
            self._fila.enqueue(
                self._tarefa,
                run_id,
                job_timeout=self._tempo_maximo_s,
                on_failure=self._ao_falhar,
            )
        except RedisError as erro:
            raise FilaIndisponivel(f"Não foi possível enfileirar a run {run_id}: {erro}") from erro
