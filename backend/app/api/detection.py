import os
import sys
import json
import uuid
import threading
import traceback
import subprocess
from typing import List
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from app.services.detection_service import detection_service
from app.utils.file_utils import save_upload_file, ensure_directories, get_file_url
from app.utils.db import get_db, SessionLocal
from app.utils.auth import get_current_user
from app.config import settings
from app.models.schemas import (
    SingleDetectionResponse, HistoryResponse, HistoryItem,
    TargetListResponse, TargetItem, HistoryDetailResponse,
    DetectionBox, DetectionResult, MessageResponse,
    BatchResultItem, BatchDetectionResponse,
    VideoTaskResponse, VideoProgressResponse,
)
from app.models.detection import DetectionRecord

router = APIRouter(prefix="/detection", tags=["detection"])

ensure_directories()

CLASS_NAME_ZH = {
    "rolled-in_scale": "轧制氧化皮",
    "patches": "斑块",
    "crazing": "开裂",
    "pitted_surface": "点蚀表面",
    "inclusion": "内含物",
    "scratches": "划痕",
}




ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm"}

TASKS_DIR = os.path.join(settings.VIDEO_RESULT_DIR, ".tasks")


def _get_task_file(task_id: str) -> str:
    return os.path.join(TASKS_DIR, f"{task_id}.json")


def _read_task(task_id: str) -> dict | None:
    task_file = _get_task_file(task_id)
    if not os.path.exists(task_file):
        return None
    with open(task_file, "r") as f:
        return json.load(f)


def _write_task(task_id: str, **kwargs):
    data = {}
    task_file = _get_task_file(task_id)
    if os.path.exists(task_file):
        try:
            with open(task_file, "r") as f:
                data = json.load(f)
        except Exception:
            pass
    data.update(kwargs)
    with open(task_file, "w") as f:
        json.dump(data, f)


def _run_video_subprocess(task_id: str, video_path: str, model_name: str,
                          frame_interval: int, user_id: str):
    os.makedirs(TASKS_DIR, exist_ok=True)
    status_file = _get_task_file(task_id)
    _write_task(task_id, status="processing", progress=0.0,
                processed_frames=0, total_frames=0,
                result_video_url=None, summary=None, message=None, user_id=user_id)

    api_dir = os.path.dirname(os.path.abspath(__file__))       # .../backend/app/api
    app_dir = os.path.dirname(api_dir)                          # .../backend/app
    backend_dir = os.path.dirname(app_dir)                      # .../backend
    python_exe = os.path.join(backend_dir, ".venv", "bin", "python3")
    if not os.path.exists(python_exe):
        python_exe = sys.executable

    task_script = os.path.join(app_dir, "process_video_task.py")

    cmd = [
        python_exe, task_script,
        video_path, task_id, model_name, str(frame_interval),
        user_id, settings.VIDEO_RESULT_DIR, status_file,
    ]

    subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
        cwd=backend_dir,
    )


@router.post("/single", response_model=SingleDetectionResponse)
async def detect_single_image(
    file: UploadFile = File(...),
    model_name: str = Form("yolo11n"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        original_filename = file.filename
        saved_filename = await save_upload_file(file, settings.UPLOAD_DIR)
        image_path = os.path.join(settings.UPLOAD_DIR, saved_filename)

        result = detection_service.detect_single_image(image_path, model_name)

        result_filename = os.path.basename(result.result_image_url)
        result_path = os.path.join(settings.RESULT_DIR, result_filename)

        detected_class_names = list(set(box.class_name for box in result.boxes))
        detected_targets = [CLASS_NAME_ZH.get(name, name) for name in detected_class_names]

        defect_results = [
            {
                "x1": box.x1,
                "y1": box.y1,
                "x2": box.x2,
                "y2": box.y2,
                "confidence": box.confidence,
                "class_id": box.class_id,
                "class_name": box.class_name,
            }
            for box in result.boxes
        ]

        record = DetectionRecord(
            id=result.detection_id,
            user_id=current_user["sub"],
            filename=original_filename,
            image_url=result.image_url,
            result_image_url=result.result_image_url,
            image_path=image_path,
            result_path=result_path,
            total_objects=result.total_objects,
            detection_time=result.detection_time,
            model_name=result.model_name,
            status="completed",
            type="single",
            defect_results=defect_results,
            created_at=result.created_at,
        )
        db.add(record)
        db.commit()

        return SingleDetectionResponse(
            success=True,
            message="检测成功",
            data=result
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"检测失败: {str(e)}")


@router.post("/batch", response_model=BatchDetectionResponse)
async def detect_batch_images(
    files: List[UploadFile] = File(...),
    model_name: str = Form("yolo11n"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if len(files) > 20:
        raise HTTPException(status_code=400, detail="最多支持20张图片")
    if len(files) == 0:
        raise HTTPException(status_code=400, detail="请至少选择一张图片")

    results = []
    for file in files:
        try:
            original_filename = file.filename
            saved_filename = await save_upload_file(file, settings.UPLOAD_DIR)
            image_path = os.path.join(settings.UPLOAD_DIR, saved_filename)

            result = detection_service.detect_single_image(image_path, model_name)

            result_filename = os.path.basename(result.result_image_url)
            result_path = os.path.join(settings.RESULT_DIR, result_filename)

            detected_class_names = list(set(box.class_name for box in result.boxes))
            detected_targets = [CLASS_NAME_ZH.get(name, name) for name in detected_class_names]

            defect_results = [
                {
                    "x1": box.x1, "y1": box.y1, "x2": box.x2, "y2": box.y2,
                    "confidence": box.confidence, "class_id": box.class_id, "class_name": box.class_name,
                }
                for box in result.boxes
            ]

            record = DetectionRecord(
                id=result.detection_id,
                user_id=current_user["sub"],
                filename=original_filename,
                image_url=result.image_url,
                result_image_url=result.result_image_url,
                image_path=image_path,
                result_path=result_path,
                total_objects=result.total_objects,
                detection_time=result.detection_time,
                model_name=result.model_name,
                status="completed",
                type="batch",
                defect_results=defect_results,
                created_at=result.created_at,
            )
            db.add(record)
            db.commit()

            results.append(BatchResultItem(filename=original_filename, success=True, result=result))
        except Exception as e:
            db.rollback()
            results.append(BatchResultItem(filename=file.filename, success=False))

    return BatchDetectionResponse(
        success=True,
        message=f"批量检测完成，共处理 {len(files)} 张图片",
        data=results,
        total=len(results),
    )


@router.post("/video/test", response_model=VideoTaskResponse)
async def detect_video_test():
    """测试端点：模拟视频检测，不跑 YOLO，排查崩溃原因"""
    task_id = uuid.uuid4().hex
    os.makedirs(TASKS_DIR, exist_ok=True)
    _write_task(task_id, status="processing", progress=0.0,
                processed_frames=0, total_frames=100,
                result_video_url=None, summary=None, message=None, user_id="test")

    def simulate():
        import time
        try:
            for i in range(1, 101):
                time.sleep(1)
                progress = i
                _write_task(task_id, status="processing", progress=progress,
                            processed_frames=i, total_frames=100)
            _write_task(task_id, status="completed", progress=100.0,
                        processed_frames=100, total_frames=100,
                        result_video_url="/static/videos/test.webm",
                        summary={"total_objects": 10, "class_counts": {"test": 10},
                                 "frames_with_defects": 5, "detection_time": 100.0,
                                 "total_frames": 100, "processed_frames": 100})
        except Exception as e:
            _write_task(task_id, status="failed", message=str(e))

    thread = threading.Thread(target=simulate, daemon=True)
    thread.start()

    return VideoTaskResponse(
        task_id=task_id,
        status="processing",
        message="测试任务已启动（无GPU）",
    )


@router.post("/video/test-gpu", response_model=VideoTaskResponse)
async def detect_video_test_gpu():
    """测试端点：真正跑 GPU 检测，验证 API 线程内 GPU 推理是否导致崩溃"""
    task_id = uuid.uuid4().hex
    os.makedirs(TASKS_DIR, exist_ok=True)
    _write_task(task_id, status="processing", progress=0.0,
                processed_frames=0, total_frames=0,
                result_video_url=None, summary=None, message=None, user_id="test")

    def run_gpu():
        try:
            from app.services.detection_service import detection_service
            video_dir = settings.UPLOAD_DIR
            videos = [f for f in os.listdir(video_dir) if f.endswith('.mp4')]
            if not videos:
                _write_task(task_id, status="failed", message="No video file found")
                return
            video_path = os.path.join(video_dir, videos[0])

            _write_task(task_id, status="processing", progress=0.0)

            def progress_cb(processed, total):
                pct = round(processed / total * 100, 1) if total > 0 else 0
                if processed % 10 == 0 or processed >= total:
                    _write_task(task_id, status="processing", progress=pct,
                                processed_frames=processed, total_frames=total)

            result = detection_service.detect_video(
                video_path=video_path,
                output_dir=settings.VIDEO_RESULT_DIR,
                model_name="yolo11n",
                frame_interval=5,
                progress_callback=progress_cb,
            )
            _write_task(task_id, status="completed", progress=100.0,
                        processed_frames=result["processed_frames"],
                        total_frames=result["total_frames"],
                        result_video_url=f"/static/videos/{result['output_filename']}",
                        summary={
                            "total_objects": result["total_objects"],
                            "class_counts": result["class_counts"],
                            "detection_time": result["detection_time"],
                        })
        except Exception as e:
            import traceback
            _write_task(task_id, status="failed", message=traceback.format_exc())

    thread = threading.Thread(target=run_gpu, daemon=True)
    thread.start()

    return VideoTaskResponse(
        task_id=task_id,
        status="processing",
        message="GPU 检测测试任务已启动",
    )


@router.post("/video", response_model=VideoTaskResponse)
async def detect_video(
    file: UploadFile = File(...),
    model_name: str = Form("yolo11n"),
    frame_interval: int = Form(5),
    current_user: dict = Depends(get_current_user),
):
    ext = os.path.splitext(file.filename or "video.mp4")[1].lower()
    if ext not in ALLOWED_VIDEO_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"不支持的视频格式: {ext}，支持 {', '.join(ALLOWED_VIDEO_EXTENSIONS)}")

    task_id = uuid.uuid4().hex
    saved_filename = await save_upload_file(file, settings.UPLOAD_DIR)
    video_path = os.path.join(settings.UPLOAD_DIR, saved_filename)

    _run_video_subprocess(task_id, video_path, model_name,
                          frame_interval, current_user["sub"])

    return VideoTaskResponse(
        task_id=task_id,
        status="processing",
        message="视频检测任务已启动",
    )


@router.get("/video/progress/{task_id}", response_model=VideoProgressResponse)
async def get_video_progress(
    task_id: str,
    current_user: dict = Depends(get_current_user),
):
    task = _read_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在或已过期")
    if task.get("user_id") != current_user["sub"] and task.get("user_id") != "test":
        raise HTTPException(status_code=404, detail="任务不存在或已过期")

    return VideoProgressResponse(
        task_id=task_id,
        status=task["status"],
        progress=task.get("progress", 0),
        processed_frames=task.get("processed_frames", 0),
        total_frames=task.get("total_frames", 0),
        result_video_url=task.get("result_video_url"),
        summary=task.get("summary"),
        message=task.get("message"),
    )


@router.get("/history", response_model=HistoryResponse)
async def get_detection_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    status: str = Query(""),
    type: str = Query(""),
    keyword: str = Query(""),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(DetectionRecord).filter(
        DetectionRecord.user_id == current_user["sub"]
    )

    if status:
        query = query.filter(DetectionRecord.status == status)
    if type:
        query = query.filter(DetectionRecord.type == type)
    if keyword:
        query = query.filter(DetectionRecord.filename.ilike(f"%{keyword}%"))

    total = query.count()
    records = (
        query.order_by(DetectionRecord.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = []
    for r in records:
        detected_class_names = list(set(
            item["class_name"] for item in (r.defect_results or [])
        ))
        detected_targets = [CLASS_NAME_ZH.get(name, name) for name in detected_class_names]

        items.append(HistoryItem(
            id=str(r.id),
            filename=r.filename,
            image=r.result_image_url,
            image_url=r.image_url,
            result_image_url=r.result_image_url,
            type=r.type,
            status=r.status,
            time=r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else "",
            count=1,
            targets=r.total_objects,
            detectedTargets=detected_targets,
        ))

    return HistoryResponse(
        success=True,
        message="获取成功",
        data=items,
        total=total,
    )


@router.get("/detail/{record_id}", response_model=HistoryDetailResponse)
async def get_detection_detail(
    record_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = (
        db.query(DetectionRecord)
        .filter(
            DetectionRecord.id == record_id,
            DetectionRecord.user_id == current_user["sub"],
        )
        .first()
    )

    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")

    boxes = []
    if record.type != "video":
        for item in (record.defect_results or []):
            boxes.append(DetectionBox(
                x1=item["x1"],
                y1=item["y1"],
                x2=item["x2"],
                y2=item["y2"],
                confidence=item["confidence"],
                class_id=item["class_id"],
                class_name=item["class_name"],
            ))

    result = DetectionResult(
        detection_id=str(record.id),
        image_url=record.image_url,
        result_image_url=record.result_image_url,
        boxes=boxes,
        total_objects=record.total_objects,
        detection_time=record.detection_time,
        model_name=record.model_name,
        created_at=record.created_at,
    )

    return HistoryDetailResponse(
        success=True,
        message="获取成功",
        data=result,
    )


@router.delete("/history/{record_id}", response_model=MessageResponse)
async def delete_detection_record(
    record_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = (
        db.query(DetectionRecord)
        .filter(
            DetectionRecord.id == record_id,
            DetectionRecord.user_id == current_user["sub"],
        )
        .first()
    )

    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")

    for file_path in [record.image_path, record.result_path]:
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass

    db.delete(record)
    db.commit()

    return MessageResponse(
        success=True,
        message="删除成功",
    )


@router.get("/targets/list", response_model=TargetListResponse)
async def get_target_list():
    targets = [
        TargetItem(id=0, name="rolled-in_scale", chinese_name="轧制氧化皮", description="钢铁表面氧化皮缺陷"),
        TargetItem(id=1, name="patches", chinese_name="斑块", description="表面不规则斑块"),
        TargetItem(id=2, name="crazing", chinese_name="开裂", description="表面裂纹缺陷"),
        TargetItem(id=3, name="pitted_surface", chinese_name="点蚀表面", description="表面点状腐蚀"),
        TargetItem(id=4, name="inclusion", chinese_name="内含物", description="材料内部夹杂物"),
        TargetItem(id=5, name="scratches", chinese_name="划痕", description="表面机械划痕"),
    ]
    return TargetListResponse(
        success=True,
        message="获取成功",
        data=targets
    )
