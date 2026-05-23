# 实时摄像头检测设计

## 概述

将现有的「手动拍照检测」摄像头功能改为实时检测模式：摄像头画面持续显示，帧画面持续送后端 YOLO 推理，检测框实时叠加在视频画面上。

## 架构

```
浏览器 getUserMedia → <video> 实时显示
         │
         ▼ requestAnimationFrame (每 2-3 帧发送一次)
   <canvas> → toBlob(JPEG, quality=0.7)
         │
         ▼ WebSocket binary
 FastAPI /api/detection/ws/camera
         │
         ▼ model.predict()
         │
         ▼ JSON {frame_id, boxes: [{x1,y1,x2,y2,confidence,class_name,class_id}]}
         │
         ▼
   <canvas overlay> 画检测框
   右侧面板更新识别清单
```

## 后端

### 新增 WebSocket 端点

- **路由**: `WS /api/detection/ws/camera`（挂载到 `detection_router`，前缀 `/api`）
- **认证**: 通过 URL query 参数传 token，如 `ws://.../ws/camera?token=xxx`
- **接收**: binary 消息（JPEG 字节流）
- **处理**: 
  - 解码 JPEG → PIL Image / ndarray
  - 调用 `detection_service.detect_single_image()` 或直接 `model.predict()`
  - 只返回检测框坐标（不保存图片、不写数据库）
- **发送**: JSON 文本消息 `{"frame_id": int, "boxes": [...], "total_objects": int}`
- **模型选择**: 连接时通过 query 参数 `model_name` 传入
- **场景选择**: 连接时通过 query 参数 `scene` 传入
- **错误处理**: 单帧推理失败不影响后续帧
- **连接关闭**: 客户端断开或发送关闭帧时结束

### 认证方式

因为 WebSocket 不支持 headers，JWT token 通过 URL query 参数传递：
```python
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    user = verify_token(token)  # 复用现有的 verify_token
    if not user:
        await websocket.close(code=4001)
        return
```

## 前端

### DetectionPage.vue 改动

摄像头 tab 不再打开 `<el-dialog>`，改为在主内容区展示：

#### 点击「摄像头检测」tab → 直接进入摄像头模式
- 页面左侧（检测预览区）显示 `<video>` + `<canvas>` 叠加层
- 右侧面板显示实时检测结果
- 不再弹出 dialog

#### 新增状态变量
- `cameraMode` (bool) — 是否处于摄像头实时检测模式
- `wsConnection` (WebSocket) — WebSocket 连接实例
- `frameId` (int) — 自增帧计数器
- `lastBoxes` (array) — 最近一帧的检测框

#### 帧采集循环
- 用 `requestAnimationFrame` 驱动
- 每 2-3 帧才真正截取发送（控制 ~10-20 FPS）
- 截帧: video → canvas(640x480) → toBlob(jpeg, 0.7) → WebSocket.send

#### 结果渲染
- `<canvas>` 覆盖在 `<video>` 上，位置对齐
- 收到检测结果 → 清除旧框 → 绘制新框（矩形 + class_name + confidence）
- 右侧面板更新识别清单

#### 控制 UI
- **红色录制指示点** + 「检测中 (15 FPS)」提示
- **「停止检测」按钮** → 关闭摄像头 + 断开 WebSocket + 回到空状态
- **「暂停/继续」按钮**（可选）→ 暂停截帧但不关闭摄像头
- **「保存快照」按钮** → 将当前帧 JPEG + 检测结果上传保存到历史记录（复用 `POST /api/detection/single`）
- **模型选择器** → 断开 WebSocket 后用新模型重新连接

#### 保存快照流程
1. 截取当前 `<canvas>` 上的帧（含标注框）→ toBlob → File
2. 调用现有的 `performSingleDetection(file)`，复用完整保存逻辑
3. 同时保存标注后的图像到历史记录

## 性能

- **目标帧率**: 10-20 FPS（摄像头 30 FPS 无需全检，人眼感知 15 FPS 已很流畅）
- **JPEG 质量**: 0.7，平衡大小和质量
- **帧尺寸**: 640x480（摄像头分辨率，过大增加编码+传输时间）
- **推理**: yolo11n 在本地 GPU ~20-50ms，加上编解码总延迟 ~30-60ms
- **帧跳过**: 若推理积压，跳过多余帧（`model.predict()` 本身非阻塞）

## 文件改动清单

| 文件 | 改动 |
|------|------|
| `backend/app/api/detection.py` | 新增 WebSocket 端点 `ws/camera` |
| `backend/app/utils/auth.py` | (可选) 导出 `verify_token` 供 WebSocket 认证使用 |
| `frontend/src/views/DetectionPage.vue` | 重写摄像头模式：去掉弹窗，改为视频+Canvas叠加+实时检测 |
| `frontend/src/api/detection.js` | (可选) 新增 WebSocket URL 导出 |
