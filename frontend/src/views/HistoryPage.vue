<template>
  <div class="history-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <h1 class="page-title">检测历史记录</h1>
      <p class="page-subtitle">查看和管理您的所有检测记录</p>
    </div>

    <!-- 搜索和筛选 -->
    <div class="search-bar">
      <el-input
        v-model="searchQuery"
        placeholder="搜索检测记录..."
        size="default"
        class="search-input"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>

      <el-select
        v-model="filterStatus"
        placeholder="状态筛选"
        size="default"
        class="filter-select"
      >
        <el-option label="全部" value="" />
        <el-option label="检测完成" value="completed" />
        <el-option label="检测中" value="processing" />
        <el-option label="失败" value="failed" />
      </el-select>

      <el-select
        v-model="filterType"
        placeholder="类型筛选"
        size="default"
        class="filter-select"
      >
        <el-option label="全部" value="" />
        <el-option label="单图检测" value="single" />
        <el-option label="批量检测" value="batch" />
        <el-option label="文件夹" value="folder" />
        <el-option label="视频检测" value="video" />
      </el-select>
    </div>

    <!-- 记录列表 -->
    <div class="history-list">
      <div
        v-for="record in filteredRecords"
        :key="record.id"
        class="history-card"
        @click="viewRecord(record)"
      >
        <div class="record-preview">
          <img
            :src="record.image"
            :alt="record.filename"
            class="preview-image"
          />
          <div
            class="status-badge"
            :class="record.status"
          >
            <el-icon><component :is="getStatusIcon(record.status)" /></el-icon>
            {{ getStatusText(record.status) }}
          </div>
        </div>

        <div class="record-info">
          <div class="record-header">
            <span class="record-filename">{{ record.filename }}</span>
            <span class="record-type">{{ getTypeText(record.type) }}</span>
          </div>
          <div class="record-meta">
            <span class="meta-item">
              <el-icon><Clock /></el-icon>
              {{ record.time }}
            </span>
            <span class="meta-item">
              <el-icon><Picture /></el-icon>
              {{ record.count }} 张图片
            </span>
            <span class="meta-item">
              <el-icon><Aim /></el-icon>
              {{ record.targets }} 个目标
            </span>
          </div>
          <div class="record-tags">
            <span
              v-for="tag in record.detectedTargets"
              :key="tag"
              class="detected-tag"
            >
              {{ tag }}
            </span>
          </div>
        </div>

        <div class="record-actions">
          <el-button size="small" @click.stop="viewRecord(record)">
            <el-icon><Monitor/></el-icon>
            查看
          </el-button>
          <el-button size="small" @click.stop="downloadRecord(record)">
            <el-icon><Download/></el-icon>
            下载
          </el-button>
          <el-button
            size="small"
            type="danger"
            @click.stop="deleteRecord(record)"
          >
            <el-icon><Delete/></el-icon>
            删除
          </el-button>
        </div>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-if="filteredRecords.length === 0" class="empty-state">
      <el-icon :size="64" class="empty-icon"><Help /></el-icon>
      <p class="empty-text">暂无检测记录</p>
      <el-button type="primary" @click="goToDetection">
        <el-icon><Plus /></el-icon>
        开始检测
      </el-button>
    </div>

    <!-- 分页 -->
    <div class="pagination-wrapper">
      <el-pagination
        v-if="totalRecords > 0"
        :total="totalRecords"
        :page-size="pageSize"
        :current-page="currentPage"
        @current-change="handlePageChange"
        layout="prev, pager, next"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from "vue";
import { useRouter } from "vue-router";
import {
  Search,
  Clock,
  Picture,
  Aim,
  Monitor,
  Download,
  Delete,
  Plus,
  Help,
  CircleCheck,
  Loading,
  CircleClose,
} from "@element-plus/icons-vue";

const router = useRouter();

const searchQuery = ref("");
const filterStatus = ref("");
const filterType = ref("");
const currentPage = ref(1);
const pageSize = ref(10);

const historyRecords = ref([
  {
    id: 1,
    filename: "airport_20241201.jpg",
    image: "https://neeko-copilot.bytedance.net/api/text_to_image?prompt=satellite%20view%20of%20airport%20runway%20and%20airplanes&image_size=landscape_4_3",
    type: "single",
    status: "completed",
    time: "2024-12-01 14:30",
    count: 1,
    targets: 3,
    detectedTargets: ["飞机", "机场跑道", "建筑物"],
  },
  {
    id: 2,
    filename: "shipyard_batch.zip",
    image: "https://neeko-copilot.bytedance.net/api/text_to_image?prompt=aerial%20view%20of%20shipyard%20with%20multiple%20ships&image_size=landscape_4_3",
    type: "batch",
    status: "completed",
    time: "2024-12-01 10:15",
    count: 15,
    targets: 28,
    detectedTargets: ["船舶", "港口", "集装箱"],
  },
  {
    id: 3,
    filename: "city_area",
    image: "https://neeko-copilot.bytedance.net/api/text_to_image?prompt=aerial%20view%20of%20urban%20city%20buildings&image_size=landscape_4_3",
    type: "folder",
    status: "processing",
    time: "2024-11-30 16:45",
    count: 50,
    targets: 0,
    detectedTargets: [],
  },
  {
    id: 4,
    filename: "highway_monitor.mp4",
    image: "https://neeko-copilot.bytedance.net/api/text_to_image?prompt=highway%20traffic%20monitoring%20video%20frame&image_size=landscape_4_3",
    type: "video",
    status: "completed",
    time: "2024-11-30 09:20",
    count: 1,
    targets: 156,
    detectedTargets: ["汽车", "卡车", "道路"],
  },
  {
    id: 5,
    filename: "wind_farm.jpg",
    image: "https://neeko-copilot.bytedance.net/api/text_to_image?prompt=wind%20farm%20with%20wind%20turbines%20from%20above&image_size=landscape_4_3",
    type: "single",
    status: "failed",
    time: "2024-11-29 11:00",
    count: 1,
    targets: 0,
    detectedTargets: [],
  },
  {
    id: 6,
    filename: "industrial_zone.jpg",
    image: "https://neeko-copilot.bytedance.net/api/text_to_image?prompt=industrial%20area%20with%20tanks%20and%20factories&image_size=landscape_4_3",
    type: "single",
    status: "completed",
    time: "2024-11-28 15:30",
    count: 1,
    targets: 5,
    detectedTargets: ["油罐", "烟囱", "建筑物"],
  },
]);

const filteredRecords = computed(() => {
  return historyRecords.value.filter((record) => {
    const matchesSearch =
      !searchQuery.value ||
      record.filename.toLowerCase().includes(searchQuery.value.toLowerCase());
    const matchesStatus = !filterStatus.value || record.status === filterStatus.value;
    const matchesType = !filterType.value || record.type === filterType.value;
    return matchesSearch && matchesStatus && matchesType;
  });
});

const totalRecords = computed(() => filteredRecords.value.length);

const getStatusIcon = (status) => {
  const icons = {
    completed: CircleCheck,
    processing: Loading,
    failed: CircleClose,
  };
  return icons[status] || CircleCheck;
};

const getStatusText = (status) => {
  const texts = {
    completed: "检测完成",
    processing: "检测中",
    failed: "失败",
  };
  return texts[status] || status;
};

const getTypeText = (type) => {
  const texts = {
    single: "单图检测",
    batch: "批量检测",
    folder: "文件夹",
    video: "视频检测",
  };
  return texts[type] || type;
};

const viewRecord = (record) => {
  console.log("查看记录:", record);
  // 这里可以跳转到检测详情页面
};

const downloadRecord = (record) => {
  console.log("下载记录:", record);
};

const deleteRecord = (record) => {
  if (confirm(`确定要删除记录 "${record.filename}" 吗？`)) {
    const index = historyRecords.value.findIndex((r) => r.id === record.id);
    if (index > -1) {
      historyRecords.value.splice(index, 1);
    }
  }
};

const goToDetection = () => {
  router.push("/detection");
};

const handlePageChange = (page) => {
  currentPage.value = page;
};
</script>

<style scoped lang="scss">
.history-page {
  width: 100%;

  .page-header {
    margin-bottom: 24px;

    .page-title {
      font-size: 24px;
      font-weight: 600;
      color: var(--text-primary);
      margin-bottom: 8px;
    }

    .page-subtitle {
      font-size: 14px;
      color: var(--text-secondary);
    }
  }

  .search-bar {
    display: flex;
    gap: 16px;
    margin-bottom: 24px;
    align-items: center;

    .search-input {
      flex: 1;
      max-width: 300px;
    }

    .filter-select {
      width: 140px;
    }
  }

  .history-list {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .history-card {
    background-color: #ffffff;
    border-radius: 12px;
    padding: 20px;
    box-shadow: var(--card-shadow);
    display: flex;
    align-items: center;
    gap: 20px;
    cursor: pointer;
    transition: all 0.2s;

    &:hover {
      box-shadow: 0 4px 24px rgba(0, 0, 0, 0.08);
      transform: translateY(-2px);
    }

    .record-preview {
      position: relative;
      width: 120px;
      height: 80px;
      border-radius: 8px;
      overflow: hidden;

      .preview-image {
        width: 100%;
        height: 100%;
        object-fit: cover;
      }

      .status-badge {
        position: absolute;
        bottom: 8px;
        left: 8px;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 12px;
        display: flex;
        align-items: center;
        gap: 4px;

        &.completed {
          background-color: rgba(34, 197, 94, 0.9);
          color: white;
        }

        &.processing {
          background-color: rgba(59, 130, 246, 0.9);
          color: white;
        }

        &.failed {
          background-color: rgba(239, 68, 68, 0.9);
          color: white;
        }
      }
    }

    .record-info {
      flex: 1;
      min-width: 0;

      .record-header {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 10px;

        .record-filename {
          font-size: 15px;
          font-weight: 500;
          color: var(--text-primary);
        }

        .record-type {
          padding: 3px 8px;
          background-color: #f3f4f6;
          border-radius: 4px;
          font-size: 12px;
          color: var(--text-secondary);
        }
      }

      .record-meta {
        display: flex;
        gap: 20px;
        margin-bottom: 10px;

        .meta-item {
          display: flex;
          align-items: center;
          gap: 4px;
          font-size: 13px;
          color: var(--text-secondary);

          :deep(.el-icon) {
            font-size: 14px;
          }
        }
      }

      .record-tags {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;

        .detected-tag {
          padding: 3px 8px;
          background-color: rgba(39, 174, 96, 0.1);
          color: #27ae60;
          border-radius: 4px;
          font-size: 12px;
        }
      }
    }

    .record-actions {
      display: flex;
      gap: 8px;
    }
  }

  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 60px 0;

    .empty-icon {
      color: #9ca3af;
      margin-bottom: 16px;
    }

    .empty-text {
      font-size: 15px;
      color: var(--text-secondary);
      margin-bottom: 24px;
    }
  }

  .pagination-wrapper {
    display: flex;
    justify-content: center;
    margin-top: 32px;
  }
}
</style>