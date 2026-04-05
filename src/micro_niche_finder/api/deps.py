from collections.abc import Generator

from sqlalchemy.orm import Session

from micro_niche_finder.bootstrap import ApplicationContainer, get_container
from micro_niche_finder.config.database import SessionLocal


def get_db_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def get_app_container() -> ApplicationContainer:
    return get_container()
