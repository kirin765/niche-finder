from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from micro_niche_finder.config.settings import get_settings


settings = get_settings()

engine = create_engine(settings.database_url, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()
