import os
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from app.services.detection_service import detection_service
from app.utils.file_utils import save_upload_file, ensure_directories
from app.config import settings
from app.models.schemas import SingleDetectionResponse, HistoryResponse, TargetListResponse, TargetItem
from datetime import datetime

router = APIRouter(prefix="/detection", tags=["detection"])

ensure_directories()


@router.post("/single", response_model=SingleDetectionResponse)
async def detect_single_image(
    file: UploadFile = File(...),
    model_name: str = Form("pest-v1")
):
    try:
        filename = await save_upload_file(file, settings.UPLOAD_DIR)
        image_path = os.path.join(settings.UPLOAD_DIR, filename)
        
        result = detection_service.detect_single_image(image_path, model_name)
        
        return SingleDetectionResponse(
            success=True,
            message="检测成功",
            data=result
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"检测失败: {str(e)}")


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