import os
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
import numpy as np
from ultralytics import YOLO
from PIL import Image
import cv2
from app.config import settings
from app.models.schemas import DetectionBox, DetectionResult
from app.utils.file_utils import get_file_url
from app.utils.minio_client import download_model


MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")


class DetectionService:
    def __init__(self):
        self.models: Dict[str, Any] = {}
        self.class_names = {
            0: "rolled-in_scale",
            1: "patches",
            2: "crazing",
            3: "pitted_surface",
            4: "inclusion",
            5: "scratches",
        }

    def _get_model(self, model_name: str):
        if model_name in self.models:
            return self.models[model_name]

        model_filename = f"{model_name}.pt" if not model_name.endswith(".pt") else model_name
        model_path = os.path.join(MODELS_DIR, model_filename)

        if not os.path.exists(model_path):
            print(f"Model not found locally, downloading from MinIO: {model_filename}")
            if not download_model(model_filename, model_path):
                raise FileNotFoundError(
                    f"Model '{model_name}' not found locally and failed to download from MinIO"
                )

        print(f"Loading model: {model_name} from {model_path}")
        model = YOLO(model_path)
        self.models[model_name] = model
        return model

    def get_available_models(self) -> List[str]:
        models = []
        if os.path.isdir(MODELS_DIR):
            for f in os.listdir(MODELS_DIR):
                if f.endswith(".pt"):
                    models.append(f.replace(".pt", ""))
        return sorted(models)

    def _get_class_names(self, model) -> dict:
        """获取模型的 class names 映射，兜底返回硬编码的钢铁缺陷映射"""
        if hasattr(model, "names") and model.names:
            # 检查是否是真正的命名映射（非纯数字索引）
            names = model.names
            sample = next(iter(names.values()), "")
            # 如果 class name 是纯数字字符串（如 "0","1"），说明模型没有真实命名
            if not sample.isdigit():
                return names
        return {
            0: "rolled-in_scale",
            1: "patches",
            2: "crazing",
            3: "pitted_surface",
            4: "inclusion",
            5: "scratches",
        }

    def get_model_class_names(self, model_path: str) -> dict:
        """Load a model and return its class names. Used by custom scene upload."""
        from ultralytics import YOLO
        model = YOLO(model_path)
        return self._get_class_names(model)

    def detect_single_image(self, image_path: str, model_name: str = "yolo11n") -> DetectionResult:
        start_time = time.time()
        detection_id = str(uuid.uuid4())

        model = self._get_model(model_name)
        results = model.predict(
            source=image_path,
            conf=settings.CONFIDENCE_THRESHOLD,
            iou=settings.IOU_THRESHOLD,
            save=False
        )

        boxes = []
        class_names = self._get_class_names(model)
        for result in results:
            for box in result.boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                confidence = float(box.conf[0])
                class_id = int(box.cls[0])
                class_name = class_names.get(class_id, f"class_{class_id}")
                
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
        
        annotated_image = results[0].plot()  # already BGR
        cv2.imwrite(result_path, annotated_image)

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

    def detect_frame(self, image_array: np.ndarray, model_name: str = "yolo11n") -> dict:
        """Lightweight detection for real-time camera frames. No file I/O, no DB."""
        model = self._get_model(model_name)
        results = model.predict(
            source=image_array,
            conf=settings.CONFIDENCE_THRESHOLD,
            iou=settings.IOU_THRESHOLD,
            save=False,
            verbose=False,
        )
        boxes = []
        class_names = self._get_class_names(model)
        for result in results:
            for box in result.boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                boxes.append({
                    "x1": round(x1, 1),
                    "y1": round(y1, 1),
                    "x2": round(x2, 1),
                    "y2": round(y2, 1),
                    "confidence": round(float(box.conf[0]), 4),
                    "class_id": int(box.cls[0]),
                    "class_name": class_names.get(int(box.cls[0]), f"class_{int(box.cls[0])}"),
                })
        return {"boxes": boxes, "total_objects": len(boxes)}

    def detect_video(self, video_path: str, output_dir: str, model_name: str,
                     frame_interval: int = 5, progress_callback=None,
                     max_dim: int = 1280) -> dict:
        start_time = time.time()
        model = self._get_model(model_name)
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video file: {video_path}")

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0:
            fps = 30
        in_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        in_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        scale = min(max_dim / max(in_width, in_height), 1.0)
        if scale < 1.0:
            out_width, out_height = int(in_width * scale), int(in_height * scale)
        else:
            out_width, out_height = in_width, in_height

        codec_attempts = [
            ("vp80", ".webm"),
            ("mp4v", ".mp4"),
            ("avc1", ".mp4"),
            ("XVID", ".avi"),
        ]
        out = None
        output_path = None
        output_filename = None
        for fourcc_str, ext in codec_attempts:
            output_filename = f"video_{uuid.uuid4().hex}{ext}"
            output_path = os.path.join(output_dir, output_filename)
            fourcc = cv2.VideoWriter_fourcc(*fourcc_str)
            out = cv2.VideoWriter(output_path, fourcc, fps, (out_width, out_height))
            if out.isOpened():
                print(f"VideoWriter opened with codec {fourcc_str}, output: {output_filename}")
                break
        if out is None or not out.isOpened():
            cap.release()
            raise RuntimeError(f"Cannot open video writer, tried: {[c for c, _ in codec_attempts]}")

        class_counts: Dict[str, int] = {}
        total_objects = 0
        frames_with_defects = 0
        frame_idx = 0

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                frame_idx += 1

                if scale < 1.0:
                    frame = cv2.resize(frame, (out_width, out_height))

                should_detect = (frame_idx - 1) % frame_interval == 0

                if should_detect:
                    try:
                        results = model.predict(
                            source=frame,
                            conf=settings.CONFIDENCE_THRESHOLD,
                            iou=settings.IOU_THRESHOLD,
                            save=False,
                            verbose=False,
                        )
                        boxes = results[0].boxes
                        if len(boxes) > 0:
                            frames_with_defects += 1
                            annotated = results[0].plot()  # already BGR
                            frame = annotated
                            class_names = self._get_class_names(model)
                            for box in boxes:
                                cls_id = int(box.cls[0])
                                cls_name = class_names.get(cls_id, f"class_{cls_id}")
                                class_counts[cls_name] = class_counts.get(cls_name, 0) + 1
                                total_objects += 1
                    except Exception as e:
                        print(f"Frame {frame_idx} detection failed: {e}")
                        # Fall through to write the original un-annotated frame

                out.write(frame)

                if progress_callback:
                    progress_callback(frame_idx, total_frames)
        finally:
            cap.release()
            out.release()

        detection_time = time.time() - start_time

        return {
            "output_filename": output_filename,
            "output_path": output_path,
            "total_objects": total_objects,
            "class_counts": class_counts,
            "frames_with_defects": frames_with_defects,
            "total_frames": total_frames,
            "processed_frames": frame_idx,
            "detection_time": round(detection_time, 3),
        }


detection_service = DetectionService()