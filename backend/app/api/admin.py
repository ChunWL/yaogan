from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.utils.db import get_db
from app.utils.auth import require_admin
from app.models.user import User
from app.models.schemas import (
    UserListItem,
    UserListResponse,
    UserStatusRequest,
    MessageResponse,
)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=UserListResponse)
async def get_users(
    db: Session = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    users = db.query(User).order_by(User.created_at.desc()).all()
    return UserListResponse(
        success=True,
        message="获取成功",
        data=[
            UserListItem(
                id=str(u.id),
                username=u.username,
                email=u.email,
                is_active=u.is_active,
                is_admin=u.is_admin,
                created_at=u.created_at.strftime("%Y-%m-%d %H:%M") if u.created_at else "",
            )
            for u in users
        ],
        total=len(users),
    )


@router.put("/users/{user_id}/status", response_model=MessageResponse)
async def toggle_user_status(
    user_id: str,
    req: UserStatusRequest,
    db: Session = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )
    if user.is_admin and not req.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能禁用管理员账号",
        )
    user.is_active = req.is_active
    db.commit()
    action = "启用" if req.is_active else "禁用"
    return MessageResponse(success=True, message=f"用户已{action}")
