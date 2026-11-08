"""cria esquema inicial da v1

Revision ID: 0001
Revises:
Create Date: 2026-11-08 15:50:15.478804
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Enums criados e removidos de forma explícita: o autogenerate cria o tipo junto com a
# tabela, mas não o remove no downgrade, e o upgrade seguinte quebraria.
ORIGEM_SPEC = postgresql.ENUM("url", "arquivo", name="origem_spec", create_type=False)
STATUS_RUN = postgresql.ENUM(
    "na_fila",
    "em_execucao",
    "passou",
    "falhou",
    "interrompida",
    name="status_run",
    create_type=False,
)
STATUS_RESULTADO = postgresql.ENUM("passou", "falhou", name="status_resultado", create_type=False)
ENUMS = (ORIGEM_SPEC, STATUS_RUN, STATUS_RESULTADO)


def upgrade() -> None:
    for enum in ENUMS:
        enum.create(op.get_bind())

    op.create_table(
        "api_alvo",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("nome", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("base_url", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("spec_url", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "spec_versao",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("api_alvo_id", sa.BigInteger(), nullable=False),
        sa.Column("conteudo", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("hash", sa.CHAR(length=64), nullable=False),
        sa.Column("origem", ORIGEM_SPEC, nullable=False),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["api_alvo_id"], ["api_alvo.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("api_alvo_id", "hash", name="uq_spec_versao_api_hash"),
    )
    op.create_table(
        "run",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("api_alvo_id", sa.BigInteger(), nullable=False),
        sa.Column("spec_versao_id", sa.BigInteger(), nullable=True),
        sa.Column("status", STATUS_RUN, server_default="na_fila", nullable=False),
        sa.Column("seed", sa.BigInteger(), nullable=False),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("inicio", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fim", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_passou", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_falhou", sa.Integer(), server_default="0", nullable=False),
        sa.Column("mensagem_erro", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["api_alvo_id"], ["api_alvo.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["spec_versao_id"], ["spec_versao.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_run_api_criado_em", "run", ["api_alvo_id", "criado_em"], unique=False)
    op.create_table(
        "resultado_teste",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.BigInteger(), nullable=False),
        sa.Column("endpoint", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("metodo", sa.String(length=10), nullable=False),
        sa.Column("status", STATUS_RESULTADO, nullable=False),
        sa.Column("duracao_ms", sa.Integer(), nullable=False),
        sa.Column("mensagem_erro", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["run_id"], ["run.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "run_id", "endpoint", "metodo", name="uq_resultado_run_endpoint_metodo"
        ),
    )


def downgrade() -> None:
    op.drop_table("resultado_teste")
    op.drop_index("ix_run_api_criado_em", table_name="run")
    op.drop_table("run")
    op.drop_table("spec_versao")
    op.drop_table("api_alvo")

    for enum in reversed(ENUMS):
        enum.drop(op.get_bind())
