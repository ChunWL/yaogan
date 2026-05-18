<template>
  <div class="header-container">
    <div class="breadcrumbs">
      <el-icon class="breadcrumb-icon"><House /></el-icon>
      <span class="breadcrumb-separator">/</span>
      <span class="breadcrumb-text">智能检测</span>
    </div>

    <div class="header-actions">
      <el-tag type="success" effect="light" class="status-tag">
        <el-icon class="el-icon--left"><Check /></el-icon>
        检测完成
      </el-tag>

      <div class="action-icons">
        <el-icon class="action-icon"><Grid /></el-icon>
        <el-icon class="action-icon"><Bell /></el-icon>
        <el-icon class="action-icon"><QuestionFilled /></el-icon>
        <div class="user-dropdown">
          <el-avatar class="user-avatar" size="32">
            <img
              src="https://cube.elemecdn.com/0/88/03b0d39583f48206768a7534e55bcpng.png"
              alt="用户头像"
            />
          </el-avatar>
          <div class="user-info">
            <div class="user-name">Lily</div>
            <div class="user-role">普通用户</div>
          </div>
          <el-icon class="dropdown-icon"><CaretBottom /></el-icon>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import {
  Check,
  Grid,
  Bell,
  QuestionFilled,
  CaretBottom,
  House,
} from "@element-plus/icons-vue";
</script>

<style scoped>
.header-container {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}

.breadcrumbs {
  display: flex;
  align-items: center;
}

.breadcrumb-icon {
  font-size: 14px;
  color: var(--text-secondary);
}

.breadcrumb-separator {
  font-size: 14px;
  color: var(--text-secondary);
  margin: 0 8px;
}

.breadcrumb-text {
  font-size: 14px;
  color: var(--text-primary);
}

.header-actions {
  display: flex;
  align-items: center;
}

.status-tag {
  margin-right: 24px;
  padding: 6px 12px;
  border-radius: 20px;
  font-size: 13px;
}

.action-icons {
  display: flex;
  align-items: center;
}

.action-icon {
  font-size: 18px;
  color: var(--text-secondary);
  margin-right: 20px;
  cursor: pointer;
  transition: color 0.2s;
}

.action-icon:hover {
  color: var(--primary-color);
}

.user-dropdown {
  display: flex;
  align-items: center;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 6px;
  transition: background-color 0.2s;
}

.user-dropdown:hover {
  background-color: #f3f4f6;
}

.user-avatar {
  margin-right: 8px;
}

.user-info {
  margin-right: 6px;
}

.user-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
}

.user-role {
  font-size: 12px;
  color: var(--text-secondary);
}

.dropdown-icon {
  font-size: 12px;
  color: var(--text-secondary);
}
</style>