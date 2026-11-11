"""Entrada do worker: python -m app.adapters.inbound.worker (ADR-006).

Recupera as runs presas e só então passa a pegar jobs da fila. Worker único na v1: a
recuperação supõe que nenhum outro worker está executando runs.
"""

import logging

from redis import Redis
from rq import Worker

from app.adapters.inbound.worker import tarefas
from app.bootstrap.configuracao import Configuracao

log = logging.getLogger("worker")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    configuracao = Configuracao()

    interrompidas = tarefas.recuperar_runs_presas()
    log.info("Runs presas marcadas como interrompidas na subida: %s", interrompidas or "nenhuma")
    # O RQ cria um processo por job com fork. Conexões abertas não podem ser herdadas.
    tarefas.container().engine.dispose()

    conexao = Redis.from_url(configuracao.redis_url)
    Worker([configuracao.fila_das_runs], connection=conexao).work()


if __name__ == "__main__":
    main()
