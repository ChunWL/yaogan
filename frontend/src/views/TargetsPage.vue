<template>
  <div class="targets-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <h1 class="page-title">{{ sceneConfig.labels.targetLib }}</h1>
      <p class="page-subtitle">{{ sceneConfig.labels.targetLibDesc }}</p>
    </div>

    <!-- 搜索框 -->
    <div class="search-container">
      <el-input
        v-model="searchQuery"
        :placeholder="sceneConfig.labels.searchPlaceholder"
        size="default"
        class="search-input"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-cards">
      <div class="stat-card">
        <div class="stat-icon target-icon">
          <el-icon><Warning /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ totalTargets }}</div>
          <div class="stat-label">{{ sceneConfig.labels.totalTargets }}</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon category-icon">
          <el-icon><Grid /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ sceneConfig.targetGroups.length }}</div>
          <div class="stat-label">{{ sceneConfig.labels.categoryCount }}</div>
        </div>
      </div>
    </div>

    <!-- 目标类别列表 -->
    <div class="target-categories">
      <div
        v-for="category in filteredCategories"
        :key="category.id"
        class="category-card"
      >
        <div class="category-header">
          <div
            class="category-icon"
            :style="{ backgroundColor: category.color }"
          >
            <el-icon><component :is="iconMap[category.icon] || iconMap.Warning" /></el-icon>
          </div>
          <div class="category-info">
            <div class="category-name">{{ category.name }}</div>
            <div class="category-count">
              {{ category.targets.length }} {{ sceneConfig.labels.targetUnit.replace('{count}', '') }}
            </div>
          </div>
        </div>
        <div class="target-list">
          <div
            v-for="target in category.targets"
            :key="target.id"
            class="target-item"
            @click="showTargetDetail(target)"
          >
            <el-icon :size="14" class="target-item-icon"><CircleCheck /></el-icon>
            <span>{{ target.name }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-if="filteredCategories.length === 0" class="empty-state">
      <el-icon :size="64" class="empty-icon"><Help /></el-icon>
      <p class="empty-text">{{ sceneConfig.labels.noMatch }}</p>
    </div>

    <!-- 目标详情弹窗 -->
    <el-dialog
      v-if="selectedTarget"
      :title="selectedTarget.name"
      :visible.sync="showDialog"
      width="400px"
    >
      <div class="target-detail">
        <div class="detail-icon" :style="{ backgroundColor: getCategoryColor(selectedTarget.categoryId) }">
          <el-icon :size="48"><component :is="getCategoryIcon(selectedTarget.categoryId)" /></el-icon>
        </div>
        <div class="detail-info">
          <div class="detail-item">
            <span class="detail-label">所属类别</span>
            <span class="detail-value">{{ getCategoryName(selectedTarget.categoryId) }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">目标描述</span>
            <span class="detail-value">{{ selectedTarget.description }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">检测精度</span>
            <span class="detail-value">{{ selectedTarget.accuracy }}</span>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed } from "vue";
import { useRoute } from "vue-router";
import {
  Search,
  Aim,
  Grid,
  CircleCheck,
  Help,
  Setting,
  Warning,
  Remove,
  User,
  Monitor,
  Sell,
} from "@element-plus/icons-vue";
import { getSceneConfig } from "../config/scenes";

const route = useRoute();
const sceneKey = computed(() => route.query.scene || localStorage.getItem("scene") || "steel");
const sceneConfig = computed(() => getSceneConfig(sceneKey.value));

const searchQuery = ref("");
const showDialog = ref(false);
const selectedTarget = ref(null);

const iconMap = {
  Remove,
  Setting,
  Warning,
  User,
  Monitor,
  Sell,
}

const filteredCategories = computed(() => {
  const groups = sceneConfig.value.targetGroups || [];
  if (!searchQuery.value) {
    return groups;
  }
  const query = searchQuery.value.toLowerCase();
  return groups.map((category) => ({
    ...category,
    targets: category.targets.filter((target) =>
      target.name.toLowerCase().includes(query)
    ),
  })).filter((category) =>
    category.name.toLowerCase().includes(query) || category.targets.length > 0
  );
});

const totalTargets = computed(() => {
  const groups = sceneConfig.value.targetGroups || [];
  return groups.reduce((sum, category) => sum + category.targets.length, 0);
});

const getCategoryColor = (categoryId) => {
  const groups = sceneConfig.value.targetGroups || [];
  const category = groups.find((c) => c.id === categoryId);
  return category ? category.color : "#6b7280";
};

const getCategoryIcon = (categoryId) => {
  const groups = sceneConfig.value.targetGroups || [];
  const category = groups.find((c) => c.id === categoryId);
  const iconName = category ? category.icon : "Warning";
  return iconMap[iconName] || Warning;
};

const getCategoryName = (categoryId) => {
  const groups = sceneConfig.value.targetGroups || [];
  const category = groups.find((c) => c.id === categoryId);
  return category ? category.name : "未知";
};

const showTargetDetail = (target) => {
  selectedTarget.value = target;
  showDialog.value = true;
};
</script>

<style scoped>
.targets-page {
  width: 100%;
}

.page-header {
  margin-bottom: 24px;
}

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

.search-container {
  margin-bottom: 24px;
}

.search-input {
  max-width: 300px;
}

.stats-cards {
  display: flex;
  gap: 20px;
  margin-bottom: 24px;
}

.stat-card {
  flex: 1;
  max-width: 200px;
  background-color: #ffffff;
  border-radius: 12px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
}

.stat-icon {
  width: 50px;
  height: 50px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 24px;
}

.stat-icon.target-icon {
  background-color: #1a56db;
}

.stat-icon.category-icon {
  background-color: #dc2626;
}

.stat-info .stat-value {
  font-size: 24px;
  font-weight: 600;
  color: var(--text-primary);
}

.stat-info .stat-label {
  font-size: 13px;
  color: var(--text-secondary);
}

.target-categories {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 24px;
}

.category-card {
  background-color: #ffffff;
  border-radius: 12px;
  padding: 20px;
  transition: all 0.2s;
}

.category-card:hover {
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.08);
}

.category-header {
  display: flex;
  align-items: center;
  margin-bottom: 16px;
}

.category-icon {
  width: 50px;
  height: 50px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 24px;
  margin-right: 16px;
}

.category-info .category-name {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.category-info .category-count {
  font-size: 13px;
  color: var(--text-secondary);
}

.target-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.target-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  background-color: #f3f4f6;
  border-radius: 20px;
  font-size: 14px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s;
}

.target-item:hover {
  background-color: rgba(26, 86, 219, 0.1);
  color: #1a56db;
}

.target-item-icon {
  color: #1a56db;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 0;
}

.empty-icon {
  color: #9ca3af;
  margin-bottom: 16px;
}

.empty-text {
  font-size: 15px;
  color: var(--text-secondary);
}

.target-detail {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20px 0;
}

.detail-icon {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  margin-bottom: 20px;
}

.detail-info {
  width: 100%;
}

.detail-item {
  display: flex;
  justify-content: space-between;
  padding: 12px 0;
  border-bottom: 1px solid #f3f4f6;
}

.detail-item:last-child {
  border-bottom: none;
}

.detail-label {
  font-size: 14px;
  color: var(--text-secondary);
}

.detail-value {
  font-size: 14px;
  color: var(--text-primary);
  font-weight: 500;
}
</style>
