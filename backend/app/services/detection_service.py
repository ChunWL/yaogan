import os
import json
import subprocess
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

    # Color palette for detection boxes (BGR)
    BOX_COLORS = [
        (0, 255, 0),      # green
        (255, 0, 0),      # blue
        (0, 128, 255),    # orange
        (255, 0, 255),    # magenta
        (0, 255, 255),    # yellow
        (255, 128, 0),    # light blue
        (128, 0, 255),    # purple
        (0, 255, 128),    # lime
    ]

    def _draw_boxes(self, frame: np.ndarray, boxes_data: list) -> np.ndarray:
        """Draw detection boxes on frame with consistent style."""
        for b in boxes_data:
            x1 = int(b["x1"]); y1 = int(b["y1"])
            x2 = int(b["x2"]); y2 = int(b["y2"])
            cls_id = b.get("class_id", 0)
            color = self.BOX_COLORS[cls_id % len(self.BOX_COLORS)]

            # Rectangle outline
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

            # Label
            label = f"{b['class_name']} {b['confidence']:.2f}"
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)

            # Label background (filled)
            cv2.rectangle(frame, (x1, y1 - th - 6), (x1 + tw + 4, y1), color, -1)
            # Label text
            cv2.putText(frame, label, (x1 + 2, y1 - 3),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        return frame

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

        class_counts: Dict[str, int] = {}
        total_objects = 0
        frames_with_defects = 0
        frame_idx = 0
        per_frame_data = []
        prev_detection_boxes = []

        # Use imageio-ffmpeg's bundled ffmpeg for H.264 encoding (fast + browser-compatible)
        try:
            import imageio_ffmpeg
            ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            ffmpeg_bin = "ffmpeg"

        output_filename = f"video_{uuid.uuid4().hex}.mp4"
        output_path = os.path.join(output_dir, output_filename)
        ffmpeg_cmd = [
            ffmpeg_bin, '-y',
            '-f', 'rawvideo',
            '-pix_fmt', 'bgr24',
            '-s', f'{out_width}x{out_height}',
            '-r', str(fps),
            '-i', '-',
            '-c:v', 'libx264',
            '-preset', 'ultrafast',
            '-crf', '28',
            '-pix_fmt', 'yuv420p',
            output_path,
        ]
        ffmpeg_proc = subprocess.Popen(
            ffmpeg_cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL
        )

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
                        class_names = self._get_class_names(model)
                        frame_class_counts = {}
                        prev_detection_boxes = []
                        if len(boxes) > 0:
                            frames_with_defects += 1
                            for box in boxes:
                                cls_id = int(box.cls[0])
                                cls_name = class_names.get(cls_id, f"class_{cls_id}")
                                class_counts[cls_name] = class_counts.get(cls_name, 0) + 1
                                total_objects += 1
                                frame_class_counts[cls_name] = frame_class_counts.get(cls_name, 0) + 1
                                x1, y1, x2, y2 = box.xyxy[0].tolist()
                                prev_detection_boxes.append({
                                    "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                                    "class_name": cls_name,
                                    "confidence": round(float(box.conf[0]), 4),
                                    "class_id": cls_id,
                                })
                        per_frame_data.append({
                            "frame_index": frame_idx,
                            "total_objects": len(boxes),
                            "class_counts": frame_class_counts,
                        })
                    except Exception as e:
                        print(f"Frame {frame_idx} detection failed: {e}")
                        prev_detection_boxes = []
                        per_frame_data.append({
                            "frame_index": frame_idx,
                            "total_objects": 0,
                            "class_counts": {},
                        })

                # Draw boxes with consistent style on every frame
                if prev_detection_boxes:
                    self._draw_boxes(frame, prev_detection_boxes)

                # Pipe raw frame to ffmpeg for H.264 encoding
                ffmpeg_proc.stdin.write(frame.tobytes())

                if progress_callback:
                    progress_callback(frame_idx, total_frames)
        finally:
            cap.release()
            ffmpeg_proc.stdin.close()
            ffmpeg_proc.wait()

        # Save per-frame data as JSON sidecar
        per_frame_filename = f"{os.path.splitext(output_filename)[0]}.json"
        per_frame_path = os.path.join(output_dir, per_frame_filename)
        try:
            with open(per_frame_path, "w") as f:
                json.dump({
                    "fps": fps,
                    "frame_interval": frame_interval,
                    "total_frames": total_frames,
                    "frames": per_frame_data,
                }, f)
        except Exception as e:
            print(f"Failed to save per-frame data: {e}")
            per_frame_filename = ""

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
            "per_frame_filename": per_frame_filename,
        }


detection_service = DetectionService()