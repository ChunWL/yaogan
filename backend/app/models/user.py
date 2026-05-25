import uuid
from datetime import datetime, timedelta, timezone

China_tz = timezone(timedelta(hours=8))


def _beijing_now():
    return datetime.now(China_tz).replace(tzinfo=None)
from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from app.utils.db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=_beijing_now)
    avatar_url = Column(String(255), nullable=True, default=None)
