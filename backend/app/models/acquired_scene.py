import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from app.utils.db import Base
from datetime import datetime


def china_now():
    return datetime.utcnow()


class AcquiredScene(Base):
    __tablename__ = "acquired_scenes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    custom_scene_id = Column(UUID(as_uuid=True), ForeignKey("custom_scenes.id"), nullable=False)
    created_at = Column(DateTime, default=china_now)

    __table_args__ = (
        UniqueConstraint("user_id", "custom_scene_id", name="uq_user_acquired_scene"),
    )
