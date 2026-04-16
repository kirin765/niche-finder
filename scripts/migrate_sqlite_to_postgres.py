from __future__ import annotations

import argparse
import sqlite3
import tempfile
from pathlib import Path

from sqlalchemy import Column, MetaData, String, Table, create_engine, delete, insert, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError
from sqlalchemy.sql.schema import Table as SATable

from micro_niche_finder.config.database import Base
from micro_niche_finder.config.settings import get_settings
from micro_niche_finder.domain import models  # noqa: F401 - ensure metadata is populated


def _resolve_sqlite_path(source_url: str) -> Path:
    url = make_url(source_url)
    if url.drivername not in {"sqlite", "sqlite+pysqlite"}:
        raise ValueError(f"source URL must be SQLite, got {source_url!r}")
    if not url.database:
        raise ValueError("source SQLite URL must include a database path")

    source_path = Path(url.database).expanduser()
    if not source_path.is_absolute():
        source_path = (Path.cwd() / source_path).resolve()
    return source_path


def _snapshot_sqlite_database(source_path: Path) -> Path:
    temp_file = tempfile.NamedTemporaryFile(prefix="micro-niche-finder-", suffix=".sqlite3", delete=False)
    temp_path = Path(temp_file.name)
    temp_file.close()

    source_connection = sqlite3.connect(source_path)
    destination_connection = sqlite3.connect(temp_path)
    try:
        source_connection.backup(destination_connection)
    finally:
        destination_connection.close()
        source_connection.close()
    return temp_path


def _iter_rows(source_conn, table: SATable, batch_size: int):
    result = source_conn.execute(select(table))
    while True:
        rows = result.mappings().fetchmany(batch_size)
        if not rows:
            break
        yield rows


def _truncate_target_tables(target_conn, tables: list[SATable]) -> None:
    if not tables:
        return

    preparer = target_conn.dialect.identifier_preparer
    quoted_tables = ", ".join(preparer.quote(table.name) for table in tables)
    target_conn.execute(text(f"TRUNCATE TABLE {quoted_tables} RESTART IDENTITY CASCADE"))


def _reset_postgres_sequence(target_conn, table: SATable) -> None:
    pk_columns = list(table.primary_key.columns)
    if len(pk_columns) != 1:
        return

    pk_column = pk_columns[0]
    if pk_column.name != "id":
        return

    sequence_name = target_conn.execute(
        text("SELECT pg_get_serial_sequence(:table_name, :column_name)"),
        {"table_name": table.name, "column_name": pk_column.name},
    ).scalar_one_or_none()
    if not sequence_name:
        return

    max_id = target_conn.execute(text(f"SELECT COALESCE(MAX({pk_column.name}), 0) FROM {table.name}")).scalar_one()
    quoted_sequence_name = "'" + str(sequence_name).replace("'", "''") + "'"
    target_conn.execute(
        text(f"SELECT setval({quoted_sequence_name}::regclass, :sequence_value, :is_called)"),
        {"sequence_value": max_id if max_id else 1, "is_called": bool(max_id)},
    )


def _ensure_alembic_version_table(target_conn) -> Table:
    alembic_version = Table(
        "alembic_version",
        MetaData(),
        Column("version_num", String(32), nullable=False),
    )
    alembic_version.create(bind=target_conn, checkfirst=True)
    return alembic_version


def _ensure_target_database_exists(target_url: str) -> None:
    url = make_url(target_url)
    if url.get_backend_name() != "postgresql" or not url.database:
        return

    maintenance_url = url.set(database="postgres")
    maintenance_engine = create_engine(maintenance_url.render_as_string(hide_password=False), future=True)
    try:
        with maintenance_engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            exists = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :database_name"),
                {"database_name": url.database},
            ).scalar_one_or_none()
            if exists is None:
                quoted_database = '"' + url.database.replace('"', '""') + '"'
                conn.execute(text(f"CREATE DATABASE {quoted_database}"))
    finally:
        maintenance_engine.dispose()


def migrate_sqlite_to_postgres(*, source_url: str, target_url: str, batch_size: int = 1000, replace_target_data: bool = True) -> dict[str, int | str]:
    source_path = _resolve_sqlite_path(source_url)
    snapshot_path = _snapshot_sqlite_database(source_path)

    source_engine = create_engine(f"sqlite+pysqlite:///{snapshot_path}", future=True)
    target_engine = create_engine(target_url, future=True)

    table_counts: dict[str, int] = {}

    try:
        _ensure_target_database_exists(target_url)
        Base.metadata.create_all(bind=target_engine)

        with source_engine.connect() as source_conn, target_engine.begin() as target_conn:
            model_tables = list(Base.metadata.sorted_tables)
            if replace_target_data:
                _truncate_target_tables(target_conn, model_tables)

            for table in model_tables:
                inserted = 0
                for rows in _iter_rows(source_conn, table, batch_size):
                    if rows:
                        target_conn.execute(insert(table), rows)
                        inserted += len(rows)
                table_counts[table.name] = inserted
                _reset_postgres_sequence(target_conn, table)

            source_alembic = source_conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).scalar_one_or_none()
            if source_alembic is not None:
                alembic_version = _ensure_alembic_version_table(target_conn)
                if replace_target_data:
                    target_conn.execute(delete(alembic_version))
                target_conn.execute(insert(alembic_version).values(version_num=source_alembic))
                table_counts["alembic_version"] = 1
    finally:
        source_engine.dispose()
        target_engine.dispose()
        try:
            snapshot_path.unlink(missing_ok=True)
        except OSError:
            pass

    return {
        "source": str(source_path),
        "target": target_url,
        "tables_migrated": len(table_counts),
        "rows_migrated": sum(table_counts.values()),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Copy the current SQLite database into PostgreSQL.")
    parser.add_argument("--source", default="sqlite:///./micro_niche_finder.db", help="SQLite URL or path to copy from.")
    parser.add_argument(
        "--target",
        default=get_settings().database_url,
        help="PostgreSQL SQLAlchemy URL to copy into. Defaults to DATABASE_URL.",
    )
    parser.add_argument("--batch-size", type=int, default=1000, help="Rows per insert batch.")
    parser.add_argument(
        "--no-replace-target-data",
        action="store_true",
        help="Do not truncate target tables before copying.",
    )
    args = parser.parse_args()

    summary = migrate_sqlite_to_postgres(
        source_url=args.source,
        target_url=args.target,
        batch_size=args.batch_size,
        replace_target_data=not args.no_replace_target_data,
    )
    print(summary)


if __name__ == "__main__":
    main()
