from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class DetectionBox(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float
    confidence: float
    class_id: int
    class_name: str


class DetectionResult(BaseModel):
    detection_id: str
    image_url: str
    result_image_url: str
    boxes: List[DetectionBox]
    total_objects: int
    detection_time: float
    model_name: str
    created_at: datetime


class SingleDetectionResponse(BaseModel):
    success: bool
    message: str
    data: Optional[DetectionResult] = None


class HistoryItem(BaseModel):
    id: str
    image_url: str
    result_image_url: str
    total_objects: int
    created_at: datetime
    model_name: str


class HistoryResponse(BaseModel):
    success: bool
    message: str
    data: List[HistoryItem]
    total: int


class TargetItem(BaseModel):
    id: int
    name: str
    chinese_name: str
    description: Optional[str] = None


class TargetListResponse(BaseModel):
    success: bool
    message: str
    data: List[TargetItem]