<template>
  <div class="scene-selector">
    <div class="page-header">
      <div class="breadcrumb">
        <span>工作台</span>
        <span class="separator">›</span>
        <span class="active">更多功能</span>
      </div>
      <h1 class="page-title">选择检测场景</h1>
      <p class="page-subtitle">选择不同的检测场景，系统将自动切换对应的检测模型</p>
    </div>

    <div class="scene-grid">
      <div
        v-for="scene in sceneList"
        :key="scene.key"
        class="scene-card"
        @click="goToScene(scene)"
      >
        <div class="scene-icon-wrapper">
          <el-icon :size="32"><component :is="sceneIconMap[scene.icon] || sceneIconMap.Monitor" /></el-icon>
        </div>
        <div class="scene-info">
          <h3 class="scene-name">{{ scene.name }}</h3>
          <p class="scene-desc">{{ scene.description }}</p>
        </div>
        <div class="scene-footer">
          <el-tag size="small" type="info" effect="plain">
            模型: {{ scene.defaultModel }}
          </el-tag>
          <el-icon class="scene-arrow"><ArrowRight /></el-icon>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue"
import { useRouter } from "vue-router"
import { Monitor, Picture, ArrowRight } from "@element-plus/icons-vue"
import { SCENE_LIST } from "../config/scenes"

const router = useRouter()

const sceneList = computed(() => SCENE_LIST)

const sceneIconMap = {
  Monitor,
  Picture,
}

function goToScene(scene) {
  localStorage.setItem("scene", scene.key)
  router.push({ path: "/detection", query: { scene: scene.key } })
}
</script>

<style scoped>
.scene-selector {
  width: 100%;
}

.page-header {
  margin-bottom: 32px;
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

.scene-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 20px;
}

.scene-card {
  background: #ffffff;
  border-radius: 12px;
  padding: 24px;
  cursor: pointer;
  transition: all 0.25s;
  border: 2px solid transparent;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.scene-card:hover {
  border-color: var(--primary-color);
  box-shadow: 0 4px 20px rgba(26, 86, 219, 0.12);
  transform: translateY(-2px);
}

.scene-icon-wrapper {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  background: var(--primary-light);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--primary-color);
}

.scene-info h3 {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 6px;
}

.scene-info p {
  font-size: 14px;
  color: var(--text-secondary);
  line-height: 1.5;
}

.scene-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 12px;
  border-top: 1px solid var(--border-color);
}

.scene-arrow {
  color: var(--text-secondary);
  font-size: 16px;
}

.scene-card:hover .scene-arrow {
  color: var(--primary-color);
}
</style>
