"""Alembic environment for the Read Store.

Mirrors ``db/migrations/env.py`` but targets the *separate* read database:
reads ``READ_STORE_URL`` (not ``DATABASE_URL``) and uses
``db.readstore.base.ReadStoreBase.metadata`` as ``target_metadata`` so the
Read Store projections are migrated independently of the Operational DB.
"""

import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Repo root on sys.path so `db.readstore.*` imports resolve.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from db.readstore.base import ReadStoreBase  # noqa: E402

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

read_store_url = os.environ.get("READ_STORE_URL")
if read_store_url:
    config.set_main_option("sqlalchemy.url", read_store_url)

target_metadata = ReadStoreBase.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
