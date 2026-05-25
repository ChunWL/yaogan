import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
import uuid
import time
import atexit
import signal
import traceback

def main():
    video_path = sys.argv[1]
    task_id = sys.argv[2]
    model_name = sys.argv[3]
    scene = sys.argv[4]
    frame_interval = int(sys.argv[5])
    user_id = sys.argv[6]
    output_dir = sys.argv[7]
    status_file = sys.argv[8]

    def write_status(status, **kwargs):
        data = {}
        if os.path.exists(status_file):
            try:
                with open(status_file, "r") as f:
                    data = json.load(f)
            except Exception:
                pass
        data["status"] = status
        data.update(kwargs)
        with open(status_file, "w") as f:
            json.dump(data, f)

    def on_crash():
        write_status("failed", message="进程异常终止")

    atexit.register(on_crash)
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda s, f: sys.exit(1))

    stderr_log = os.path.join(os.path.dirname(status_file), f"{task_id}.log")
    sys.stderr = open(stderr_log, "w")

    try:
        write_status("processing", progress=0.0, processed_frames=0, total_frames=0)

        from app.services.detection_service import DetectionService
        from app.config import settings

        service = DetectionService()

        _last_progress_frame = [0]  # mutable closure for throttle
        def progress_callback(processed, total):
            # Throttle: only write to status file every 10 frames to reduce I/O
            if processed - _last_progress_frame[0] < 10 and processed < total:
                return
            _last_progress_frame[0] = processed
            progress = round(processed / total * 100, 1) if total > 0 else 0
            write_status("processing", progress=progress,
                        processed_frames=processed, total_frames=total)

        result = service.detect_video(
            video_path=video_path,
            output_dir=output_dir,
            model_name=model_name,
            frame_interval=frame_interval,
            progress_callback=progress_callback,
        )

        from app.utils.db import SessionLocal
        from app.models.detection import DetectionRecord
        from app.models.user import User  # ensure FK table metadata is loaded
        db = SessionLocal()
        try:
            video_filename = os.path.basename(video_path)
            record = DetectionRecord(
                id=uuid.uuid4(),
                user_id=user_id,
                filename=video_filename,
                image_url=f"/static/uploads/{video_filename}",
                result_image_url=f"/static/videos/{result['output_filename']}",
                image_path=video_path,
                result_path=result["output_path"],
                total_objects=result["total_objects"],
                detection_time=result["detection_time"],
                model_name=model_name,
                status="completed",
                type="video",
                scene=scene,
                defect_results=[{"class_name": cls_name} for cls_name in result["class_counts"].keys()],
            )
            db.add(record)
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

        write_status("completed", progress=100.0,
                    processed_frames=result["processed_frames"],
                    total_frames=result["total_frames"],
                    result_video_url=f"/static/videos/{result['output_filename']}",
                    summary={
                        "total_objects": result["total_objects"],
                        "class_counts": result["class_counts"],
                        "frames_with_defects": result["frames_with_defects"],
                        "detection_time": result["detection_time"],
                        "total_frames": result["total_frames"],
                        "processed_frames": result["processed_frames"],
                        "per_frame_json_url": f"/static/videos/{result['per_frame_filename']}" if result.get("per_frame_filename") else "",
                    })

    except Exception:
        write_status("failed", message=traceback.format_exc())
    finally:
        atexit.unregister(on_crash)
        sys.stderr.close()


if __name__ == "__main__":
    main()
