import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from app.utils.db import Base
from datetime import datetime


def china_now():
    return datetime.utcnow()


class UserSceneGroupMapping(Base):
    __tablename__ = "user_scene_group_mappings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    scene_key = Column(String(100), nullable=False)
    group_id = Column(UUID(as_uuid=True), ForeignKey("scene_groups.id"), nullable=False)
    created_at = Column(DateTime, default=china_now)

    __table_args__ = (
        UniqueConstraint("user_id", "scene_key", name="uq_user_scene_group"),
    )
