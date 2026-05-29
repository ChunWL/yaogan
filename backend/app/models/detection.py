import uuid
from datetime import datetime, timedelta, timezone

China_tz = timezone(timedelta(hours=8))


def _utc_now():
    return datetime.utcnow()


from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSON
from app.utils.db import Base


class DetectionRecord(Base):
    __tablename__ = "detection_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    image_url = Column(String(500), nullable=False)
    result_image_url = Column(String(500), nullable=False)
    image_path = Column(String(500), nullable=False)
    result_path = Column(String(500), nullable=False)
    total_objects = Column(Integer, default=0)
    detection_time = Column(Float, default=0.0)
    model_name = Column(String(100), default="pest-v1")
    status = Column(String(50), default="completed")
    type = Column(String(50), default="single")
    scene = Column(String(50), default="steel", index=True)
    defect_results = Column(JSON, default=list)
    created_at = Column(DateTime, default=_utc_now)
