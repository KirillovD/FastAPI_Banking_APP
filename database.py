from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config import settings
from models import Base


def _engine_kwargs(database_url: str) -> dict:
    if database_url.startswith("sqlite"):
        return {
            "connect_args": {
                "check_same_thread": False,
            }
        }

    return {}


engine = create_engine(
    settings.database_url,
    **_engine_kwargs(settings.database_url),
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
