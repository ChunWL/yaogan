from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from app.utils.db import get_db
from app.utils.auth import hash_password, verify_password, create_access_token, get_current_user
from app.models.user import User
from app.models.detection import DetectionRecord
from app.models.schemas import (
    LoginRequest,
    RegisterRequest,
    ForgotPasswordRequest,
    TokenResponse,
    UserInfo,
    MessageResponse,
    UserProfile,
    ProfileResponse,
    UpdateProfileRequest,
    ChangePasswordRequest,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == req.username).first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )
    token = create_access_token({"sub": str(user.id), "username": user.username, "is_admin": user.is_admin})
    return TokenResponse(
        access_token=token,
        user=UserInfo(id=str(user.id), username=user.username, email=user.email, is_admin=user.is_admin),
    )


@router.post("/register", response_model=MessageResponse)
async def register(req: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(
        or_(User.username == req.username, User.email == req.email)
    ).first()
    if existing:
        if existing.username == req.username:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="用户名已被注册",
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="邮箱已被注册",
        )
    user = User(
        username=req.username,
        email=req.email,
        hashed_password=hash_password(req.password),
    )
    db.add(user)
    db.commit()
    return MessageResponse(success=True, message="注册成功")


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(req: ForgotPasswordRequest):
    return MessageResponse(success=True, message="密码重置链接已发送到您的邮箱（功能开发中）")


@router.get("/profile", response_model=ProfileResponse)
async def get_profile(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == current_user["sub"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    total_detections = (
        db.query(func.count(DetectionRecord.id))
        .filter(DetectionRecord.user_id == current_user["sub"])
        .scalar()
    ) or 0

    total_objects = (
        db.query(func.coalesce(func.sum(DetectionRecord.total_objects), 0))
        .filter(DetectionRecord.user_id == current_user["sub"])
        .scalar()
    ) or 0

    China_tz = timezone(timedelta(hours=8))
    now = datetime.now(China_tz).replace(tzinfo=None)
    usage_days = max(0, (now - user.created_at.replace(tzinfo=None)).days)

    profile = UserProfile(
        id=str(user.id),
        username=user.username,
        email=user.email,
        is_admin=user.is_admin,
        created_at=user.created_at.strftime("%Y-%m-%d") if user.created_at else "",
        total_detections=total_detections,
        total_objects=total_objects,
        success_rate=100.0,
        usage_days=usage_days,
    )

    return ProfileResponse(success=True, message="获取成功", data=profile)


@router.put("/profile", response_model=MessageResponse)
async def update_profile(
    req: UpdateProfileRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    import re
    if not re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", req.email):
        raise HTTPException(status_code=400, detail="邮箱格式不正确")

    existing = db.query(User).filter(User.email == req.email, User.id != current_user["sub"]).first()
    if existing:
        raise HTTPException(status_code=409, detail="邮箱已被其他用户使用")

    user = db.query(User).filter(User.id == current_user["sub"]).first()
    user.email = req.email
    db.commit()

    return MessageResponse(success=True, message="邮箱修改成功")


@router.put("/password", response_model=MessageResponse)
async def change_password(
    req: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == current_user["sub"]).first()
    if not user or not verify_password(req.old_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="旧密码错误")

    if len(req.new_password) < 6 or len(req.new_password) > 30:
        raise HTTPException(status_code=400, detail="密码长度需要6-30位")

    import re
    if not re.search(r"[a-zA-Z]", req.new_password) or not re.search(r"\d", req.new_password):
        raise HTTPException(status_code=400, detail="密码需要包含字母和数字")

    user.hashed_password = hash_password(req.new_password)
    db.commit()

    return MessageResponse(success=True, message="密码修改成功")
