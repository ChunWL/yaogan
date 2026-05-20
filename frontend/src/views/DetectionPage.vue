<template>
  <div class="detection-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="breadcrumb">
        <span>工作台</span>
        <span class="separator">›</span>
        <span class="active">缺陷检测</span>
      </div>
      <h1 class="page-title">上传钢铁表面图像，立即识别表面缺陷</h1>
      <p class="page-subtitle">
        支持轧制氧化皮 / 斑块 / 开裂 / 点蚀表面 / 内含物 / 划痕等缺陷检测
      </p>
    </div>

    <!-- 模型选择器 -->
    <div class="model-selector">
      <el-select v-model="selectedModel" style="width: 180px">
        <el-option label="steel-v1" value="steel-v1" />
        <el-option label="steel-v2" value="steel-v2" />
      </el-select>
    </div>

    <!-- 功能选项卡 -->
    <div class="function-tabs">
      <div
        v-for="tab in functionTabs"
        :key="tab.key"
        class="function-tab"
        :class="{ active: activeTab === tab.key }"
        :data-key="tab.key"
        @click="handleTabClick(tab.key)"
      >
        <input
          v-if="tab.key !== 'camera'"
          type="file"
          :accept="tab.accept"
          :multiple="tab.multiple"
          class="file-input"
          @change="handleFileChange($event, tab.key)"
          @click.stop
          ref="fileInputs"
        />
        <el-icon :size="18" class="tab-icon"><component :is="tab.icon" /></el-icon>
        <div class="tab-content">
          <span class="tab-text">{{ tab.name }}</span>
          <span class="tab-desc">{{ tab.desc }}</span>
        </div>
      </div>
    </div>

    <!-- 主内容区域 -->
    <div class="main-content">
      <!-- 左侧检测结果区域 -->
      <div class="left-panel">
        <div class="panel-header">
          <span class="panel-title">检测预览</span>
          <el-tag type="success" effect="light" class="result-tag">
            <el-icon class="el-icon--left"><Check /></el-icon>
            检测完成
          </el-tag>
        </div>

        <!-- 工具栏 -->
        <div class="toolbar">
          <el-button
            :class="{ active: compareMode === 'side' }"
            size="small"
            @click="compareMode = 'side'"
          >
            <el-icon><Minus /></el-icon>
            并排对比
          </el-button>
          <el-button
            :class="{ active: compareMode === 'grid' }"
            size="small"
            @click="compareMode = 'grid'"
          >
            <el-icon><Grid /></el-icon>
            栅格对比
          </el-button>
        </div>

        <!-- 图片对比区域 -->
        <div class="image-compare">
          <div class="image-card">
            <img
              :src="originalImage"
              alt="原始图片"
              class="compare-image"
            />
            <div class="image-label">原始图片</div>
          </div>
          <div class="image-card">
            <img
              :src="resultImage"
              alt="检测结果"
              class="compare-image"
            />
            <div class="image-label">检测结果</div>
            <div class="detection-mark" v-if="detectionResult"></div>
          </div>
        </div>
      </div>

      <!-- 右侧信息面板 -->
      <div class="right-panel">
        <!-- 模型信息 -->
        <div class="info-card">
          <div class="info-item">
            <span class="info-label">检测模型</span>
            <span class="info-value">{{ selectedModel }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">模型版本</span>
            <span class="info-value">v1.0.0</span>
          </div>
        </div>

        <!-- 识别清单 -->
        <div class="result-card">
          <div class="card-header">
            <el-icon><List /></el-icon>
            <span class="card-title">识别清单</span>
          </div>
          <div v-if="!detectionResult || detectionResult.total_objects === 0" class="empty-state">
            <el-icon class="empty-icon"><CircleCheck /></el-icon>
            <p class="empty-text">未检测到缺陷</p>
            <p class="empty-desc">表面无异常缺陷</p>
          </div>
          <div v-else class="detection-list">
            <div
              v-for="(box, index) in detectionResult.boxes"
              :key="index"
              class="detection-item"
            >
              <span class="item-name">{{ box.class_name }}</span>
              <span class="item-confidence">{{ (box.confidence * 100).toFixed(1) }}%</span>
            </div>
          </div>
        </div>

        <!-- AI诊断建议 -->
        <div class="result-card">
          <div class="card-header">
            <el-icon><ChatDotRound /></el-icon>
            <span class="card-title">AI 诊断建议</span>
          </div>
          <div class="diagnosis-content">
            <p v-if="!detectionResult">未检测到表面缺陷</p>
            <p v-else>
              检测到 {{ detectionResult.total_objects }} 处缺陷，耗时 {{ detectionResult.detection_time }}s。
              模型: {{ detectionResult.model_name }}
            </p>
          </div>
        </div>

        <!-- 操作按钮 -->
        <div class="action-buttons">
          <el-button size="default" class="btn-secondary" @click="handleRedetect">
            <el-icon><Refresh /></el-icon>
            重新检测
          </el-button>
          <el-button type="primary" size="default" class="btn-primary">
            查看完整报告
          </el-button>
        </div>
      </div>
    </div>

    <!-- 摄像头弹窗 -->
    <el-dialog v-model="showCamera" title="摄像头检测" width="640px" :close-on-click-modal="false" @close="stopCamera">
      <div class="camera-container">
        <video ref="videoRef" autoplay playsinline class="camera-video"></video>
        <canvas ref="canvasRef" class="camera-canvas"></canvas>
      </div>
      <template #footer>
        <el-button @click="stopCamera">取消</el-button>
        <el-button type="primary" @click="captureFrame" :disabled="!cameraReady">
          <el-icon><Camera /></el-icon>
          拍照检测
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onUnmounted } from "vue";
import { ElMessage, ElLoading } from "element-plus";
import {
  Picture,
  Plus,
  Camera,
  Monitor,
  Check,
  Grid,
  List,
  CircleCheck,
  ChatDotRound,
  Refresh,
  Minus,
} from "@element-plus/icons-vue";
import { detectSingleImage } from "../api/detection";

const selectedModel = ref("steel-v1");
const activeTab = ref("single");
const compareMode = ref("side");
const originalImage = ref("../assets/images/bus.jpg");
const resultImage = ref("../assets/images/predict-bus.png");
const detectionResult = ref(null);
const isDetecting = ref(false);
const showCamera = ref(false);
const cameraReady = ref(false);
const videoRef = ref(null);
const canvasRef = ref(null);
let cameraStream = null;

const functionTabs = [
  {
    key: "single",
    name: "单图检测",
    desc: "快速识别一张图片",
    icon: Picture,
    accept: "image/*",
    multiple: false,
  },
  {
    key: "batch",
    name: "批量检测",
    desc: "一次处理多张图片",
    icon: Plus,
    accept: "image/*",
    multiple: true,
  },
  {
    key: "camera",
    name: "摄像头检测",
    desc: "调用摄像头实时检测",
    icon: Camera,
    accept: "video/*",
    multiple: false,
  },
  {
    key: "video",
    name: "视频检测",
    desc: "上传视频自动分析",
    icon: Monitor,
    accept: "video/*",
    multiple: false,
  },
];

const fileInputs = ref([]);

const handleTabClick = (key) => {
  activeTab.value = key;
  if (key === "camera") {
    startCamera();
    return;
  }
  const input = document.querySelector(`.function-tab[data-key="${key}"] .file-input`);
  if (input) {
    input.click();
  }
};

const handleFileChange = async (event, tabKey) => {
  event.stopPropagation();
  event.preventDefault();
  const files = event.target.files;
  if (files && files.length > 0) {
    if (tabKey === "single") {
      await performSingleDetection(files[0]);
    }
  }
  setTimeout(() => {
    event.target.value = '';
  }, 0);
};

const performSingleDetection = async (file) => {
  const loading = ElLoading.service({
    lock: true,
    text: "正在检测中...",
    background: "rgba(0, 0, 0, 0.7)",
  });
  
  try {
    isDetecting.value = true;
    
    const formData = new FormData();
    formData.append("file", file);
    formData.append("model_name", selectedModel.value);
    
    originalImage.value = URL.createObjectURL(file);
    
    const response = await detectSingleImage(formData);
    if (response.success && response.data) {
      detectionResult.value = response.data;
      resultImage.value = response.data.result_image_url;
      ElMessage.success("检测成功！");
    } else {
      ElMessage.error(response.message || "检测失败");
    }
  } catch (error) {
    console.error("检测错误:", error);
    ElMessage.error("检测失败，请稍后重试");
  } finally {
    isDetecting.value = false;
    loading.close();
  }
};

const startCamera = async () => {
  showCamera.value = true;
  cameraReady.value = false;
  try {
    cameraStream = await navigator.mediaDevices.getUserMedia({
      video: { width: 640, height: 480, facingMode: "environment" }
    });
    if (videoRef.value) {
      videoRef.value.srcObject = cameraStream;
      videoRef.value.onloadedmetadata = () => {
        cameraReady.value = true;
      };
    }
  } catch (error) {
    ElMessage.error("无法访问摄像头: " + error.message);
    showCamera.value = false;
  }
};

const stopCamera = () => {
  if (cameraStream) {
    cameraStream.getTracks().forEach(track => track.stop());
    cameraStream = null;
  }
  cameraReady.value = false;
  showCamera.value = false;
};

const captureFrame = async () => {
  const video = videoRef.value;
  const canvas = canvasRef.value;
  if (!video || !canvas) return;

  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  const ctx = canvas.getContext("2d");
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

  const blob = await new Promise(resolve => canvas.toBlob(resolve, "image/jpeg", 0.95));
  const file = new File([blob], "camera_capture.jpg", { type: "image/jpeg" });

  stopCamera();
  await performSingleDetection(file);
};

onUnmounted(() => {
  stopCamera();
});

const handleRedetect = () => {
  const input = document.querySelector(`.function-tab[data-key="single"] .file-input`);
  if (input) {
    input.click();
  }
};
</script>

<style scoped>
.detection-page {
  width: 100%;
  position: relative;
}

.page-header {
  margin-bottom: 32px;
  padding-top: 0;
}

.breadcrumb {
  font-size: 14px;
  color: var(--text-secondary);
  margin-bottom: 12px;
}

.separator {
  margin: 0 6px;
}

.active {
  color: var(--text-primary);
}

.page-title {
  font-size: 28px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.page-subtitle {
  font-size: 14px;
  color: var(--text-secondary);
}

.model-selector {
  position: absolute;
  top: 0;
  right: 0;
  z-index: 10;
}

.function-tabs {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
}

.function-tab {
  flex: 1;
  display: flex;
  align-items: center;
  padding: 16px 20px;
  background-color: #ffffff;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
  border: 2px solid transparent;
  position: relative;
  overflow: hidden;
}

.file-input {
  position: absolute;
  width: 100%;
  height: 100%;
  opacity: 0;
  cursor: pointer;
  z-index: 10;
}

.function-tab:hover {
  background-color: var(--primary-light);
}

.function-tab.active {
  background-color: var(--primary-light);
  border-color: var(--primary-color);
}

.tab-icon {
  font-size: 18px;
  color: var(--primary-color);
  margin-right: 12px;
  flex-shrink: 0;
}

.tab-content {
  display: flex;
  flex-direction: column;
}

.tab-text {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  line-height: 1.4;
}

.tab-desc {
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.4;
}

.main-content {
  display: flex;
  gap: 24px;
}

.left-panel {
  flex: 1;
  background-color: #ffffff;
  border-radius: 12px;
  padding: 20px;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.panel-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.result-tag {
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 13px;
}

.toolbar {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}

.toolbar .el-button {
  border-radius: 6px;
  padding: 6px 14px;
}

.toolbar .el-button.active {
  background-color: var(--primary-light);
  color: var(--primary-color);
  border-color: var(--primary-color);
}

.image-compare {
  display: flex;
  gap: 16px;
  height: 320px;
}

.image-card {
  flex: 1;
  position: relative;
  border-radius: 8px;
  overflow: hidden;
  background-color: #f9fafb;
}

.compare-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.image-label {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 8px 12px;
  background: rgba(0, 0, 0, 0.5);
  color: #ffffff;
  font-size: 13px;
}

.detection-mark {
  position: absolute;
  top: 12px;
  right: 12px;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background-color: var(--primary-color);
  display: flex;
  align-items: center;
  justify-content: center;
}

.detection-mark::after {
  content: "✓";
  color: #ffffff;
  font-size: 18px;
  font-weight: bold;
}

.right-panel {
  width: 360px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.info-card {
  background-color: #ffffff;
  border-radius: 12px;
  padding: 16px;
}

.info-item {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid var(--border-color);
}

.info-item:last-child {
  border-bottom: none;
}

.info-label {
  font-size: 13px;
  color: var(--text-secondary);
}

.info-value {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
}

.result-card {
  background-color: #ffffff;
  border-radius: 12px;
  padding: 16px;
}

.card-header {
  display: flex;
  align-items: center;
  margin-bottom: 16px;
}

.card-header .el-icon {
  font-size: 16px;
  color: var(--primary-color);
  margin-right: 8px;
}

.card-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 32px 0;
}

.empty-icon {
  font-size: 48px;
  color: var(--success-color);
  margin-bottom: 12px;
}

.empty-text {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.empty-desc {
  font-size: 13px;
  color: var(--text-secondary);
}

.detection-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.detection-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background-color: var(--primary-light);
  border-radius: 8px;
}

.item-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
}

.item-confidence {
  font-size: 13px;
  color: var(--primary-color);
  font-weight: 600;
}

.diagnosis-content {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.6;
}

.action-buttons {
  display: flex;
  gap: 12px;
}

.btn-secondary {
  flex: 1;
  border-radius: 8px;
  padding: 10px;
  font-size: 14px;
}

.btn-primary {
  flex: 2;
  border-radius: 8px;
  padding: 10px;
  font-size: 14px;
}

.camera-container {
  position: relative;
  display: flex;
  justify-content: center;
  background: #000;
  border-radius: 8px;
  overflow: hidden;
  min-height: 360px;
}

.camera-video {
  width: 100%;
  max-height: 480px;
  object-fit: contain;
}

.camera-canvas {
  display: none;
}
</style>