from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

_db_url = settings.DATABASE_URL


def _ensure_sslmode(url: str) -> str:
    if "sslmode=" in url:
        return url
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    params["sslmode"] = ["require"]
    return urlunparse(parsed._replace(query=urlencode(params, doseq=True)))


if "supabase" in _db_url or "render" in _db_url:
    _db_url = _ensure_sslmode(_db_url)

engine = create_engine(_db_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
