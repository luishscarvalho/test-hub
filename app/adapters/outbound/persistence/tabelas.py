"""Tabelas SQLModel da v1, fiéis ao docs/der/der-test-hub.dbml.

São modelos de banco (table=True), separados dos DTOs da API (ADR-002). Os enums daqui
existem só para o esquema: o mapeamento para o domínio fica nos repositórios.
"""

from datetime import datetime
from enum import StrEnum
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class OrigemSpec(StrEnum):
    URL = "url"
    ARQUIVO = "arquivo"


class StatusRun(StrEnum):
    NA_FILA = "na_fila"
    EM_EXECUCAO = "em_execucao"
    PASSOU = "passou"
    FALHOU = "falhou"
    INTERROMPIDA = "interrompida"


class StatusResultado(StrEnum):
    PASSOU = "passou"
    FALHOU = "falhou"


def _tipo_enum(enum: type[StrEnum], nome: str) -> sa.Enum:
    # Sem values_callable o SQLAlchemy grava o nome do membro (NA_FILA), não o valor (na_fila).
    return sa.Enum(enum, name=nome, values_callable=lambda membros: [m.value for m in membros])


def _id() -> Any:
    return Field(default=None, primary_key=True, sa_type=sa.BigInteger)


def _fk(alvo: str, *, nullable: bool = False) -> Any:
    return Field(
        default=None if nullable else ...,
        foreign_key=alvo,
        ondelete="RESTRICT",
        nullable=nullable,
        sa_type=sa.BigInteger,
    )


def _criado_em() -> Any:
    # Preenchido pelo banco (default now()). None no objeto até o INSERT.
    return Field(
        default=None,
        nullable=False,
        sa_type=sa.DateTime(timezone=True),
        sa_column_kwargs={"server_default": sa.func.now()},
    )


class ApiAlvoTabela(SQLModel, table=True):
    __tablename__ = "api_alvo"

    id: int | None = _id()
    nome: str = Field(nullable=False)
    base_url: str = Field(nullable=False)
    # Preenchida se a spec foi cadastrada por URL. Nula se foi por arquivo.
    spec_url: str | None = Field(default=None, nullable=True)
    criado_em: datetime | None = _criado_em()


class SpecVersaoTabela(SQLModel, table=True):
    """Imutável. Não pode ser removida enquanto houver run que a referencie (ADR-007)."""

    __tablename__ = "spec_versao"
    __table_args__ = (sa.UniqueConstraint("api_alvo_id", "hash", name="uq_spec_versao_api_hash"),)

    id: int | None = _id()
    api_alvo_id: int = _fk("api_alvo.id")
    # JSON normalizado. YAML é convertido antes de gravar.
    conteudo: dict[str, Any] = Field(sa_type=JSONB, nullable=False)
    # SHA-256 do JSON normalizado com chaves ordenadas.
    hash: str = Field(sa_type=sa.CHAR(64), nullable=False)
    origem: OrigemSpec = Field(sa_type=_tipo_enum(OrigemSpec, "origem_spec"), nullable=False)
    criado_em: datetime | None = _criado_em()


class RunTabela(SQLModel, table=True):
    """Status passou, falhou e interrompida são finais e imutáveis (RN-05, ADR-006)."""

    __tablename__ = "run"
    __table_args__ = (sa.Index("ix_run_api_criado_em", "api_alvo_id", "criado_em"),)

    id: int | None = _id()
    api_alvo_id: int = _fk("api_alvo.id")
    # Nula até o worker resolver a spec.
    spec_versao_id: int | None = _fk("spec_versao.id", nullable=True)
    status: StatusRun = Field(
        default=StatusRun.NA_FILA,
        nullable=False,
        sa_type=_tipo_enum(StatusRun, "status_run"),
        sa_column_kwargs={"server_default": StatusRun.NA_FILA.value},
    )
    # Seed usada pelo gerador (ADR-005).
    seed: int = Field(sa_type=sa.BigInteger, nullable=False)
    # Momento em que a run entrou na fila.
    criado_em: datetime | None = _criado_em()
    inicio: datetime | None = Field(default=None, sa_type=sa.DateTime(timezone=True))
    fim: datetime | None = Field(default=None, sa_type=sa.DateTime(timezone=True))
    total_passou: int = Field(default=0, nullable=False, sa_column_kwargs={"server_default": "0"})
    total_falhou: int = Field(default=0, nullable=False, sa_column_kwargs={"server_default": "0"})
    mensagem_erro: str | None = Field(default=None, sa_type=sa.Text)


class ResultadoTesteTabela(SQLModel, table=True):
    """Um resultado consolidado por par endpoint e método (RN-03, ADR-005)."""

    __tablename__ = "resultado_teste"
    __table_args__ = (
        sa.UniqueConstraint(
            "run_id", "endpoint", "metodo", name="uq_resultado_run_endpoint_metodo"
        ),
    )

    id: int | None = _id()
    run_id: int = _fk("run.id")
    # Caminho da spec, ex.: /tarefas/{id}
    endpoint: str = Field(nullable=False)
    metodo: str = Field(sa_type=sa.String(10), nullable=False)
    status: StatusResultado = Field(
        sa_type=_tipo_enum(StatusResultado, "status_resultado"), nullable=False
    )
    # Soma da duração dos casos do endpoint (ADR-005).
    duracao_ms: int = Field(nullable=False)
    # Mensagem do primeiro caso que falhou (ADR-005).
    mensagem_erro: str | None = Field(default=None, sa_type=sa.Text)
