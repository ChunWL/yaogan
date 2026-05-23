<template>
  <div class="detection-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="breadcrumb">
        <span>工作台</span>
        <span class="separator">›</span>
        <span class="active">{{ sceneConfig.name }}</span>
      </div>
      <div class="page-title-row">
        <h1 class="page-title">{{ sceneConfig.name }}</h1>
        <el-tag
          v-if="sceneKey !== 'steel'"
          size="small"
          effect="plain"
          class="scene-badge"
          @click="$router.push('/scenes')"
          style="cursor:pointer"
        >
          <el-icon style="margin-right:4px"><Refresh /></el-icon>
          切换场景
        </el-tag>
      </div>
      <p class="page-subtitle">{{ sceneConfig.subtitle }}</p>
    </div>

    <!-- 模型选择器 -->
    <div class="model-selector">
      <el-select v-model="selectedModel" style="width: 180px">
        <el-option
          v-for="m in availableModels"
          :key="m"
          :label="m"
          :value="m"
        />
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
          <el-tag v-if="hasResults" type="success" effect="light" class="result-tag">
            <el-icon class="el-icon--left"><Check /></el-icon>
            {{ isBatch ? `共 ${batchResults.length} 张` : '检测完成' }}
          </el-tag>
        </div>

        <!-- 工具栏 -->
        <div class="toolbar" v-if="hasResults && !isVideo">
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
            :disabled="!isBatch"
            @click="compareMode = 'grid'"
          >
            <el-icon><Grid /></el-icon>
            栅格对比
          </el-button>
        </div>

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

        <!-- 视频处理进度 -->
        <div v-if="isVideo && (videoStatus === 'uploading' || videoStatus === 'processing')" class="video-progress">
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

        <!-- 视频检测失败 -->
        <div v-else-if="isVideo && videoStatus === 'failed'" class="video-failed">
          <el-icon :size="64" class="video-failed-icon"><CircleClose /></el-icon>
          <p class="video-failed-text">视频检测失败</p>
          <p class="video-failed-desc">请检查视频文件是否有效，或稍后重试</p>
        </div>

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

        <!-- 空状态 -->
        <div v-else-if="!hasResults" class="empty-preview">
          <el-icon :size="64" class="empty-icon"><Picture /></el-icon>
          <p class="empty-text">请选择检测模式并上传图片</p>
          <p class="empty-desc">支持单图、批量、摄像头、视频检测</p>
        </div>

        <!-- 并排对比模式 -->
        <div v-else-if="compareMode === 'side'" class="side-compare">
          <div v-if="isBatch" class="back-to-grid" @click="compareMode = 'grid'">
            <el-icon><ArrowLeft /></el-icon>
            返回全部结果
          </div>
          <div class="image-card">
            <img
              :src="currentOriginalUrl"
              alt="原始图片"
              class="compare-image"
            />
            <div class="image-label">原始图片</div>
          </div>
          <div class="image-card">
            <img
              :src="currentResultUrl"
              alt="检测结果"
              class="compare-image"
            />
            <div class="image-label">检测结果</div>
            <div class="detection-mark" v-if="currentDetectionResult"></div>
          </div>
        </div>

        <!-- 栅格模式 (批量结果) -->
        <div v-else class="grid-compare">
          <div
            v-for="(item, index) in batchResults"
            :key="index"
            class="grid-item"
            @click="viewBatchItem(index)"
          >
            <div class="grid-image-wrapper">
              <img
                v-if="item.success"
                :src="item.result.result_image_url"
                :alt="item.filename"
                class="grid-image"
              />
              <div v-else class="grid-image-failed">
                <el-icon :size="32"><CircleClose /></el-icon>
                <span>检测失败</span>
              </div>
            </div>
            <div class="grid-info">
              <div class="grid-filename" :title="item.filename">{{ item.filename }}</div>
              <div class="grid-meta" v-if="item.success">
                <span>{{ item.result.total_objects }} 个目标</span>
                <span>{{ item.result.detection_time }}s</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧信息面板 -->
      <div class="right-panel">
        <!-- 批量汇总 -->
        <div v-if="isBatch" class="info-card">
          <div class="info-item">
            <span class="info-label">检测图片</span>
            <span class="info-value">{{ batchResults.length }} 张</span>
          </div>
          <div class="info-item">
            <span class="info-label">成功/失败</span>
            <span class="info-value">
              {{ successCount }} / {{ failCount }}
            </span>
          </div>
          <div class="info-item">
            <span class="info-label">检测总目标</span>
            <span class="info-value">{{ totalBatchObjects }}</span>
          </div>
        </div>

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
            <span class="info-label">含{{ sceneConfig.labels.target }}帧数</span>
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
            <span class="card-title">{{ sceneConfig.labels.target }}类别统计</span>
          </div>
          <div v-if="videoSummary.total_objects === 0" class="empty-state">
            <el-icon class="empty-icon"><CircleCheck /></el-icon>
            <p class="empty-text">{{ sceneConfig.labels.empty }}</p>
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
          <div v-if="isVideo && videoSummary && videoSummary.total_objects > 0" class="detection-list">
            <div
              v-for="(count, className) in videoSummary.class_counts"
              :key="className"
              class="detection-item"
            >
              <span class="item-name">{{ className }}</span>
              <span class="item-confidence">{{ count }} 个</span>
            </div>
          </div>
          <div v-else-if="!currentDetectionResult || currentDetectionResult.total_objects === 0" class="empty-state">
            <el-icon class="empty-icon"><CircleCheck /></el-icon>
            <p class="empty-text">{{ sceneConfig.labels.empty }}</p>
            <p class="empty-desc">{{ sceneConfig.labels.emptyDesc }}</p>
          </div>
          <div v-else class="detection-list">
            <div
              v-for="(box, index) in currentDetectionResult.boxes"
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
            <p v-if="isVideo && videoSummary">
              {{ formatLabel(sceneConfig.labels.videoDiagnosis, { count: videoSummary.total_objects, frames: videoSummary.frames_with_defects, time: videoSummary.detection_time }) }}
            </p>
            <p v-else-if="!currentDetectionResult">{{ sceneConfig.labels.empty }}</p>
            <p v-else>
              {{ formatLabel(sceneConfig.labels.diagnosis, { count: currentDetectionResult.total_objects, time: currentDetectionResult.detection_time, model: currentDetectionResult.model_name }) }}
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

  </div>
</template>

<script setup>
import { ref, computed, onUnmounted, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
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
  CircleClose,
  ChatDotRound,
  Refresh,
  Minus,
  ArrowLeft,
  VideoCamera,
  VideoPause,
  VideoPlay,
} from "@element-plus/icons-vue";
import { detectSingleImage, detectBatchImages, detectVideo, getVideoProgress, getModelsList, getCameraWsUrl } from "../api/detection";
import { getSceneConfig } from "../config/scenes";

const route = useRoute();
const router = useRouter();

function resolveSceneKey() {
  return route.query.scene || localStorage.getItem("scene") || "steel";
}
const sceneKey = computed(() => resolveSceneKey());
const sceneConfig = computed(() => getSceneConfig(sceneKey.value));

function formatLabel(template, params) {
  return template.replace(/\{(\w+)\}/g, (_, key) => params[key] ?? key);
}

const selectedModel = ref("yolo11n");
const availableModels = ref(["yolo11n", "gt"]);

onMounted(async () => {
  // 如果 URL 没有 scene 参数但 localStorage 有，自动补充
  if (!route.query.scene && localStorage.getItem("scene")) {
    router.replace({ query: { scene: localStorage.getItem("scene") } })
  }
  // 同步当前场景到 localStorage
  if (route.query.scene) {
    localStorage.setItem("scene", route.query.scene)
  }
  // 根据场景设置默认模型
  selectedModel.value = sceneConfig.value.defaultModel;
  try {
    const res = await getModelsList();
    if (res.data) {
      availableModels.value = res.data;
      if (!availableModels.value.includes(selectedModel.value)) {
        selectedModel.value = availableModels.value[0] || "yolo11n";
      }
    }
  } catch (e) {
    // fallback to defaults
  }
});
const activeTab = ref("single");
const compareMode = ref("side");
const isBatch = ref(false);
const isDetecting = ref(false);

const currentOriginalUrl = ref("");
const currentResultUrl = ref("");
const currentDetectionResult = ref(null);

const batchResults = ref([]);
const batchObjectUrls = [];

// Real-time camera detection
const cameraMode = ref(false);
const cameraDetecting = ref(false);
const cameraPaused = ref(false);
const cameraFps = ref(0);
const cameraVideoRef = ref(null);
const cameraOverlayRef = ref(null);
const lastCameraBoxes = ref([]);
let cameraWs = null;
let cameraAnimFrameId = null;
let cameraFrameCount = 0;
let cameraLastFpsTime = 0;
let cameraStream = null;

const videoTaskId = ref("");
const videoStatus = ref("idle"); // idle | uploading | processing | completed | failed
const videoProgress = ref(0);
const videoProcessedFrames = ref(0);
const videoTotalFrames = ref(0);
const videoResultUrl = ref("");
const videoSummary = ref(null);
let pollingTimer = null;

const hasResults = computed(() => {
  if (isBatch.value) return batchResults.value.length > 0;
  if (isVideo.value && videoStatus.value === "completed") return true;
  return !!currentDetectionResult.value;
});

const successCount = computed(() =>
  batchResults.value.filter((r) => r.success).length
);

const failCount = computed(() => batchResults.value.length - successCount.value);

const totalBatchObjects = computed(() =>
  batchResults.value
    .filter((r) => r.success)
    .reduce((sum, r) => sum + (r.result?.total_objects || 0), 0)
);

const isVideo = computed(() => activeTab.value === "video");

const functionTabs = [
  { key: "single", name: "单图检测", desc: "快速识别一张图片", icon: Picture, accept: "image/*", multiple: false },
  { key: "batch", name: "批量检测", desc: "一次处理多张图片", icon: Plus, accept: "image/*", multiple: true },
  { key: "camera", name: "摄像头检测", desc: "调用摄像头实时检测", icon: Camera, accept: "video/*", multiple: false },
  { key: "video", name: "视频检测", desc: "上传视频自动分析", icon: Monitor, accept: "video/*", multiple: false },
];

const resetResults = () => {
  if (cameraMode.value) {
    stopCameraDetection();
  }
  batchObjectUrls.forEach((url) => URL.revokeObjectURL(url));
  batchObjectUrls.length = 0;
  batchResults.value = [];
  isBatch.value = false;
  currentOriginalUrl.value = "";
  currentResultUrl.value = "";
  currentDetectionResult.value = null;
  compareMode.value = "side";
  stopPolling();
  videoStatus.value = "idle";
  videoResultUrl.value = "";
  videoSummary.value = null;
};

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

const performSingleDetection = async (file) => {
  const loading = ElLoading.service({
    lock: true,
    text: "正在检测中...",
    background: "rgba(0, 0, 0, 0.7)",
  });

  try {
    isDetecting.value = true;
    resetResults();

    const formData = new FormData();
    formData.append("file", file);
    formData.append("model_name", selectedModel.value);
    formData.append("scene", sceneKey.value);

    const url = URL.createObjectURL(file);
    currentOriginalUrl.value = url;
    batchObjectUrls.push(url);

    const response = await detectSingleImage(formData);
    if (response.success && response.data) {
      currentDetectionResult.value = response.data;
      currentResultUrl.value = response.data.result_image_url;
      compareMode.value = "side";
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

const performBatchDetection = async (files) => {
  const loading = ElLoading.service({
    lock: true,
    text: `正在批量检测 ${files.length} 张图片...`,
    background: "rgba(0, 0, 0, 0.7)",
  });

  try {
    isDetecting.value = true;
    resetResults();
    isBatch.value = true;
    compareMode.value = "grid";

    const formData = new FormData();
    const objectUrls = [];
    for (const file of files) {
      formData.append("files", file);
      objectUrls.push(URL.createObjectURL(file));
    }
    formData.append("model_name", selectedModel.value);
    formData.append("scene", sceneKey.value);

    const response = await detectBatchImages(formData);
    if (response.success && response.data) {
      // Pair each result with its Object URL
      batchResults.value = response.data.map((item, i) => ({
        ...item,
        objectUrl: objectUrls[i],
      }));
      batchObjectUrls.push(...objectUrls);

      // Set current to the first successful result
      const firstSuccess = batchResults.value.find((r) => r.success);
      if (firstSuccess) {
        currentOriginalUrl.value = firstSuccess.objectUrl;
        currentResultUrl.value = firstSuccess.result.result_image_url;
        currentDetectionResult.value = firstSuccess.result;
      }

      ElMessage.success(`批量检测完成，共处理 ${response.total} 张图片`);
    } else {
      ElMessage.error(response.message || "检测失败");
    }
  } catch (error) {
    console.error("批量检测错误:", error);
    ElMessage.error("批量检测失败，请稍后重试");
  } finally {
    isDetecting.value = false;
    loading.close();
  }
};

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
    formData.append("scene", sceneKey.value);
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
  let failCount = 0;
  pollingTimer = setInterval(async () => {
    try {
      const response = await getVideoProgress(videoTaskId.value);
      failCount = 0;
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
      failCount++;
      if (failCount >= 5) {
        stopPolling();
        videoStatus.value = "failed";
        ElMessage.error("获取检测进度失败，请检查后端服务");
      }
    }
  }, 1000);
};

const stopPolling = () => {
  if (pollingTimer) {
    clearInterval(pollingTimer);
    pollingTimer = null;
  }
};

const viewBatchItem = (index) => {
  const item = batchResults.value[index];
  if (!item || !item.success) return;
  compareMode.value = "side";
  currentOriginalUrl.value = item.objectUrl;
  currentResultUrl.value = item.result.result_image_url;
  currentDetectionResult.value = item.result;
};

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
    cameraStream = await navigator.mediaDevices.getUserMedia({
      video: { width: 640, height: 480, facingMode: "environment" },
    });
    if (cameraVideoRef.value) {
      cameraVideoRef.value.srcObject = cameraStream;
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
    const wsUrl = getCameraWsUrl(token, selectedModel.value);
    cameraWs = new WebSocket(wsUrl);

    cameraWs.onopen = () => {
      cameraDetecting.value = true;
      startFrameCapture();
    };

    cameraWs.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.error) {
          console.warn("Camera WS error:", data.error);
          return;
        }
        lastCameraBoxes.value = data.boxes;
        drawDetectionBoxes(data.boxes);
        // Update right panel
        currentDetectionResult.value = {
          total_objects: data.total_objects,
          boxes: data.boxes,
          model_name: selectedModel.value,
        };
      } catch (e) {
        console.warn("Failed to parse camera WS message:", e);
      }
    };

    cameraWs.onclose = () => {
      stopCameraDetection();
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

const stopCameraDetection = () => {
  stopFrameCapture();
  if (cameraWs) {
    cameraWs.close();
    cameraWs = null;
  }
  if (cameraStream) {
    cameraStream.getTracks().forEach((t) => t.stop());
    cameraStream = null;
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
  cameraPaused.value = true;

  try {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("model_name", selectedModel.value);
    formData.append("scene", sceneKey.value);

    const response = await detectSingleImage(formData);
    if (response.success && response.data) {
      ElMessage.success("快照已保存到历史记录！");
    } else {
      ElMessage.error(response.message || "保存失败");
    }
  } catch (error) {
    console.error("保存快照错误:", error);
    ElMessage.error("保存快照失败");
  } finally {
    cameraPaused.value = false;
  }
};

const handleRedetect = () => {
  stopPolling();
  videoStatus.value = "idle";
  const tabKey = activeTab.value;
  const input = document.querySelector(`.function-tab[data-key="${tabKey}"] .file-input`);
  if (input) {
    input.value = "";
    input.click();
  }
};

onUnmounted(() => {
  stopCameraDetection();
  stopPolling();
  batchObjectUrls.forEach((url) => URL.revokeObjectURL(url));
});
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

.page-title-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.page-title-row .page-title {
  margin-bottom: 0;
}

.scene-badge {
  font-size: 12px;
  padding: 0 10px;
  height: 26px;
  line-height: 26px;
  border-radius: 4px;
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

/* 空状态 */
.empty-preview {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 320px;
  color: var(--text-secondary);
}

.empty-preview .empty-icon {
  color: #d1d5db;
  margin-bottom: 16px;
}

.empty-preview .empty-text {
  font-size: 16px;
  font-weight: 500;
  margin-bottom: 4px;
}

.empty-preview .empty-desc {
  font-size: 13px;
}

/* 并排对比 */
.side-compare {
  display: flex;
  gap: 16px;
  height: 320px;
  position: relative;
}

.back-to-grid {
  position: absolute;
  top: -40px;
  left: 0;
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: var(--primary-color);
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  transition: background 0.2s;
}

.back-to-grid:hover {
  background-color: var(--primary-light);
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

/* 栅格对比 */
.grid-compare {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 16px;
  min-height: 200px;
  max-height: 500px;
  overflow-y: auto;
}

.grid-item {
  background: #f9fafb;
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.2s;
  border: 2px solid transparent;
}

.grid-item:hover {
  border-color: var(--primary-color);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  transform: translateY(-2px);
}

.grid-image-wrapper {
  width: 100%;
  height: 140px;
  overflow: hidden;
}

.grid-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.grid-image-failed {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: #fef2f2;
  color: #ef4444;
  gap: 8px;
  font-size: 13px;
}

.grid-info {
  padding: 10px 12px;
}

.grid-filename {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.grid-meta {
  display: flex;
  justify-content: space-between;
  margin-top: 4px;
  font-size: 12px;
  color: var(--text-secondary);
}

/* 右侧面板 */
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

.camera-video {
  width: 100%;
  max-height: 480px;
  object-fit: contain;
}

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
</style>
