import os
import uuid
import json
import csv
import io
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.utils.db import get_db
from app.utils.auth import get_current_user
from app.utils.s3_client import upload_file as s3_upload, download_file as s3_download
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


def _parse_results_csv(contents: bytes) -> dict:
    """Parse Ultralytics results.csv and return best-epoch metrics.

    Returns {precision, recall, map50, map50_95} or empty dict if parsing fails.
    """
    try:
        text = io.StringIO(contents.decode("utf-8"))
        reader = csv.DictReader(text)

        precision_col = recall_col = map50_col = map50_95_col = None
        best = {"precision": 0, "recall": 0, "map50": 0, "map50_95": 0}
        best_map50 = -1

        for row in reader:
            # Find relevant columns on first non-empty row
            if precision_col is None:
                for col in row.keys():
                    col_lower = col.strip().lower()
                    # Match "map50-95" before "map50" to avoid substring collision
                    if "map50-95" in col_lower and "(b)" in col_lower:
                        map50_95_col = col
                    elif "map50" in col_lower and "(b)" in col_lower:
                        map50_col = col
                    elif "precision" in col_lower and "(b)" in col_lower:
                        precision_col = col
                    elif "recall" in col_lower and "(b)" in col_lower:
                        recall_col = col

            try:
                cur_map50 = float(row.get(map50_col or "", 0) or 0)
            except (ValueError, TypeError):
                cur_map50 = 0

            if cur_map50 > best_map50:
                best_map50 = cur_map50
                try:
                    best = {
                        "precision": round(float(row.get(precision_col or "", 0) or 0) * 100, 1),
                        "recall": round(float(row.get(recall_col or "", 0) or 0) * 100, 1),
                        "map50": round(float(row.get(map50_col or "", 0) or 0) * 100, 1),
                        "map50_95": round(float(row.get(map50_95_col or "", 0) or 0) * 100, 1),
                    }
                except (ValueError, TypeError):
                    pass

        if best_map50 >= 0:
            return best
    except Exception:
        pass
    return {}


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
        "user_id": str(scene.user_id) if scene.user_id else None,
        "group_id": str(scene.group_id) if scene.group_id else None,
        "precision": scene.precision,
        "recall": scene.recall,
        "map50": scene.map50,
        "map50_95": scene.map50_95,
    }


@router.post("/upload")
async def upload_scene(
    file: UploadFile = File(...),
    name: str = Form(...),
    is_public: bool = Form(False),
    description: str = Form(""),
    results: UploadFile = File(None),
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
    s3_upload(settings.S3_BUCKET, model_filename, model_path)

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

    # Parse optional results.csv
    metrics = {}
    if results and results.filename and results.filename.endswith(".csv"):
        csv_contents = await results.read()
        metrics = _parse_results_csv(csv_contents)

    # Save to DB
    record = CustomScene(
        user_id=current_user["sub"],
        name=name,
        model_filename=model_filename,
        original_model_name=original_name,
        class_names=class_names,
        description=description,
        is_public=is_public,
        precision=metrics.get("precision"),
        recall=metrics.get("recall"),
        map50=metrics.get("map50"),
        map50_95=metrics.get("map50_95"),
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

    # Add creator_name for all custom scenes
    user_ids = set(str(s.user_id) for s in custom if s.user_id)
    users = {}
    if user_ids:
        for u in db.query(User).filter(User.id.in_([uuid.UUID(uid) for uid in user_ids])).all():
            users[str(u.id)] = u.username

    custom_dicts = []
    for s in custom:
        d = _custom_scene_to_dict(s)
        d["creator_name"] = users.get(str(s.user_id), "未知用户")
        custom_dicts.append(d)

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
        "data": builtins + custom_dicts,
    }


@router.put("/{scene_id}")
async def update_scene(
    scene_id: str,
    name: str = Form(None),
    description: str = Form(None),
    is_public: bool = Form(None),
    file: UploadFile = File(None),
    results: UploadFile = File(None),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a custom scene: name, description, is_public, optionally replace model file or results.csv."""
    import uuid as uuid_lib
    try:
        uid = uuid_lib.UUID(scene_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的场景 ID")

    record = db.query(CustomScene).filter(CustomScene.id == uid).first()
    if not record:
        raise HTTPException(status_code=404, detail="场景不存在")
    if str(record.user_id) != current_user["sub"]:
        raise HTTPException(status_code=403, detail="只能编辑自己的场景")

    if name is not None:
        record.name = name
    if description is not None:
        record.description = description
    if is_public is not None:
        record.is_public = is_public

    # Optional: replace model file
    if file and file.filename:
        if not file.filename.endswith(".pt"):
            raise HTTPException(status_code=400, detail="仅支持 .pt 模型文件")

        # Delete old model files
        old_model_path = os.path.join(MODELS_DIR, record.model_filename)
        if os.path.exists(old_model_path):
            os.remove(old_model_path)
        from app.utils.s3_client import delete_file as s3_delete
        s3_delete(settings.S3_BUCKET, record.model_filename)

        # Save new model file (keep same filename to preserve scene key)
        contents = await file.read()
        with open(old_model_path, "wb") as f:
            f.write(contents)

        # Upload to MinIO
        from app.utils.s3_client import upload_file as s3_upload
        s3_upload(settings.S3_BUCKET, record.model_filename, old_model_path)

        # Extract class names from new model
        try:
            class_names = detection_service.get_model_class_names(old_model_path)
            record.class_names = class_names
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"无法读取新模型: {str(e)}")

        # Update original model name
        original_name = (file.filename or "").replace(".pt", "")
        record.original_model_name = original_name

    # Optional: parse new results.csv
    if results and results.filename and results.filename.endswith(".csv"):
        csv_contents = await results.read()
        metrics = _parse_results_csv(csv_contents)
        record.precision = metrics.get("precision")
        record.recall = metrics.get("recall")
        record.map50 = metrics.get("map50")
        record.map50_95 = metrics.get("map50_95")

    db.commit()
    db.refresh(record)

    return {
        "success": True,
        "message": "场景更新成功",
        "data": _custom_scene_to_dict(record),
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

    from app.utils.s3_client import delete_file as s3_delete
    s3_delete(settings.S3_BUCKET, record.model_filename)

    # Delete related detection history
    scene_key = f"custom_{record.id.hex}"
    from app.models.detection import DetectionRecord
    deleted_count = db.query(DetectionRecord).filter(DetectionRecord.scene == scene_key).delete()

    db.delete(record)
    db.commit()

    return {"success": True, "message": f"场景已删除，同时清理了 {deleted_count} 条检测记录"}


@router.get("/{scene_id}/download")
async def download_scene_model(
    scene_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Download the .pt model file for a custom scene."""
    import uuid as uuid_lib
    try:
        uid = uuid_lib.UUID(scene_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的场景 ID")

    record = db.query(CustomScene).filter(CustomScene.id == uid).first()
    if not record:
        raise HTTPException(status_code=404, detail="场景不存在")

    # Check access: owner or acquired
    from app.models.acquired_scene import AcquiredScene
    is_owner = str(record.user_id) == current_user["sub"]
    is_acquired = db.query(AcquiredScene).filter(
        AcquiredScene.user_id == current_user["sub"],
        AcquiredScene.custom_scene_id == uid,
    ).first() is not None

    if not is_owner and not is_acquired and not record.is_public:
        raise HTTPException(status_code=403, detail="无权下载该模型")

    # Ensure model file exists locally, download from MinIO if needed
    model_path = os.path.join(MODELS_DIR, record.model_filename)
    if not os.path.exists(model_path):
        ok = s3_download(settings.S3_BUCKET, record.model_filename, model_path)
        if not ok:
            raise HTTPException(status_code=500, detail="模型文件下载失败")

    # Determine display filename
    original_name = record.original_model_name or record.name
    download_name = original_name + ".pt"

    return StreamingResponse(
        open(model_path, "rb"),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{download_name}"',
        },
    )


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

    user_ids = list(set(str(s.user_id) for s in scenes if s.user_id))
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
        from app.utils.s3_client import download_file
        downloaded = download_file(settings.S3_BUCKET, model_filename, model_path)
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
    """列出当前用户已获取的模型（供侧边栏使用），包括已被管理员删除的场景"""
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
                "status": s.status,
                "deleted": False,
                "scene_id": str(s.id),
            })
        else:
            # Orphaned AcquiredScene — model was deleted by admin
            result.append({
                "key": f"orphaned_{r.id.hex}",
                "name": "（已删除的模型）",
                "originalModelName": "已删除",
                "defaultModel": "",
                "deleted": True,
                "acquired_scene_id": str(r.custom_scene_id),
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
