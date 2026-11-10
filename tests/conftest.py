"""Fixtures compartilhadas."""

import os
import socket
import subprocess
import sys
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import httpx
import pytest
from sqlalchemy import Engine, create_engine, make_url, text

RAIZ = Path(__file__).resolve().parent.parent
LIMITE_SUBIDA_S = 15.0
INTERVALO_CONSULTA_S = 0.05


def _porta_livre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        porta: int = s.getsockname()[1]
        return porta


def _esperar_saude(processo: subprocess.Popen[bytes], base_url: str) -> None:
    """Espera o GET /saude responder 200, com tempo limite (sem sleep fixo)."""
    prazo = time.monotonic() + LIMITE_SUBIDA_S
    while time.monotonic() < prazo:
        if processo.poll() is not None:
            raise RuntimeError(f"API alvo encerrou na subida (código {processo.returncode})")
        try:
            if httpx.get(f"{base_url}/saude", timeout=0.5).status_code == 200:
                return
        except httpx.TransportError:
            pass
        time.sleep(INTERVALO_CONSULTA_S)
    raise TimeoutError(f"API alvo não ficou saudável em {LIMITE_SUBIDA_S}s")


@contextmanager
def _subir_api_alvo(modo_falha: str | None) -> Iterator[str]:
    """Sobe a API alvo com uvicorn em subprocesso (ADR-004) e devolve a base URL.

    modo_falha=None remove MODO_FALHA do ambiente, para testar o padrão de verdade.
    """
    ambiente = {k: v for k, v in os.environ.items() if k != "MODO_FALHA"}
    if modo_falha is not None:
        ambiente["MODO_FALHA"] = modo_falha
    porta = _porta_livre()
    comando = [sys.executable, "-m", "uvicorn", "target_api.main:app"]
    comando += ["--host", "127.0.0.1", "--port", str(porta), "--log-level", "warning"]
    processo = subprocess.Popen(comando, cwd=RAIZ, env=ambiente)
    base_url = f"http://127.0.0.1:{porta}"
    try:
        _esperar_saude(processo, base_url)
        yield base_url
    finally:
        processo.terminate()
        try:
            processo.wait(timeout=10)
        except subprocess.TimeoutExpired:
            processo.kill()
            processo.wait()


# Escopo de função: cada teste recebe a API no estado inicial da seed (ADR-008).
@pytest.fixture
def api_alvo() -> Iterator[str]:
    """API alvo sem MODO_FALHA no ambiente."""
    with _subir_api_alvo(modo_falha=None) as base_url:
        yield base_url


@pytest.fixture
def api_alvo_com_falha() -> Iterator[str]:
    """API alvo com MODO_FALHA=true."""
    with _subir_api_alvo(modo_falha="true") as base_url:
        yield base_url


# Mesmo valor do .env.example. No CI, DATABASE_URL vem do job test.
URL_BANCO_PADRAO = "postgresql+psycopg://testhub:testhub@localhost:5432/testhub"


@pytest.fixture(scope="session")
def _engine_da_sessao() -> Iterator[Engine]:
    """Banco novo por sessão, com o esquema criado pelas migrações do Alembic (ADR-002)."""
    url = make_url(os.environ.get("DATABASE_URL", URL_BANCO_PADRAO))
    nome = f"repo_{uuid.uuid4().hex}"
    admin = create_engine(url, isolation_level="AUTOCOMMIT")
    with admin.connect() as conexao:
        conexao.execute(text(f'CREATE DATABASE "{nome}"'))
    url_teste = url.set(database=nome).render_as_string(hide_password=False)
    engine = create_engine(url_teste)
    try:
        subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=RAIZ,
            env={**os.environ, "DATABASE_URL": url_teste},
            check=True,
            capture_output=True,
        )
        yield engine
    finally:
        engine.dispose()
        with admin.connect() as conexao:
            conexao.execute(text(f'DROP DATABASE IF EXISTS "{nome}" WITH (FORCE)'))
        admin.dispose()


@pytest.fixture
def engine(_engine_da_sessao: Engine) -> Iterator[Engine]:
    """Engine do banco de testes. Cada teste termina com as tabelas truncadas."""
    yield _engine_da_sessao
    with _engine_da_sessao.begin() as conexao:
        conexao.execute(
            text("TRUNCATE resultado_teste, run, spec_versao, api_alvo RESTART IDENTITY CASCADE")
        )
