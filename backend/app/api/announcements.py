from fastapi import APIRouter, Depends, HTTPException, Form
from sqlalchemy.orm import Session
from app.utils.db import get_db
from app.utils.auth import require_admin
from app.models.announcement import Announcement

router = APIRouter(prefix="/announcements", tags=["announcements"])


def _to_dict(r: Announcement) -> dict:
    return {
        "id": str(r.id),
        "title": r.title or "",
        "message": r.message,
        "model_name": r.model_name or "",
        "created_at": r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else "",
    }


@router.get("")
async def list_announcements(
    db: Session = Depends(get_db),
):
    records = db.query(Announcement).order_by(Announcement.created_at.desc()).limit(50).all()
    return {"success": True, "data": [_to_dict(r) for r in records]}


@router.post("")
async def create_announcement(
    title: str = Form(""),
    message: str = Form(...),
    db: Session = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    record = Announcement(title=title or None, message=message)
    db.add(record)
    db.commit()
    db.refresh(record)
    return {"success": True, "data": _to_dict(record), "message": "公告已发布"}


@router.put("/{announcement_id}")
async def update_announcement(
    announcement_id: str,
    title: str = Form(""),
    message: str = Form(...),
    db: Session = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    import uuid as uuid_lib
    try:
        uid = uuid_lib.UUID(announcement_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的公告 ID")

    record = db.query(Announcement).filter(Announcement.id == uid).first()
    if not record:
        raise HTTPException(status_code=404, detail="公告不存在")

    record.title = title or None
    record.message = message
    db.commit()
    db.refresh(record)
    return {"success": True, "data": _to_dict(record), "message": "公告已更新"}


@router.delete("/{announcement_id}")
async def delete_announcement(
    announcement_id: str,
    db: Session = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    import uuid as uuid_lib
    try:
        uid = uuid_lib.UUID(announcement_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的公告 ID")

    record = db.query(Announcement).filter(Announcement.id == uid).first()
    if not record:
        raise HTTPException(status_code=404, detail="公告不存在")

    db.delete(record)
    db.commit()
    return {"success": True, "message": "公告已删除"}
