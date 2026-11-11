"""Fixtures do hub montado com os adapters reais (bootstrap), para rotas e worker."""

import os
import uuid
from collections.abc import Iterator

import pytest
from redis import Redis
from rq import Queue
from sqlalchemy import Engine

from app.adapters.inbound.worker import tarefas
from app.bootstrap.configuracao import Configuracao
from app.bootstrap.container import Container, montar

# Mesmo valor do .env.example. No CI, REDIS_URL vem do job test.
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
SEED = 20261111


@pytest.fixture
def fila() -> Iterator[Queue]:
    """Fila com nome único, apagada no fim, para não misturar com a fila real `runs`."""
    fila = Queue(f"teste-{uuid.uuid4().hex}", connection=Redis.from_url(REDIS_URL))
    try:
        yield fila
    finally:
        fila.delete(delete_jobs=True)


@pytest.fixture
def configuracao(engine: Engine, fila: Queue) -> Configuracao:
    return Configuracao(
        database_url=engine.url.render_as_string(hide_password=False),
        redis_url=REDIS_URL,
        fila_das_runs=fila.name,
        seed=SEED,
        timeout_conexao_s=1.0,
    )


@pytest.fixture
def container(configuracao: Configuracao) -> Iterator[Container]:
    """Container do hub. As tarefas do worker usam este mesmo container."""
    montado = montar(configuracao)
    tarefas.usar(montado)
    try:
        yield montado
    finally:
        tarefas.usar(None)
        montado.engine.dispose()
