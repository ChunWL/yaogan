# 实时摄像头检测 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace manual camera capture with real-time WebSocket-based video detection

**Architecture:** Browser captures webcam frames via getUserMedia → JPEG-compresses via canvas.toBlob → sends binary over WebSocket to FastAPI → YOLO inference → returns JSON boxes → Canvas overlay draws on video

**Tech Stack:** FastAPI WebSocket, YOLO/ultralytics, Vue 3 Canvas API

---

### Task 1: Backend — Add lightweight `detect_frame` to DetectionService

**File:** Modify: `backend/app/services/detection_service.py` (after line 127, before `detect_video`)

- [ ] **Step 1: Add `detect_frame` method**

```python
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
```

- [ ] **Step 2: Verify import works**

Run: `wsl -d Ubuntu -- bash -c "cd /home/cwl/yaogan/backend && .venv/bin/python3 -c \"from app.services.detection_service import detection_service; print('ok')\""`
Expected: prints "ok"

---

### Task 2: Backend — Add WebSocket camera endpoint

**File:** Modify: `backend/app/api/detection.py`

- [ ] **Step 1: Add imports at top**

```python
import cv2
import numpy as np
from fastapi import WebSocket, WebSocketDisconnect, Query
from app.utils.auth import verify_token
```

- [ ] **Step 2: Add WebSocket endpoint before the POST routes**

```python
@router.websocket("/ws/camera")
async def camera_websocket(
    websocket: WebSocket,
    token: str = Query(...),
    model_name: str = Query("yolo11n"),
    scene: str = Query("steel"),
):
    # Auth
    user = verify_token(token)
    if not user:
        await websocket.close(code=4001)
        return

    await websocket.accept()
    frame_id = 0

    try:
        while True:
            data = await websocket.receive_bytes()

            # Decode JPEG bytes → numpy array (BGR)
            nparr = np.frombuffer(data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                continue

            frame_id += 1
            result = detection_service.detect_frame(img, model_name)

            await websocket.send_json({
                "frame_id": frame_id,
                "boxes": result["boxes"],
                "total_objects": result["total_objects"],
            })
    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"error": str(e)})
        except Exception:
            pass
```

- [ ] **Step 3: Verify backend starts**

Run:
```bash
wsl -d Ubuntu -- bash -c "cd /home/cwl/yaogan/backend && kill \$(lsof -ti:8000) 2>/dev/null; sleep 1; .venv/bin/python3 -c \"from app.api.detection import router; print('WS endpoint loaded')\""
```
Expected: prints "WS endpoint loaded"

---

### Task 3: Frontend — Add WebSocket URL helper

**File:** Modify: `frontend/src/api/detection.js`

- [ ] **Step 1: Add WebSocket URL helper at the end**

```javascript
// WebSocket camera detection
export const getCameraWsUrl = (token, modelName = "yolo11n", scene = "steel") => {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const host = window.location.host;
  return `${protocol}//${host}/api/detection/ws/camera?token=${encodeURIComponent(token)}&model_name=${encodeURIComponent(modelName)}&scene=${encodeURIComponent(scene)}`;
};
```

---

### Task 4: Frontend — Rewrite camera mode in DetectionPage.vue

**File:** Modify: `frontend/src/views/DetectionPage.vue`

This is the main task. The camera mode changes from dialog-based to inline video+canvas.

#### 4a: Template changes

- [ ] **Step 1: Remove the camera dialog (`<el-dialog>`) block** (lines 334-346)

Replace with nothing — camera mode will render in the main content area.

- [ ] **Step 2: Add camera view to the main content area**

In the `else-if` chain for empty/side/grid states (around line 133), add a camera mode block before the empty state:

```html
<!-- 摄像头实时检测 -->
<div v-else-if="cameraMode" class="camera-view">
  <div class="camera-overlay-container">
    <video ref="cameraVideoRef" autoplay playsinline class="camera-video"></video>
    <canvas ref="cameraOverlayRef" class="camera-overlay"></canvas>
    <div class="camera-status">
      <span class="status-dot" :class="{ active: cameraDetecting }"></span>
      <span class="status-text">{{ cameraDetecting ? `检测中 (${cameraFps} FPS)` : '已暂停' }}</span>
    </div>
  </div>
</div>
```

- [ ] **Step 3: Add camera control buttons in the toolbar area** (after the existing toolbar, around line 97)

```html
<div class="camera-actions" v-if="cameraMode">
  <el-button
    type="danger"
    size="small"
    @click="stopCameraDetection"
  >
    <el-icon><VideoPause /></el-icon>
    停止检测
  </el-button>
  <el-button
    size="small"
    @click="toggleCameraPause"
  >
    <el-icon><VideoPlay v-if="cameraPaused" /><VideoPause v-else /></el-icon>
    {{ cameraPaused ? '继续' : '暂停' }}
  </el-button>
  <el-button
    type="primary"
    size="small"
    @click="saveCameraSnapshot"
    :disabled="!cameraDetecting && !lastCameraBoxes.length"
  >
    <el-icon><Camera /></el-icon>
    保存快照
  </el-button>
</div>
```

#### 4b: Script changes

- [ ] **Step 4: Add new imports** (add to the existing icon imports)

```javascript
import {
  // ... existing icons ...
  VideoPause,
  VideoPlay,
} from "@element-plus/icons-vue";
```

- [ ] **Step 5: Add new state variables** (after existing camera state lines, around line 424)

```javascript
// Real-time camera detection
const cameraMode = ref(false);
const cameraDetecting = ref(false);
const cameraPaused = ref(false);
const cameraFps = ref(0);
const cameraVideoRef = ref(null);
const cameraOverlayRef = ref(null);
const lastCameraBoxes = ref([]);
const lastCameraFrameUrl = ref("");
let cameraWs = null;
let cameraAnimFrameId = null;
let cameraFrameCount = 0;
let cameraLastFpsTime = 0;
let cameraStream2 = null;  // separate ref from dialog cameraStream
```

- [ ] **Step 6: Update `handleTabClick` for camera tab**

Replace the camera branch (around line 486-489):

```javascript
const handleTabClick = (key) => {
  activeTab.value = key;
  if (key !== "video") {
    stopPolling();
  }
  if (key === "camera") {
    startCameraDetection();
    return;
  }
  // For other tabs, stop camera if active
  if (cameraMode.value) {
    stopCameraDetection();
  }
  const input = document.querySelector(`.function-tab[data-key="${key}"] .file-input`);
  if (input) {
    input.value = "";
    input.click();
  }
};
```

- [ ] **Step 7: Add `startCameraDetection` function**

```javascript
const startCameraDetection = async () => {
  resetResults();
  cameraMode.value = true;
  cameraDetecting.value = false;
  cameraPaused.value = false;
  cameraFps.value = 0;
  lastCameraBoxes.value = [];
  cameraFrameCount = 0;
  cameraLastFpsTime = performance.now();

  // Open camera
  try {
    cameraStream2 = await navigator.mediaDevices.getUserMedia({
      video: { width: 640, height: 480, facingMode: "environment" },
    });
    if (cameraVideoRef.value) {
      cameraVideoRef.value.srcObject = cameraStream2;
    }
  } catch (error) {
    ElMessage.error("无法访问摄像头: " + error.message);
    cameraMode.value = false;
    return;
  }

  // Connect WebSocket
  const token = localStorage.getItem("token");
  if (!token) {
    ElMessage.error("请先登录");
    stopCameraDetection();
    return;
  }

  try {
    const wsUrl = getCameraWsUrl(token, selectedModel.value, sceneKey.value);
    cameraWs = new WebSocket(wsUrl);

    cameraWs.onopen = () => {
      cameraDetecting.value = true;
      startFrameCapture();
    };

    cameraWs.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.error) return;
      lastCameraBoxes.value = data.boxes;
      drawDetectionBoxes(data.boxes);
      // Update right panel
      currentDetectionResult.value = {
        total_objects: data.total_objects,
        boxes: data.boxes,
        detection_time: 0,
        model_name: selectedModel.value,
      };
    };

    cameraWs.onclose = () => {
      cameraDetecting.value = false;
    };

    cameraWs.onerror = () => {
      ElMessage.error("WebSocket 连接失败");
      stopCameraDetection();
    };
  } catch (error) {
    ElMessage.error("连接失败: " + error.message);
    stopCameraDetection();
  }
};
```

- [ ] **Step 8: Add frame capture loop**

```javascript
const startFrameCapture = () => {
  if (cameraAnimFrameId) return;
  let frameSkip = 0;

  const capture = () => {
    cameraAnimFrameId = requestAnimationFrame(capture);
    if (!cameraWs || cameraWs.readyState !== WebSocket.OPEN) return;
    if (cameraPaused.value) return;

    const video = cameraVideoRef.value;
    if (!video || !video.videoWidth) return;

    // FPS calculation
    cameraFrameCount++;
    const now = performance.now();
    const elapsed = now - cameraLastFpsTime;
    if (elapsed >= 1000) {
      cameraFps.value = Math.round(cameraFrameCount / (elapsed / 1000));
      cameraFrameCount = 0;
      cameraLastFpsTime = now;
    }

    // Skip every other frame to control rate (~15 FPS from 30 FPS source)
    frameSkip++;
    if (frameSkip < 2) return;
    frameSkip = 0;

    // Capture frame to canvas
    const canvas = document.createElement("canvas");
    canvas.width = 640;
    canvas.height = 480;
    const ctx = canvas.getContext("2d");
    ctx.drawImage(video, 0, 0, 640, 480);

    canvas.toBlob((blob) => {
      if (blob && cameraWs && cameraWs.readyState === WebSocket.OPEN) {
        cameraWs.send(blob);
      }
    }, "image/jpeg", 0.7);
  };

  capture();
};

const stopFrameCapture = () => {
  if (cameraAnimFrameId) {
    cancelAnimationFrame(cameraAnimFrameId);
    cameraAnimFrameId = null;
  }
};
```

- [ ] **Step 9: Add canvas drawing function**

```javascript
const drawDetectionBoxes = (boxes) => {
  const canvas = cameraOverlayRef.value;
  const video = cameraVideoRef.value;
  if (!canvas || !video) return;

  canvas.width = video.clientWidth;
  canvas.height = video.clientHeight;
  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  const scaleX = canvas.width / 640;
  const scaleY = canvas.height / 480;

  for (const box of boxes) {
    const x1 = box.x1 * scaleX;
    const y1 = box.y1 * scaleY;
    const x2 = box.x2 * scaleX;
    const y2 = box.y2 * scaleY;

    // Draw rectangle
    ctx.strokeStyle = "#00ff00";
    ctx.lineWidth = 2;
    ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);

    // Draw label background
    const label = `${box.class_name} ${(box.confidence * 100).toFixed(1)}%`;
    ctx.font = "14px sans-serif";
    const textWidth = ctx.measureText(label).width;
    ctx.fillStyle = "rgba(0, 255, 0, 0.3)";
    ctx.fillRect(x1, y1 - 20, textWidth + 8, 20);

    // Draw label text
    ctx.fillStyle = "#ffffff";
    ctx.fillText(label, x1 + 4, y1 - 4);
  }
};
```

- [ ] **Step 10: Add control functions**

```javascript
const stopCameraDetection = () => {
  stopFrameCapture();
  if (cameraWs) {
    cameraWs.close();
    cameraWs = null;
  }
  if (cameraStream2) {
    cameraStream2.getTracks().forEach((t) => t.stop());
    cameraStream2 = null;
  }
  cameraDetecting.value = false;
  cameraMode.value = false;
  cameraPaused.value = false;
  lastCameraBoxes.value = [];
  currentDetectionResult.value = null;
  cameraFps.value = 0;
};

const toggleCameraPause = () => {
  cameraPaused.value = !cameraPaused.value;
};

const saveCameraSnapshot = async () => {
  const video = cameraVideoRef.value;
  if (!video) return;

  // Capture current frame (with drawn boxes) to blob
  const captureCanvas = document.createElement("canvas");
  captureCanvas.width = video.videoWidth || 640;
  captureCanvas.height = video.videoHeight || 480;
  const ctx = captureCanvas.getContext("2d");
  ctx.drawImage(video, 0, 0);

  // Also draw the last detection boxes on the snapshot
  if (lastCameraBoxes.value.length > 0) {
    const scaleX = captureCanvas.width / 640;
    const scaleY = captureCanvas.height / 480;
    for (const box of lastCameraBoxes.value) {
      const x1 = box.x1 * scaleX, y1 = box.y1 * scaleY;
      const x2 = box.x2 * scaleX, y2 = box.y2 * scaleY;
      ctx.strokeStyle = "#00ff00";
      ctx.lineWidth = 3;
      ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);
    }
  }

  const blob = await new Promise((r) => captureCanvas.toBlob(r, "image/jpeg", 0.95));
  if (!blob) return;
  const file = new File([blob], `camera_snapshot_${Date.now()}.jpg`, { type: "image/jpeg" });

  // Pause detection while saving
  const wasPaused = cameraPaused.value;
  cameraPaused.value = true;

  await performSingleDetection(file);

  cameraPaused.value = wasPaused;
};
```

- [ ] **Step 11: Update `onUnmounted` to clean up camera resources**

Add camera cleanup to existing `onUnmounted`:

```javascript
onUnmounted(() => {
  stopCameraDetection();
  stopCamera();
  stopPolling();
  batchObjectUrls.forEach((url) => URL.revokeObjectURL(url));
});
```

- [ ] **Step 12: Update `resetResults` to handle camera mode**

Add camera cleanup at the beginning of `resetResults`:

```javascript
const resetResults = () => {
  if (cameraMode.value) {
    stopCameraDetection();
  }
  // ... existing code ...
};
```

- [ ] **Step 13: Remove old camera dialog code**

Remove the old `startCamera`, `stopCamera`, `captureFrame` functions (lines 685-728) since they're replaced by the new real-time versions. The `showCamera`, `cameraReady`, `videoRef`, `canvasRef`, `cameraStream` variables from the dialog approach can be removed if they're no longer referenced.

#### 4c: Style changes

- [ ] **Step 14: Add camera view styles** (after existing camera styles, around line 1241)

```css
.camera-view {
  position: relative;
  width: 100%;
  min-height: 320px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #000;
  border-radius: 8px;
  overflow: hidden;
}

.camera-overlay-container {
  position: relative;
  width: 100%;
  max-height: 480px;
}

.camera-video {
  width: 100%;
  max-height: 480px;
  display: block;
  object-fit: contain;
}

.camera-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.camera-status {
  position: absolute;
  top: 12px;
  left: 12px;
  display: flex;
  align-items: center;
  gap: 6px;
  background: rgba(0, 0, 0, 0.6);
  padding: 4px 10px;
  border-radius: 12px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #666;
}

.status-dot.active {
  background: #ff4444;
  animation: pulse 1.2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.status-text {
  font-size: 12px;
  color: #fff;
}

.camera-actions {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}
```

---

### Task 5: Build and verify frontend

- [ ] **Step 1: Rebuild frontend**

```bash
wsl -d Ubuntu -- bash -c "cd /home/cwl/yaogan/frontend && npm run build 2>&1 | tail -20"
```
Expected: Build succeeds with no errors.

- [ ] **Step 2: Restart backend**

```bash
wsl -d Ubuntu -- bash -c "kill \$(lsof -ti:8000) 2>/dev/null; sleep 1; cd /home/cwl/yaogan/backend && .venv/bin/python3 main.py &>/tmp/yaogan.log &
sleep 8"
```

- [ ] **Step 3: Quick smoke test**

Open browser to `http://localhost:8000`, login, click "摄像头检测" tab, verify:
- Camera permission dialog appears
- Video feed shows in main content area
- Red recording dot + FPS counter visible
- Detection boxes appear on video
- Right panel updates with detections
- Stop/Pause/Save buttons work
