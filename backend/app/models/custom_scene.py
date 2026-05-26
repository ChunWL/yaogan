import uuid
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, JSON, Float
from sqlalchemy.dialects.postgresql import UUID
from app.utils.db import Base
from datetime import datetime


def china_now():
    return datetime.utcnow()


class CustomScene(Base):
    __tablename__ = "custom_scenes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    name = Column(String(100), nullable=False)
    model_filename = Column(String(255), nullable=False)
    original_model_name = Column(String(255), nullable=True)
    class_names = Column(JSON, nullable=False, default=dict)
    description = Column(String(500), default="")
    is_public = Column(Boolean, default=False)
    status = Column(String(20), default="active", nullable=False)
    group_id = Column(UUID(as_uuid=True), ForeignKey("scene_groups.id"), nullable=True, index=True)
    precision = Column(Float, nullable=True)
    recall = Column(Float, nullable=True)
    map50 = Column(Float, nullable=True)
    map50_95 = Column(Float, nullable=True)
    created_at = Column(DateTime, default=china_now)
