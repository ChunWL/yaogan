import socket
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

_db_url = settings.DATABASE_URL


def _resolve_ipv4(hostname: str) -> str | None:
    try:
        info = socket.getaddrinfo(hostname, None, socket.AF_INET)
        return info[0][4][0]
    except socket.gaierror:
        return None


def _ensure_sslmode(url: str) -> str:
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    if "sslmode" not in params:
        params["sslmode"] = ["require"]
    return urlunparse(parsed._replace(query=urlencode(params, doseq=True)))


if "supabase" in _db_url or "render" in _db_url:
    _db_url = _ensure_sslmode(_db_url)

# Replace hostname with IPv4 to avoid Render IPv6 issues
parsed = urlparse(_db_url)
if parsed.hostname:
    ipv4 = _resolve_ipv4(parsed.hostname)
    if ipv4:
        _db_url = _db_url.replace(parsed.hostname, ipv4)

engine = create_engine(_db_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
