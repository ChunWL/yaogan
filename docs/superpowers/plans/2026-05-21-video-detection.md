# Video Detection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement video detection tab: user uploads video → backend processes frames with YOLO at configurable intervals → returns annotated video + defect summary.

**Architecture:** Backend accepts video via new `/detection/video` endpoint, processes asynchronously in a background thread (cv2 frame reading + YOLO inference every N frames + cv2 VideoWriter output), exposes progress via `/detection/video/progress/{task_id}`. Frontend polls progress every 500ms, shows progress bar during processing, then displays `<video>` player with annotated result + summary panel.

**Tech Stack:** Python FastAPI (threading), OpenCV (cv2), Ultralytics YOLO, Vue 3 + Element Plus

---

### Task 1: Add video config and ensure output directory

**Files:**
- Modify: `backend/app/config.py`
- Modify: `backend/app/utils/file_utils.py`

- [ ] **Step 1: Add video settings to config.py**

```python
# In class Settings(BaseModel), add after RESULT_DIR:
    VIDEO_RESULT_DIR: str = "static/results/videos"
    VIDEO_FRAME_INTERVAL: int = 5
    VIDEO_TASK_TIMEOUT: int = 300
```

- [ ] **Step 2: Add VIDEO_RESULT_DIR to ensure_directories in file_utils.py**

```python
def ensure_directories():
    os.makedirs(settings.STATIC_DIR, exist_ok=True)
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs(settings.RESULT_DIR, exist_ok=True)
    os.makedirs(settings.VIDEO_RESULT_DIR, exist_ok=True)
```

---

### Task 2: Add video response schemas

**Files:**
- Modify: `backend/app/models/schemas.py`

- [ ] **Step 1: Add VideoTaskResponse and VideoProgressResponse at end of schemas.py**

```python
class VideoTaskResponse(BaseModel):
    task_id: str
    status: str
    message: str


class VideoProgressResponse(BaseModel):
    task_id: str
    status: str
    progress: float = 0.0
    processed_frames: int = 0
    total_frames: int = 0
    result_video_url: Optional[str] = None
    summary: Optional[dict] = None
    message: Optional[str] = None
```

---

### Task 3: Add detect_video method to DetectionService

**Files:**
- Modify: `backend/app/services/detection_service.py`

- [ ] **Step 1: Add `detect_video` method to the `DetectionService` class, after `detect_single_image`**

```python
    def detect_video(self, video_path: str, output_dir: str, model_name: str,
                     frame_interval: int = 5, progress_callback=None) -> dict:
        start_time = time.time()
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video file: {video_path}")

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0:
            fps = 30
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        output_filename = f"video_{uuid.uuid4().hex}.mp4"
        output_path = os.path.join(output_dir, output_filename)

        fourcc = cv2.VideoWriter_fourcc(*'avc1')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        if not out.isOpened():
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        class_counts: Dict[str, int] = {}
        total_objects = 0
        frames_with_defects = 0
        frame_idx = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_idx += 1
            should_detect = (frame_idx - 1) % frame_interval == 0

            if should_detect:
                results = self.model.predict(
                    source=frame,
                    conf=settings.CONFIDENCE_THRESHOLD,
                    iou=settings.IOU_THRESHOLD,
                    save=False,
                    verbose=False,
                )
                boxes = results[0].boxes
                if len(boxes) > 0:
                    frames_with_defects += 1
                    annotated = results[0].plot()
                    frame = cv2.cvtColor(annotated, cv2.COLOR_RGB2BGR)
                    for box in boxes:
                        cls_id = int(box.cls[0])
                        cls_name = self.class_names.get(cls_id, f"class_{cls_id}")
                        class_counts[cls_name] = class_counts.get(cls_name, 0) + 1
                        total_objects += 1

            out.write(frame)

            if progress_callback:
                progress_callback(frame_idx, total_frames)

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
```

Add `import threading` at the top of detection_service.py is not needed — it's used in detection.py where the background thread is created.

---

### Task 4: Add video API endpoints and async task management

**Files:**
- Modify: `backend/app/api/detection.py`

- [ ] **Step 1: Add imports at top of detection.py**

Add `import threading` at line 1 (with other stdlib imports), and add `VideoTaskResponse, VideoProgressResponse` to the schema imports at line 11-15:

```python
import os
import threading
import uuid
from typing import List
```

And update the schemas import to include:
```python
from app.models.schemas import (
    SingleDetectionResponse, HistoryResponse, HistoryItem,
    TargetListResponse, TargetItem, HistoryDetailResponse,
    DetectionBox, DetectionResult, MessageResponse,
    BatchResultItem, BatchDetectionResponse,
    VideoTaskResponse, VideoProgressResponse,
)
```

Also add `from app.utils.file_utils import get_file_url` to the import at line 6 (it currently only imports `save_upload_file, ensure_directories`):

```python
from app.utils.file_utils import save_upload_file, ensure_directories, get_file_url
```

- [ ] **Step 2: Add video_tasks dict and background processing function, after the CLASS_NAME_ZH dict (after line 29)**

```python
video_tasks: dict = {}
video_tasks_lock = threading.Lock()

ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm"}


def _process_video_task(task_id: str, video_path: str, model_name: str, frame_interval: int, user_id: str):
    try:
        def update_progress(processed, total):
            with video_tasks_lock:
                video_tasks[task_id]["processed_frames"] = processed
                video_tasks[task_id]["total_frames"] = total
                video_tasks[task_id]["progress"] = round(processed / total * 100, 1) if total > 0 else 0

        result = detection_service.detect_video(
            video_path=video_path,
            output_dir=settings.VIDEO_RESULT_DIR,
            model_name=model_name,
            frame_interval=frame_interval,
            progress_callback=update_progress,
        )

        from app.utils.db import SessionLocal
        from app.models.detection import DetectionRecord
        db = SessionLocal()
        try:
            video_filename = os.path.basename(video_path)
            record = DetectionRecord(
                id=uuid.uuid4(),
                user_id=user_id,
                filename=video_filename,
                image_url=get_file_url(video_filename, settings.UPLOAD_DIR),
                result_image_url=get_file_url(result["output_filename"], settings.VIDEO_RESULT_DIR),
                image_path=video_path,
                result_path=result["output_path"],
                total_objects=result["total_objects"],
                detection_time=result["detection_time"],
                model_name=model_name,
                status="completed",
                type="video",
                defect_results=result,
            )
            db.add(record)
            db.commit()
        finally:
            db.close()

        with video_tasks_lock:
            video_tasks[task_id]["status"] = "completed"
            video_tasks[task_id]["progress"] = 100.0
            video_tasks[task_id]["result_video_url"] = get_file_url(result["output_filename"], settings.VIDEO_RESULT_DIR)
            video_tasks[task_id]["summary"] = {
                "total_objects": result["total_objects"],
                "class_counts": result["class_counts"],
                "frames_with_defects": result["frames_with_defects"],
                "detection_time": result["detection_time"],
                "total_frames": result["total_frames"],
                "processed_frames": result["processed_frames"],
            }
    except Exception as e:
        with video_tasks_lock:
            video_tasks[task_id]["status"] = "failed"
            video_tasks[task_id]["message"] = str(e)
```

- [ ] **Step 3: Add POST /detection/video endpoint, after the /batch endpoint (after line 160)**

```python
@router.post("/video", response_model=VideoTaskResponse)
async def detect_video(
    file: UploadFile = File(...),
    model_name: str = Form("steel-v1"),
    frame_interval: int = Form(5),
    current_user: dict = Depends(get_current_user),
):
    ext = os.path.splitext(file.filename or "video.mp4")[1].lower()
    if ext not in ALLOWED_VIDEO_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"不支持的视频格式: {ext}，支持 {', '.join(ALLOWED_VIDEO_EXTENSIONS)}")

    task_id = uuid.uuid4().hex
    saved_filename = await save_upload_file(file, settings.UPLOAD_DIR)
    video_path = os.path.join(settings.UPLOAD_DIR, saved_filename)

    with video_tasks_lock:
        video_tasks[task_id] = {
            "status": "processing",
            "progress": 0.0,
            "processed_frames": 0,
            "total_frames": 0,
            "result_video_url": None,
            "summary": None,
            "message": None,
        }

    thread = threading.Thread(
        target=_process_video_task,
        args=(task_id, video_path, model_name, frame_interval, current_user["sub"]),
        daemon=True,
    )
    thread.start()

    return VideoTaskResponse(
        task_id=task_id,
        status="processing",
        message="视频检测任务已启动",
    )
```

- [ ] **Step 4: Add GET /detection/video/progress/{task_id} endpoint**

```python
@router.get("/video/progress/{task_id}", response_model=VideoProgressResponse)
async def get_video_progress(
    task_id: str,
    current_user: dict = Depends(get_current_user),
):
    with video_tasks_lock:
        task = video_tasks.get(task_id)

    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在或已过期")

    return VideoProgressResponse(
        task_id=task_id,
        status=task["status"],
        progress=task["progress"],
        processed_frames=task["processed_frames"],
        total_frames=task["total_frames"],
        result_video_url=task["result_video_url"],
        summary=task["summary"],
        message=task["message"],
    )
```

---

### Task 5: Add video API functions to frontend

**Files:**
- Modify: `frontend/src/api/detection.js`

- [ ] **Step 1: Add detectVideo and getVideoProgress at end of detection.js**

```js
// 视频检测接口
export const detectVideo = (data) => {
  return request({
    url: "/detection/video",
    method: "post",
    data,
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
};

// 查询视频检测进度
export const getVideoProgress = (taskId) => {
  return request({
    url: `/detection/video/progress/${taskId}`,
    method: "get",
  });
};
```

---

### Task 6: Implement video detection UI and logic in DetectionPage

**Files:**
- Modify: `frontend/src/views/DetectionPage.vue`

- [ ] **Step 1: Import video API functions**

In the `<script setup>` section, change the import lines (currently lines 265-266):
```js
import { detectSingleImage, detectBatchImages, detectVideo, getVideoProgress } from "../api/detection";
```

- [ ] **Step 2: Add video state variables**

After `let cameraStream = null;` (line 285), add:
```js
const videoTaskId = ref("");
const videoStatus = ref("idle"); // idle | uploading | processing | completed | failed
const videoProgress = ref(0);
const videoProcessedFrames = ref(0);
const videoTotalFrames = ref(0);
const videoResultUrl = ref("");
const videoSummary = ref(null);
let pollingTimer = null;
```

- [ ] **Step 3: Add computed: isVideo**

After the existing computed properties (after line 302), add:
```js
const isVideo = computed(() => activeTab.value === "video");
```

- [ ] **Step 4: Add video branch in handleFileChange**

Change `handleFileChange` (lines 335-348) to include the video case:
```js
const handleFileChange = async (event, tabKey) => {
  event.stopPropagation();
  event.preventDefault();
  const input = event.target;
  const files = input.files;
  if (!files || files.length === 0) return;

  if (tabKey === "single") {
    await performSingleDetection(files[0]);
  } else if (tabKey === "batch") {
    await performBatchDetection(files);
  } else if (tabKey === "video") {
    await performVideoDetection(files[0]);
  }
  input.value = "";
};
```

- [ ] **Step 5: Add performVideoDetection function**

After `performBatchDetection` (after line 436), add:
```js
const performVideoDetection = async (file) => {
  try {
    resetResults();
    activeTab.value = "video";
    videoStatus.value = "uploading";
    videoProgress.value = 0;
    videoResultUrl.value = "";
    videoSummary.value = null;

    const formData = new FormData();
    formData.append("file", file);
    formData.append("model_name", selectedModel.value);
    formData.append("frame_interval", "5");

    const response = await detectVideo(formData);
    if (!response.task_id) {
      ElMessage.error("启动视频检测失败");
      videoStatus.value = "idle";
      return;
    }

    videoTaskId.value = response.task_id;
    videoStatus.value = "processing";
    startPolling();
  } catch (error) {
    console.error("视频检测错误:", error);
    ElMessage.error("视频检测启动失败");
    videoStatus.value = "idle";
  }
};

const startPolling = () => {
  stopPolling();
  pollingTimer = setInterval(async () => {
    try {
      const response = await getVideoProgress(videoTaskId.value);
      videoProgress.value = response.progress;
      videoProcessedFrames.value = response.processed_frames;
      videoTotalFrames.value = response.total_frames;

      if (response.status === "completed") {
        stopPolling();
        videoStatus.value = "completed";
        videoResultUrl.value = response.result_video_url;
        videoSummary.value = response.summary;
        ElMessage.success("视频检测完成！");
      } else if (response.status === "failed") {
        stopPolling();
        videoStatus.value = "failed";
        ElMessage.error(response.message || "视频检测失败");
      }
    } catch (error) {
      stopPolling();
      videoStatus.value = "failed";
      ElMessage.error("获取检测进度失败");
    }
  }, 500);
};

const stopPolling = () => {
  if (pollingTimer) {
    clearInterval(pollingTimer);
    pollingTimer = null;
  }
};
```

- [ ] **Step 6: Add cleanup in onUnmounted**

Change `onUnmounted` (lines 500-503) to include polling cleanup:
```js
onUnmounted(() => {
  stopCamera();
  stopPolling();
  batchObjectUrls.forEach((url) => URL.revokeObjectURL(url));
});
```

- [ ] **Step 7: Add video processing/progress UI in the template left panel**

Before the empty state `<div v-if="!hasResults" ...>` (before line 85), add the video processing progress UI. Video states must be checked first so they don't fall through to the empty state when `hasResults` is false:
```html
        <!-- 视频处理进度 -->
        <div v-else-if="isVideo && (videoStatus === 'uploading' || videoStatus === 'processing')" class="video-progress">
          <el-icon :size="48" class="video-progress-icon"><VideoCamera /></el-icon>
          <p class="video-progress-title">{{ videoStatus === 'uploading' ? '正在上传视频...' : '正在分析视频...' }}</p>
          <el-progress
            :percentage="videoProgress"
            :stroke-width="12"
            :text-inside="true"
            class="video-progress-bar"
          />
          <p class="video-progress-desc" v-if="videoTotalFrames > 0">
            已处理 {{ videoProcessedFrames }} / {{ videoTotalFrames }} 帧
          </p>
        </div>
```

- [ ] **Step 8: Add video result display in the template left panel**, after the progress UI:
```html
        <!-- 视频检测结果 -->
        <div v-else-if="isVideo && videoStatus === 'completed'" class="video-result">
          <video
            :src="videoResultUrl"
            controls
            autoplay
            loop
            class="result-video"
          ></video>
          <div class="video-result-label">检测结果视频</div>
        </div>
```

- [ ] **Step 9: Add video failed state in the template left panel**, after the video result:
```html
        <!-- 视频检测失败 -->
        <div v-else-if="isVideo && videoStatus === 'failed'" class="video-failed">
          <el-icon :size="64" class="video-failed-icon"><CircleClose /></el-icon>
          <p class="video-failed-text">视频检测失败</p>
          <p class="video-failed-desc">请检查视频文件是否有效，或稍后重试</p>
        </div>
```

- [ ] **Step 10: Add video summary panel in the right panel**

After the "批量汇总" `<div v-if="isBatch" ...>` block (lines 150-165), add:
```html
        <!-- 视频检测汇总 -->
        <div v-if="isVideo && videoStatus === 'completed' && videoSummary" class="info-card">
          <div class="info-item">
            <span class="info-label">检测帧数</span>
            <span class="info-value">{{ videoSummary.processed_frames }} / {{ videoSummary.total_frames }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">检测总目标</span>
            <span class="info-value">{{ videoSummary.total_objects }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">含缺陷帧数</span>
            <span class="info-value">{{ videoSummary.frames_with_defects }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">检测耗时</span>
            <span class="info-value">{{ videoSummary.detection_time }}s</span>
          </div>
        </div>

        <!-- 视频缺陷类别分布 -->
        <div v-if="isVideo && videoStatus === 'completed' && videoSummary" class="result-card">
          <div class="card-header">
            <el-icon><List /></el-icon>
            <span class="card-title">缺陷类别统计</span>
          </div>
          <div v-if="videoSummary.total_objects === 0" class="empty-state">
            <el-icon class="empty-icon"><CircleCheck /></el-icon>
            <p class="empty-text">未检测到缺陷</p>
          </div>
          <div v-else class="detection-list">
            <div
              v-for="(count, className) in videoSummary.class_counts"
              :key="className"
              class="detection-item"
            >
              <span class="item-name">{{ className }}</span>
              <span class="item-confidence">{{ count }} 个</span>
            </div>
          </div>
        </div>
```

- [ ] **Step 11: Add VideoCamera icon import**

In the icon imports at line 251-264, add `VideoCamera`:
```js
import {
  Picture,
  Plus,
  Camera,
  Monitor,
  Check,
  Grid,
  List,
  CircleCheck,
  CircleClose,
  ChatDotRound,
  Refresh,
  Minus,
  ArrowLeft,
  VideoCamera,
} from "@element-plus/icons-vue";
```

- [ ] **Step 12: Add video-related CSS styles at end of `<style scoped>`**

After the `.camera-canvas { display: none; }` rule (line 984), add:
```css
/* 视频处理进度 */
.video-progress {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 320px;
  gap: 16px;
}

.video-progress-icon {
  color: var(--primary-color);
}

.video-progress-title {
  font-size: 16px;
  font-weight: 500;
  color: var(--text-primary);
}

.video-progress-bar {
  width: 80%;
  max-width: 400px;
}

.video-progress-desc {
  font-size: 13px;
  color: var(--text-secondary);
}

/* 视频结果 */
.video-result {
  position: relative;
  border-radius: 8px;
  overflow: hidden;
  background: #000;
}

.result-video {
  width: 100%;
  max-height: 480px;
  display: block;
}

.video-result-label {
  padding: 8px 12px;
  font-size: 13px;
  color: #ffffff;
  background: rgba(0, 0, 0, 0.5);
  text-align: center;
}

/* 视频检测失败 */
.video-failed {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 320px;
  gap: 8px;
}

.video-failed-icon {
  color: #ef4444;
  margin-bottom: 8px;
}

.video-failed-text {
  font-size: 16px;
  font-weight: 500;
  color: var(--text-primary);
}

.video-failed-desc {
  font-size: 13px;
  color: var(--text-secondary);
}
```

- [ ] **Step 13: Also add `video` to the existing `hasResults` computed to include video completed state**

Modify the `hasResults` computed (line 287-289):
```js
const hasResults = computed(() => {
  if (isBatch.value) return batchResults.value.length > 0;
  if (isVideo.value && videoStatus.value === "completed") return true;
  return !!currentDetectionResult.value;
});
```

---

### Task 7: Verify end-to-end

- [ ] **Step 1: Start backend and verify no import errors**

```bash
wsl -d Ubuntu -- bash -c "kill \$(lsof -ti:8000) 2>/dev/null; sleep 1; cd /home/cwl/yaogan/backend && source .venv/bin/activate && nohup python main.py &>/tmp/yaogan.log & sleep 3"
```

Check for startup errors:
```bash
wsl -d Ubuntu -- bash -c "cat /tmp/yaogan.log | tail -20"
```

Expected: no traceback, server running on :8000.

- [ ] **Step 2: Start frontend and verify no build errors**

```bash
wsl -d Ubuntu -- bash -c "lsof -ti:5173 | xargs kill 2>/dev/null; sleep 1; export PATH=\"/home/cwl/.nvm/versions/node/v24.15.0/bin:\$PATH\" && cd /home/cwl/yaogan/frontend && nohup npm run dev &>/tmp/yaogan-frontend.log & sleep 3"
```

Check for build errors:
```bash
wsl -d Ubuntu -- bash -c "cat /tmp/yaogan-frontend.log | tail -20"
```

Expected: no errors, dev server running.

- [ ] **Step 3: Manual test — upload a small video, verify the full flow**

1. Open `http://localhost:5173/detection` in browser, log in.
2. Click "视频检测" tab, select a short mp4 video.
3. Verify: progress bar appears, shows frame counts, transitions to video player.
4. Verify: right panel shows summary with class counts.
5. Verify: annotated video plays with bounding boxes on detected frames.
