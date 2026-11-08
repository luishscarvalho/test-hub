import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool
from sqlmodel import SQLModel

# Registra as tabelas no SQLModel.metadata, para o autogenerate enxergá-las.
import app.adapters.outbound.persistence.tabelas  # noqa: F401

if context.config.config_file_name is not None:
    fileConfig(context.config.config_file_name)

target_metadata = SQLModel.metadata


def url_do_banco() -> str:
    return os.environ["DATABASE_URL"]


def run_migrations_offline() -> None:
    context.configure(
        url=url_do_banco(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(url_do_banco(), poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
