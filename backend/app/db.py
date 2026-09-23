"""Database access via SQLAlchemy Core (DatabaseProvider abstraction point).

Swap the engine URL to point at Supabase Postgres or any PostgreSQL instance.
"""
from __future__ import annotations

import json
import uuid
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from .settings import get_settings

_engine: Engine | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = create_engine(get_settings().database_url, pool_pre_ping=True, future=True)
    return _engine


def set_engine(engine: Engine) -> None:
    """Used by tests to point at the test database."""
    global _engine
    _engine = engine


@contextmanager
def db_conn():
    with get_engine().begin() as conn:
        yield conn


def new_id() -> str:
    return str(uuid.uuid4())


def jdump(obj) -> str:
    return json.dumps(obj, ensure_ascii=False)


def run_migrations(engine: Engine, migrations_dir) -> list[str]:
    """Apply .sql migration files in order, tracked in schema_migrations."""
    from pathlib import Path

    applied: list[str] = []
    files = sorted(Path(migrations_dir).glob("*.sql"))
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now())"
        ))
        done = {r[0] for r in conn.execute(text("SELECT version FROM schema_migrations"))}
    for f in files:
        version = f.stem
        if version in done:
            continue
        sql = f.read_text(encoding="utf-8")
        with engine.begin() as conn:
            conn.exec_driver_sql(sql)
            conn.execute(
                text("INSERT INTO schema_migrations(version) VALUES (:v) ON CONFLICT DO NOTHING"),
                {"v": version},
            )
        applied.append(version)
    return applied
