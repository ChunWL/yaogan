import os
import uuid as uuid_lib
from fastapi import APIRouter, Depends, HTTPException, status, Form
from sqlalchemy.orm import Session
from app.utils.db import get_db
from app.utils.auth import require_admin
from app.models.user import User
from app.models.custom_scene import CustomScene
from app.models.acquired_scene import AcquiredScene
from app.models.detection import DetectionRecord
from app.models.schemas import (
    UserListItem,
    UserListResponse,
    UserStatusRequest,
    MessageResponse,
)
from app.config import settings
from app.utils.minio_client import delete_file as minio_delete
from app.api.scenes import _custom_scene_to_dict
from app.models.announcement import Announcement

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


@router.get("/models")
async def admin_list_models(
    db: Session = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    """List all public models across all users (admin only)."""
    scenes = db.query(CustomScene).filter(
        CustomScene.is_public == True
    ).order_by(CustomScene.created_at.desc()).all()

    user_ids = list(set(str(s.user_id) for s in scenes))
    users = {}
    if user_ids:
        for u in db.query(User).filter(User.id.in_([uuid_lib.UUID(uid) for uid in user_ids])).all():
            users[str(u.id)] = u.username

    result = []
    for s in scenes:
        d = _custom_scene_to_dict(s)
        d["status"] = s.status
        d["creator_name"] = users.get(str(s.user_id), "未知")
        result.append(d)

    return {"success": True, "data": result}


@router.put("/models/{scene_id}/status")
async def admin_toggle_model_status(
    scene_id: str,
    status: str = Form(...),
    db: Session = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    """Toggle model status between 'active' and 'suspended'."""
    if status not in ("active", "suspended"):
        raise HTTPException(status_code=400, detail="状态值无效，仅支持 active/suspended")

    try:
        uid = uuid_lib.UUID(scene_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的场景 ID")

    scene = db.query(CustomScene).filter(CustomScene.id == uid).first()
    if not scene:
        raise HTTPException(status_code=404, detail="场景不存在")
    if not scene.is_public:
        raise HTTPException(status_code=400, detail="只能管理公开模型")

    scene.status = status
    db.commit()

    action = "已暂停" if status == "suspended" else "已恢复"
    return {"success": True, "message": f"模型已{action}"}


@router.delete("/models/{scene_id}")
async def admin_delete_model(
    scene_id: str,
    db: Session = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    """Permanently delete a public model. Also deletes related AcquiredScene records."""
    try:
        uid = uuid_lib.UUID(scene_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的场景 ID")

    scene = db.query(CustomScene).filter(CustomScene.id == uid).first()
    if not scene:
        raise HTTPException(status_code=404, detail="场景不存在")

    # Calculate MODELS_DIR (same pattern as in scenes.py)
    MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")

    # Delete .pt from local filesystem
    model_path = os.path.join(MODELS_DIR, scene.model_filename)
    if os.path.exists(model_path):
        os.remove(model_path)

    # Delete .pt from MinIO
    minio_delete(settings.MINIO_BUCKET, scene.model_filename)

    # Delete AcquiredScene records first (FK constraint), then CustomScene
    db.query(AcquiredScene).filter(AcquiredScene.custom_scene_id == uid).delete()
    db.delete(scene)
    db.commit()

    # Create announcement
    announcement = Announcement(
        message=f"管理员已删除模型「{scene.name}」",
        model_name=scene.name,
        deleted_by=uuid_lib.UUID(_admin["sub"]),
    )
    db.add(announcement)
    db.commit()

    return {"success": True, "message": "模型已永久删除"}
