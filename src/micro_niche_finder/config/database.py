from sqlalchemy import create_engine
from sqlalchemy import event
from sqlalchemy.orm import declarative_base, sessionmaker

from micro_niche_finder.config.settings import get_settings


settings = get_settings()

sqlite_enabled = settings.database_url.startswith("sqlite")
if sqlite_enabled and settings.app_env != "test":
    raise RuntimeError(
        "SQLite databases are only allowed when APP_ENV=test. "
        "Use PostgreSQL for all local, staging, and production runs."
    )

connect_args = {}
if sqlite_enabled:
    connect_args = {
        "timeout": 30,
        "check_same_thread": False,
    }

engine = create_engine(
    settings.database_url,
    future=True,
    connect_args=connect_args,
)

if sqlite_enabled:
    @event.listens_for(engine, "connect")
    def _configure_sqlite_connection(dbapi_connection, connection_record) -> None:  # type: ignore[no-untyped-def]
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA busy_timeout=60000")
        finally:
            cursor.close()

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()
