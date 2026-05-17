from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from src.config import settings


def make_engine() -> Engine:
    return create_engine(settings.db_url, pool_pre_ping=True, pool_recycle=3600)


engine = make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
