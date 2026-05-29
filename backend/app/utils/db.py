from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

_engine_args = {"pool_pre_ping": True}

if "supabase" in settings.DATABASE_URL or "render" in settings.DATABASE_URL:
    _engine_args["connect_args"] = {
        "sslmode": "require",
        "options": "-c statement_timeout=30000",
    }

engine = create_engine(settings.DATABASE_URL, **_engine_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
