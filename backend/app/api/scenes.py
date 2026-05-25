import os
import uuid
import json
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from sqlalchemy.orm import Session
from app.utils.db import get_db
from app.utils.auth import get_current_user
from app.utils.minio_client import upload_file as minio_upload
from app.config import settings
from app.models.custom_scene import CustomScene
from app.models.acquired_scene import AcquiredScene
from app.models.user import User
from app.services.detection_service import detection_service

router = APIRouter(prefix="/scenes", tags=["scenes"])

MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")

BUILT_IN_SCENES = [
    {
        "key": "steel",
        "name": "钢铁表面缺陷检测",
        "description": "对钢铁表面图像进行缺陷识别与定位",
        "defaultModel": "gt",
        "icon": "Monitor",
        "classNames": {
            "rolled-in_scale": "轧制氧化皮",
            "patches": "斑块",
            "crazing": "开裂",
            "pitted_surface": "点蚀表面",
            "inclusion": "内含物",
            "scratches": "划痕",
        },
        "is_public": True,
        "is_custom": False,
        "group_id": None,
    },
    {
        "key": "general",
        "name": "通用目标检测",
        "description": "基于 COCO 数据集的通用目标识别",
        "defaultModel": "yolo11n",
        "icon": "Picture",
        "classNames": {},
        "is_public": True,
        "is_custom": False,
        "group_id": None,
    },
]


def _custom_scene_to_dict(scene: CustomScene) -> dict:
    return {
        "key": f"custom_{scene.id.hex}",
        "name": scene.name,
        "description": f"自定义场景: {scene.name}",
        "defaultModel": scene.model_filename.replace(".pt", ""),
        "originalModelName": scene.original_model_name or scene.model_filename.replace(".pt", ""),
        "icon": "Monitor",
        "classNames": scene.class_names if isinstance(scene.class_names, dict) else json.loads(scene.class_names),
        "is_public": scene.is_public,
        "is_custom": True,
        "scene_id": str(scene.id),
        "user_id": str(scene.user_id),
        "group_id": str(scene.group_id) if scene.group_id else None,
    }


@router.post("/upload")
async def upload_scene(
    file: UploadFile = File(...),
    name: str = Form(...),
    is_public: bool = Form(False),
    description: str = Form(""),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not file.filename.endswith(".pt"):
        raise HTTPException(status_code=400, detail="仅支持 .pt 模型文件")

    # Save model file
    key = f"custom_{uuid.uuid4().hex}"
    model_filename = f"{key}.pt"
    model_path = os.path.join(MODELS_DIR, model_filename)

    contents = await file.read()
    with open(model_path, "wb") as f:
        f.write(contents)

    # Upload to MinIO
    minio_upload(settings.MINIO_BUCKET, model_filename, model_path)

    # Extract class names from model
    try:
        class_names = detection_service.get_model_class_names(model_path)
    except Exception as e:
        # Clean up on failure
        if os.path.exists(model_path):
            os.remove(model_path)
        raise HTTPException(status_code=400, detail=f"无法读取模型: {str(e)}")

    # 保存原始模型名用于展示
    original_name = (file.filename or "").replace(".pt", "")

    # Save to DB
    record = CustomScene(
        user_id=current_user["sub"],
        name=name,
        model_filename=model_filename,
        original_model_name=original_name,
        class_names=class_names,
        description=description,
        is_public=is_public,
    )
    db.add(record)
    db.commit()

    return {
        "success": True,
        "message": "场景创建成功",
        "data": _custom_scene_to_dict(record),
    }


@router.get("")
async def list_scenes(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_id = current_user["sub"]

    # 自己的自定义场景
    own_scenes = db.query(CustomScene).filter(
        CustomScene.user_id == user_id
    ).all()

    # 已获取的公开场景（其他用户的）
    acquired_ids = [
        a.custom_scene_id
        for a in db.query(AcquiredScene).filter(AcquiredScene.user_id == user_id).all()
    ]
    acquired_scenes = []
    if acquired_ids:
        acquired_scenes = db.query(CustomScene).filter(
            CustomScene.id.in_(acquired_ids)
        ).all()

    custom = own_scenes + acquired_scenes

    # Get group mappings for built-in scenes
    from app.models.user_scene_group_mapping import UserSceneGroupMapping
    mappings = {
        m.scene_key: str(m.group_id)
        for m in db.query(UserSceneGroupMapping).filter(
            UserSceneGroupMapping.user_id == user_id
        ).all()
    }

    # Annotate built-in scenes with group_id
    builtins = []
    for s in BUILT_IN_SCENES:
        s_copy = dict(s)
        s_copy["group_id"] = mappings.get(s["key"])
        builtins.append(s_copy)

    return {
        "success": True,
        "data": builtins + [_custom_scene_to_dict(s) for s in custom],
    }


@router.delete("/{scene_id}")
async def delete_scene(
    scene_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    import uuid as uuid_lib
    try:
        uid = uuid_lib.UUID(scene_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的场景 ID")

    record = db.query(CustomScene).filter(CustomScene.id == uid).first()
    if not record:
        raise HTTPException(status_code=404, detail="场景不存在")
    if str(record.user_id) != current_user["sub"]:
        raise HTTPException(status_code=403, detail="只能删除自己的场景")

    model_path = os.path.join(MODELS_DIR, record.model_filename)
    if os.path.exists(model_path):
        os.remove(model_path)

    from app.utils.minio_client import delete_file as minio_delete
    minio_delete(settings.MINIO_BUCKET, record.model_filename)

    # Delete related detection history
    scene_key = f"custom_{record.id.hex}"
    from app.models.detection import DetectionRecord
    deleted_count = db.query(DetectionRecord).filter(DetectionRecord.scene == scene_key).delete()

    db.delete(record)
    db.commit()

    return {"success": True, "message": f"场景已删除，同时清理了 {deleted_count} 条检测记录"}


@router.get("/groups")
async def list_groups(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all groups for the current user, with scene counts."""
    user_id = current_user["sub"]
    from app.models.scene_group import SceneGroup
    groups = db.query(SceneGroup).filter(SceneGroup.user_id == user_id).all()
    result = []
    for g in groups:
        custom_count = db.query(CustomScene).filter(CustomScene.group_id == g.id).count()
        from app.models.user_scene_group_mapping import UserSceneGroupMapping
        mapping_count = db.query(UserSceneGroupMapping).filter(
            UserSceneGroupMapping.group_id == g.id
        ).count()
        result.append({
            "id": str(g.id),
            "name": g.name,
            "scene_count": custom_count + mapping_count,
        })
    return {"success": True, "data": result}


@router.post("/groups")
async def create_group(
    name: str = Form(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new group."""
    from app.models.scene_group import SceneGroup
    record = SceneGroup(user_id=current_user["sub"], name=name)
    db.add(record)
    db.commit()
    db.refresh(record)
    return {
        "success": True,
        "data": {"id": str(record.id), "name": record.name, "scene_count": 0},
    }


@router.put("/groups/{group_id}")
async def rename_group(
    group_id: str,
    name: str = Form(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Rename a group."""
    import uuid as uuid_lib
    try:
        uid = uuid_lib.UUID(group_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的分组 ID")
    from app.models.scene_group import SceneGroup
    record = db.query(SceneGroup).filter(SceneGroup.id == uid, SceneGroup.user_id == current_user["sub"]).first()
    if not record:
        raise HTTPException(status_code=404, detail="分组不存在")
    record.name = name
    db.commit()
    return {"success": True, "data": {"id": str(record.id), "name": record.name}}


@router.delete("/groups/{group_id}")
async def delete_group(
    group_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a group. Scenes in the group become ungrouped (group_id = NULL)."""
    import uuid as uuid_lib
    try:
        uid = uuid_lib.UUID(group_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的分组 ID")
    from app.models.scene_group import SceneGroup
    record = db.query(SceneGroup).filter(SceneGroup.id == uid, SceneGroup.user_id == current_user["sub"]).first()
    if not record:
        raise HTTPException(status_code=404, detail="分组不存在")
    # Reassign custom scenes to ungrouped
    db.query(CustomScene).filter(CustomScene.group_id == uid).update({"group_id": None})
    # Remove mappings for built-in scenes
    from app.models.user_scene_group_mapping import UserSceneGroupMapping
    db.query(UserSceneGroupMapping).filter(UserSceneGroupMapping.group_id == uid).delete()
    # Delete group
    db.delete(record)
    db.commit()
    return {"success": True}


@router.get("/marketplace")
async def list_marketplace(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """列出当前用户可获取的公开模型（非自己上传、未获取的）"""
    import uuid as uuid_lib
    user_id = current_user["sub"]

    acquired_ids = [
        a.custom_scene_id
        for a in db.query(AcquiredScene).filter(AcquiredScene.user_id == user_id).all()
    ]

    query = db.query(CustomScene).filter(
        CustomScene.is_public == True,
        CustomScene.status == "active",
        CustomScene.user_id != user_id,
    )
    if acquired_ids:
        query = query.filter(CustomScene.id.notin_(acquired_ids))

    scenes = query.order_by(CustomScene.created_at.desc()).all()

    user_ids = list(set(str(s.user_id) for s in scenes))
    users = {}
    if user_ids:
        for u in db.query(User).filter(User.id.in_([uuid_lib.UUID(uid) for uid in user_ids])).all():
            users[str(u.id)] = u.username

    result = []
    for s in scenes:
        d = _custom_scene_to_dict(s)
        d["creator_name"] = users.get(str(s.user_id), "未知用户")
        d["description"] = s.description or ""
        result.append(d)

    return {"success": True, "data": result}


@router.post("/acquire/{scene_id}")
async def acquire_scene(
    scene_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取一个公开模型：下载 .pt + 创建获取记录"""
    import uuid as uuid_lib
    try:
        uid = uuid_lib.UUID(scene_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的场景 ID")

    scene = db.query(CustomScene).filter(CustomScene.id == uid).first()
    if not scene:
        raise HTTPException(status_code=404, detail="场景不存在")
    if not scene.is_public:
        raise HTTPException(status_code=403, detail="该场景不是公开的")
    if str(scene.user_id) == current_user["sub"]:
        raise HTTPException(status_code=400, detail="不能获取自己的模型")

    existing = db.query(AcquiredScene).filter(
        AcquiredScene.user_id == current_user["sub"],
        AcquiredScene.custom_scene_id == uid,
    ).first()
    if existing:
        return {"success": True, "message": "已获取过该模型"}

    # 下载 .pt 文件（从 MinIO 到本地）
    model_filename = scene.model_filename
    model_path = os.path.join(MODELS_DIR, model_filename)
    if not os.path.exists(model_path):
        from app.utils.minio_client import download_file
        downloaded = download_file(settings.MINIO_BUCKET, model_filename, model_path)
        if not downloaded:
            raise HTTPException(status_code=500, detail="模型文件下载失败")

    record = AcquiredScene(
        user_id=current_user["sub"],
        custom_scene_id=uid,
    )
    db.add(record)
    db.commit()

    return {"success": True, "message": "模型获取成功"}


@router.delete("/acquire/{scene_id}")
async def unacquire_scene(
    scene_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """移除已获取的模型"""
    import uuid as uuid_lib
    try:
        uid = uuid_lib.UUID(scene_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的场景 ID")

    record = db.query(AcquiredScene).filter(
        AcquiredScene.user_id == current_user["sub"],
        AcquiredScene.custom_scene_id == uid,
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="未获取过该模型")

    db.delete(record)
    db.commit()

    return {"success": True, "message": "已移除"}


@router.get("/acquired")
async def list_acquired_scenes(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """列出当前用户已获取的模型（供侧边栏使用）"""
    user_id = current_user["sub"]
    records = db.query(AcquiredScene).filter(
        AcquiredScene.user_id == user_id
    ).order_by(AcquiredScene.created_at.desc()).all()

    scene_ids = [r.custom_scene_id for r in records]
    scenes = db.query(CustomScene).filter(CustomScene.id.in_(scene_ids)).all() if scene_ids else []
    scene_map = {str(s.id): s for s in scenes}

    result = []
    for r in records:
        s = scene_map.get(str(r.custom_scene_id))
        if s:
            scene_key = f"custom_{s.id.hex}"
            result.append({
                "key": scene_key,
                "name": s.name,
                "originalModelName": s.original_model_name or s.name,
                "defaultModel": s.model_filename.replace(".pt", ""),
            })

    return {"success": True, "data": result}


@router.put("/{scene_key}/group")
async def assign_scene_group(
    scene_key: str,
    group_id: str = Form(None),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Assign a scene to a group (or unassign by sending group_id=None)."""
    user_id = current_user["sub"]
    import uuid as uuid_lib
    uid = None
    if group_id:
        try:
            uid = uuid_lib.UUID(group_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="无效的分组 ID")

    if scene_key.startswith("custom_"):
        # Custom scene: update group_id on the DB record directly
        hex_id = scene_key.replace("custom_", "")
        try:
            scene_uid = uuid_lib.UUID(hex_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="无效的场景 ID")
        record = db.query(CustomScene).filter(CustomScene.id == scene_uid).first()
        if not record:
            raise HTTPException(status_code=404, detail="场景不存在")
        record.group_id = uid
        db.commit()
    else:
        # Built-in scene: use mapping table
        from app.models.user_scene_group_mapping import UserSceneGroupMapping
        existing = db.query(UserSceneGroupMapping).filter(
            UserSceneGroupMapping.user_id == user_id,
            UserSceneGroupMapping.scene_key == scene_key,
        ).first()
        if uid:
            if existing:
                existing.group_id = uid
            else:
                mapping = UserSceneGroupMapping(
                    user_id=user_id, scene_key=scene_key, group_id=uid
                )
                db.add(mapping)
        else:
            if existing:
                db.delete(existing)
        db.commit()
    return {"success": True}
