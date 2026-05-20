import os
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
from ultralytics import YOLO
from PIL import Image
import cv2
from app.config import settings
from app.models.schemas import DetectionBox, DetectionResult
from app.utils.file_utils import get_file_url


class DetectionService:
    def __init__(self):
        self.model = None
        self.class_names = {}
        self._load_model()
        self._init_class_names()

    def _load_model(self):
        if os.path.exists(settings.YOLO_MODEL_PATH):
            self.model = YOLO(settings.YOLO_MODEL_PATH)
        else:
            raise FileNotFoundError(f"Model file not found: {settings.YOLO_MODEL_PATH}")

    def _init_class_names(self):
        self.class_names = {
            0: "person",
            1: "bicycle",
            2: "car",
            3: "motorcycle",
            4: "airplane",
            5: "bus",
            # ... 更多类别
        }

    def detect_single_image(self, image_path: str, model_name: str = "pest-v1") -> DetectionResult:
        start_time = time.time()
        detection_id = str(uuid.uuid4())

        results = self.model.predict(
            source=image_path,
            conf=settings.CONFIDENCE_THRESHOLD,
            iou=settings.IOU_THRESHOLD,
            save=False
        )

        boxes = []
        for result in results:
            for box in result.boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                confidence = float(box.conf[0])
                class_id = int(box.cls[0])
                class_name = self.class_names.get(class_id, f"class_{class_id}")
                
                boxes.append(DetectionBox(
                    x1=x1,
                    y1=y1,
                    x2=x2,
                    y2=y2,
                    confidence=confidence,
                    class_id=class_id,
                    class_name=class_name
                ))

        result_filename = f"result_{uuid.uuid4().hex}.jpg"
        result_path = os.path.join(settings.RESULT_DIR, result_filename)
        
        annotated_image = results[0].plot()
        cv2.imwrite(result_path, cv2.cvtColor(annotated_image, cv2.COLOR_RGB2BGR))

        detection_time = time.time() - start_time

        image_filename = os.path.basename(image_path)

        return DetectionResult(
            detection_id=detection_id,
            image_url=get_file_url(image_filename, settings.UPLOAD_DIR),
            result_image_url=get_file_url(result_filename, settings.RESULT_DIR),
            boxes=boxes,
            total_objects=len(boxes),
            detection_time=round(detection_time, 3),
            model_name=model_name,
            created_at=datetime.now()
        )


detection_service = DetectionService()