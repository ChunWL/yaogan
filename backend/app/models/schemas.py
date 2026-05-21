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
    filename: str
    image: str
    image_url: str
    result_image_url: str
    type: str
    status: str
    time: str
    count: int
    targets: int
    detectedTargets: List[str]


class HistoryResponse(BaseModel):
    success: bool
    message: str
    data: List[HistoryItem]
    total: int


class HistoryDetailResponse(BaseModel):
    success: bool
    message: str
    data: Optional[DetectionResult] = None


class TargetItem(BaseModel):
    id: int
    name: str
    chinese_name: str
    description: Optional[str] = None


class TargetListResponse(BaseModel):
    success: bool
    message: str
    data: List[TargetItem]


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str


class ForgotPasswordRequest(BaseModel):
    email: str


class UserInfo(BaseModel):
    id: str
    username: str
    email: str
    is_admin: bool = False

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserInfo


class MessageResponse(BaseModel):
    success: bool
    message: str


class UserListItem(BaseModel):
    id: str
    username: str
    email: str
    is_active: bool
    is_admin: bool
    created_at: str


class UserListResponse(BaseModel):
    success: bool
    message: str
    data: list[UserListItem]
    total: int


class UserStatusRequest(BaseModel):
    is_active: bool


class UserProfile(BaseModel):
    id: str
    username: str
    email: str
    is_admin: bool
    created_at: str
    total_detections: int
    total_objects: int
    success_rate: float
    usage_days: int


class ProfileResponse(BaseModel):
    success: bool
    message: str
    data: Optional[UserProfile] = None


class UpdateProfileRequest(BaseModel):
    email: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class BatchResultItem(BaseModel):
    filename: str
    success: bool
    result: Optional[DetectionResult] = None


class BatchDetectionResponse(BaseModel):
    success: bool
    message: str
    data: Optional[List[BatchResultItem]] = None
    total: int


class VideoTaskResponse(BaseModel):
    task_id: str
    status: str
    message: str


class VideoProgressResponse(BaseModel):
    task_id: str
    status: str
    progress: float = 0.0
    processed_frames: int = 0
    total_frames: int = 0
    result_video_url: Optional[str] = None
    summary: Optional[dict] = None
    message: Optional[str] = None