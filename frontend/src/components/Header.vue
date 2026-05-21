<template>
  <div class="header-container">
    <div class="header-brand">
      <div class="brand-icon">
        <el-icon :size="20"><Monitor /></el-icon>
      </div>
      <span class="brand-title">钢铁表面缺陷检测平台</span>
    </div>

    <div class="header-actions">
      <div class="action-icons">
        <el-tooltip content="暂无新通知" placement="bottom">
          <el-icon class="action-icon" @click="handleBellClick">
            <Bell />
          </el-icon>
        </el-tooltip>

        <el-tooltip content="使用帮助" placement="bottom">
          <el-icon class="action-icon" @click="handleHelpClick">
            <QuestionFilled />
          </el-icon>
        </el-tooltip>

        <el-dropdown trigger="click" @command="handleCommand">
          <div class="user-dropdown">
            <el-avatar class="user-avatar" size="32">
              <img
                src="https://cube.elemecdn.com/0/88/03b0d39583f48206768a7534e55bcpng.png"
                alt="用户头像"
              />
            </el-avatar>
            <div class="user-info">
              <div class="user-name">{{ displayName }}</div>
              <div class="user-role">{{ displayRole }}</div>
            </div>
            <el-icon class="dropdown-icon"><CaretBottom /></el-icon>
          </div>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="profile">
                <el-icon><User /></el-icon>
                个人中心
              </el-dropdown-item>
              <el-dropdown-item command="logout" divided>
                <el-icon><SwitchButton /></el-icon>
                退出登录
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import {
  Bell,
  QuestionFilled,
  CaretBottom,
  Monitor,
  User,
  SwitchButton,
} from "@element-plus/icons-vue";

const router = useRouter();

const displayName = ref("");
const displayRole = ref("普通用户");

onMounted(() => {
  const stored = localStorage.getItem("user");
  if (stored) {
    try {
      const user = JSON.parse(stored);
      displayName.value = user.username || "";
      displayRole.value = user.is_admin ? "管理员" : "普通用户";
    } catch {
      // keep defaults
    }
  }
});

const handleBellClick = () => {
  ElMessage.info("暂无新通知");
};

const handleHelpClick = () => {
  ElMessage.info("如需帮助，请联系管理员");
};

const handleCommand = (command) => {
  if (command === "profile") {
    router.push("/profile");
  } else if (command === "logout") {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    router.push("/login");
  }
};
</script>

<style scoped>
.header-container {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}

.header-brand {
  display: flex;
  align-items: center;
  gap: 12px;
}

.brand-icon {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.15);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #ffffff;
}

.brand-title {
  font-size: 16px;
  font-weight: 600;
  color: #ffffff;
  letter-spacing: 1px;
}

.header-actions {
  display: flex;
  align-items: center;
}

.action-icons {
  display: flex;
  align-items: center;
}

.action-icon {
  font-size: 18px;
  color: rgba(255, 255, 255, 0.75);
  margin-right: 20px;
  cursor: pointer;
  transition: color 0.2s;
}

.action-icon:hover {
  color: #ffffff;
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
  background-color: rgba(255, 255, 255, 0.1);
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
  color: #ffffff;
}

.user-role {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.65);
}

.dropdown-icon {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.75);
}
</style>
