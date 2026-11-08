"""NF-04: migrações do Alembic criam o esquema do zero em banco vazio (ADR-002)."""

import os
import subprocess
import sys
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import Engine, create_engine, inspect, make_url, text
from sqlalchemy.dialects.postgresql.base import PGInspector
from sqlmodel import SQLModel

import app.adapters.outbound.persistence.tabelas  # noqa: F401  (registra no metadata)

pytestmark = pytest.mark.integration

RAIZ = Path(__file__).resolve().parents[3]
# Mesmo valor do .env.example. No CI, DATABASE_URL vem do job test.
URL_PADRAO = "postgresql+psycopg://testhub:testhub@localhost:5432/testhub"

TABELAS = {"api_alvo", "spec_versao", "run", "resultado_teste"}
ENUMS = {
    "origem_spec": ["url", "arquivo"],
    "status_run": ["na_fila", "em_execucao", "passou", "falhou", "interrompida"],
    "status_resultado": ["passou", "falhou"],
}


@pytest.fixture
def banco_vazio() -> Iterator[str]:
    """Cria um banco novo no mesmo servidor e o remove no fim. Devolve a URL dele."""
    url = make_url(os.environ.get("DATABASE_URL", URL_PADRAO))
    nome = f"nf04_{uuid.uuid4().hex}"
    admin = create_engine(url, isolation_level="AUTOCOMMIT")
    with admin.connect() as conexao:
        conexao.execute(text(f'CREATE DATABASE "{nome}"'))
    try:
        yield url.set(database=nome).render_as_string(hide_password=False)
    finally:
        with admin.connect() as conexao:
            conexao.execute(text(f'DROP DATABASE IF EXISTS "{nome}" WITH (FORCE)'))
        admin.dispose()


def _alembic_upgrade_head(url: str) -> None:
    # Mesmo comando que a subida do hub roda no Compose.
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=RAIZ,
        env={**os.environ, "DATABASE_URL": url},
        check=True,
        capture_output=True,
    )


def _sem_diferenca_para_as_tabelas(engine: Engine) -> list[object]:
    with engine.connect() as conexao:
        diferencas: list[object] = compare_metadata(
            MigrationContext.configure(conexao), SQLModel.metadata
        )
        return diferencas


def test_nf_04_migracoes_criam_o_esquema_do_zero_em_banco_vazio(banco_vazio: str) -> None:
    engine = create_engine(banco_vazio)
    try:
        # Pré-condição: o banco começa vazio de verdade.
        assert inspect(engine).get_table_names() == []

        _alembic_upgrade_head(banco_vazio)

        inspetor = inspect(engine)
        assert isinstance(inspetor, PGInspector)  # get_enums só existe no PostgreSQL
        assert set(inspetor.get_table_names()) == TABELAS | {"alembic_version"}
        # Esquema igual às tabelas SQLModel: o autogenerate não teria nada a gerar.
        assert _sem_diferenca_para_as_tabelas(engine) == []

        # O compare_metadata não compara valores de enum nem defaults: conferidos aqui.
        enums = {e["name"]: e["labels"] for e in inspetor.get_enums()}
        assert enums == ENUMS

        colunas_run = {c["name"]: c for c in inspetor.get_columns("run")}
        assert colunas_run["status"]["default"] == "'na_fila'::status_run"
        assert colunas_run["total_passou"]["default"] == "0"
        assert colunas_run["total_falhou"]["default"] == "0"
        for tabela in ("api_alvo", "spec_versao", "run"):
            criado_em = {c["name"]: c for c in inspetor.get_columns(tabela)}["criado_em"]
            assert criado_em["default"] == "now()", tabela

        # As 4 FKs do DER, todas delete restrict. Contar evita passar com zero FKs.
        fks = [fk for tabela in TABELAS for fk in inspetor.get_foreign_keys(tabela)]
        assert len(fks) == 4
        for fk in fks:
            assert fk["options"].get("ondelete") == "RESTRICT", fk["name"]
    finally:
        engine.dispose()
