# 视频检测功能设计

## 概述

在检测页面已有单图、批量、摄像头三种模式的基础上，实现视频检测 tab：用户上传视频文件 → 后端逐帧抽检进行 YOLO 推理 → 返回带标注框的视频及缺陷摘要。

## 整体流程

```
前端选择视频 → POST /api/detection/video → 后端保存视频、创建异步任务、返回 task_id
                                                   ↓
                                         后台线程：逐帧读取 → 抽帧(每N帧) → YOLO → 写标注视频
                                                   ↓
                   前端轮询 GET /api/detection/video/progress/{task_id} → 获取进度
                                                   ↓
                    处理完成 → 前端展示 <video> 播放标注视频 + 缺陷摘要面板
```

## 后端变更

### 新增端点

#### `POST /api/detection/video`
- 入参（multipart/form-data）：`file`（视频文件）、`model_name`、`frame_interval`（默认 5，即每 5 帧检测一次）
- 校验：文件类型为常见视频格式（mp4/avi/mov/mkv/webm）
- 将视频保存到 `static/uploads/`
- 在后台线程启动视频处理任务，分配 `task_id`（UUID）
- 立即返回 `{task_id, status: "processing", message: "视频检测任务已启动"}`

#### `GET /api/detection/video/progress/{task_id}`
- 返回任务状态：
  - 处理中：`{task_id, status: "processing", progress: 45.2, processed_frames: 150, total_frames: 332}`
  - 已完成：`{task_id, status: "completed", progress: 100, result_video_url, summary: {total_objects, class_counts: {class_name: count}, frames_with_defects, detection_time, total_frames, processed_frames}}`
  - 失败：`{task_id, status: "failed", message: "错误原因"}`

### 新增方法 `detection_service.detect_video()`

```python
def detect_video(self, video_path: str, output_path: str, model_name: str,
                 frame_interval: int = 5, task_id: str = None) -> dict:
```

- 用 `cv2.VideoCapture` 读取视频，获取总帧数(fps)、帧率
- 遍历每一帧：
  - 每 `frame_interval` 帧做一次 YOLO 推理
  - 检测到缺陷 → 在当前帧上绘制标注框
  - 否则原帧直接写入
- 用 `cv2.VideoWriter` 输出标注视频（保持原视频编码和帧率）
- 累计统计：总缺陷数、各类别计数、含缺陷帧数
- 每处理一帧更新 `video_tasks[task_id]` 进度字典
- 完成后创建 `DetectionRecord(type="video")` 写入数据库
- 返回 `summary` 字典

### 进度存储

使用内存字典 `video_tasks: dict[str, dict]` 存储每个任务的状态：
```python
video_tasks[task_id] = {
    "status": "processing" | "completed" | "failed",
    "progress": float,       # 0-100
    "processed_frames": int,
    "total_frames": int,
    "result_video_url": str | None,
    "summary": dict | None,
    "message": str | None,
}
```

### 新增 Schema

```python
class VideoTaskResponse(BaseModel):
    task_id: str
    status: str
    message: str

class VideoProgressResponse(BaseModel):
    task_id: str
    status: str
    progress: float = 0
    processed_frames: int = 0
    total_frames: int = 0
    result_video_url: str | None = None
    summary: dict | None = None
    message: str | None = None
```

### 数据库

`detection_records.type` 字段新增 `"video"` 值。视频记录的 `defect_results` JSON 字段存储摘要数据（不存逐帧详细坐标，数据量过大）。

## 前端变更

### DetectionPage.vue

**`handleFileChange` 新增 `video` 分支：**
- 构建 FormData（file + model_name + frame_interval）
- 调用 `detectVideo(formData)` 获取 `task_id`
- 启动轮询（每 500ms 调用 `getVideoProgress(task_id)`）
- 显示进度条组件

**新增视频处理状态区（`videoProcessing` 为 true 时展示）：**
- 进度条 + 百分比 + "已处理 X / N 帧"
- 取消按钮（标记任务取消，不强制中断线程）

**处理完成后（`videoCompleted` 为 true 时展示）：**
- 左侧：`<video>` 标签播放标注视频，带播放控件
- 右侧摘要面板：
  - 总检测目标数
  - 各类别缺陷数量（柱状或列表）
  - 含缺陷帧数 / 总检测帧数
  - 检测耗时

**tab 配置不变**，`video` tab 已有 `accept: "video/*"`。

### `src/api/detection.js`

新增两个 API 函数：
```js
export const detectVideo = (data) => request.post("/detection/video", data);
export const getVideoProgress = (taskId) => request.get(`/detection/video/progress/${taskId}`);
```

## 错误处理

| 场景 | 处理方式 |
|------|----------|
| 视频格式不支持 | 后端校验文件扩展名，返回 400 + 错误信息 |
| 视频无法读取（损坏） | cv2.VideoCapture 打开失败，task 标记为 failed |
| 某帧推理异常 | 记录日志，该帧只写原帧不标注，继续处理后续帧 |
| 处理超时（5 分钟） | 后台线程超时自动标记 failed，已写入的部分视频保留 |

## 配置参数

在 `config.py` 中新增：
- `VIDEO_FRAME_INTERVAL: int = 5` — 默认抽帧间隔
- `VIDEO_RESULT_DIR: str = "static/results/videos"` — 标注视频输出目录
- `VIDEO_TASK_TIMEOUT: int = 300` — 任务超时秒数
