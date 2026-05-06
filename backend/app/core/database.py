"""Async SQLAlchemy engine and session setup."""

import logging
from collections.abc import AsyncGenerator

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Base for all ORM models."""


engine = create_async_engine(
    f"sqlite+aiosqlite:///{settings.db_path}",
    echo=False,
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db() -> None:
    """Create tables and migrate any missing columns (safe to run on every start)."""
    from app.models import download_client, event, indexer, queue_item  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_migrate_columns)


def _migrate_columns(conn) -> None:
    """Add any columns present in ORM models but missing from the live DB."""
    insp = inspect(conn)
    for table in Base.metadata.sorted_tables:
        if not insp.has_table(table.name):
            continue
        existing = {col["name"] for col in insp.get_columns(table.name)}
        for col in table.columns:
            if col.name not in existing:
                col_type = col.type.compile(conn.dialect)
                nullable = "NULL" if col.nullable else "NOT NULL"
                default_clause = ""
                if col.default is not None and col.default.is_scalar:
                    val = col.default.arg
                    if isinstance(val, str):
                        default_clause = f" DEFAULT '{val}'"
                    else:
                        default_clause = f" DEFAULT {val}"
                elif col.nullable:
                    default_clause = " DEFAULT NULL"
                ddl = (
                    f"ALTER TABLE {table.name} "
                    f"ADD COLUMN {col.name} {col_type}{default_clause}"
                )
                logger.info("Migrating: %s", ddl)
                conn.execute(text(ddl))


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a session and closes it after the request."""
    async with AsyncSessionLocal() as session:
        yield session
