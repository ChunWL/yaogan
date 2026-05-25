<template>
  <div class="sidebar-container">
    <div class="logo-section">
      <div class="logo-icon">
        <Monitor style="color: white; font-size: 20px" />
      </div>
      <div class="logo-text">
        <div class="logo-title">智检</div>
        <div class="logo-subtitle">智能检测 · AI Vision</div>
      </div>
    </div>

    <div class="nav-menu">
      <div
        v-for="item in menuList"
        :key="item.path"
        class="nav-item"
        :class="{ active: currentPath === item.path }"
        @click="handleMenuClick(item)"
      >
        <el-icon :size="18" class="nav-icon"><component :is="item.icon" /></el-icon>
        <span class="nav-text">{{ item.name }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, onMounted } from "vue";
import { useRouter, useRoute } from "vue-router";
import {
  Monitor,
  Picture,
  Clock,
  ChatDotRound,
  DataLine,
  User,
  Setting,
  Expand,
  Bell,
} from "@element-plus/icons-vue";
import { getSceneConfig } from "../config/scenes";

const router = useRouter();
const route = useRoute();

const isAdmin = ref(false);

onMounted(() => {
  const stored = localStorage.getItem("user");
  if (stored) {
    try {
      const user = JSON.parse(stored);
      isAdmin.value = user.is_admin === true;
    } catch {
      // keep false
    }
  }
});

const menuList = computed(() => {
  const items = [
    {
      name: currentSceneName.value,
      icon: Picture,
      path: "/detection",
    },
    {
      name: "历史记录",
      icon: Clock,
      path: "/history",
    },
    {
      name: "智能问答",
      icon: ChatDotRound,
      path: "/qa",
    },
    {
      name: targetLibName.value,
      icon: DataLine,
      path: "/targets",
    },
    {
      name: "更多功能",
      icon: Expand,
      path: "/scenes",
    },
    {
      name: "系统公告",
      icon: Bell,
      path: "/announcements",
    },
    {
      name: "个人中心",
      icon: User,
      path: "/profile",
    },
  ];
  if (isAdmin.value) {
    items.push({
      name: "用户管理",
      icon: Setting,
      path: "/admin/users",
    });
  }
  return items;
});

const currentPath = computed(() => route.path);

const currentSceneKey = computed(() => {
  return route.query.scene || localStorage.getItem("scene") || "steel";
});

const currentSceneName = computed(() => {
  const sceneKey = route.query.scene || localStorage.getItem("scene") || "steel";
  const cfg = getSceneConfig(sceneKey);
  return cfg.name;
});

const targetLibName = computed(() => {
  const sceneKey = route.query.scene || localStorage.getItem("scene") || "steel";
  const cfg = getSceneConfig(sceneKey);
  return cfg.labels.targetLib;
});

const sceneQuery = () => {
  const scene = route.query.scene || localStorage.getItem("scene")
  return scene ? { scene } : undefined
}

const handleMenuClick = (item) => {
  const scenePages = ["/detection", "/targets", "/history"]
  const query = scenePages.includes(item.path) ? sceneQuery() : undefined
  router.push(query ? { path: item.path, query } : item.path)
};

</script>

<style scoped>
.sidebar-container {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.logo-section {
  height: 72px;
  display: flex;
  align-items: center;
  padding: 0 12px;
  border-bottom: 1px solid var(--border-color);
}

.logo-icon {
  width: 40px;
  height: 40px;
  border-radius: 6px;
  background-color: var(--primary-color);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 10px;
  flex-shrink: 0;
}

.logo-text {
  overflow: hidden;
}

.logo-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  line-height: 1.3;
  white-space: nowrap;
}

.logo-subtitle {
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 2px;
  line-height: 1.3;
  white-space: nowrap;
}

.nav-menu {
  flex: 1;
  padding: 16px 12px;
}

.nav-item {
  display: flex;
  align-items: center;
  flex-direction: row;
  padding: 16px 12px;
  border-radius: 8px;
  margin-bottom: 8px;
  cursor: pointer;
  transition: all 0.2s;
  text-align: left;
  border-left: 3px solid transparent;
}

.nav-item:hover {
  background-color: var(--primary-light);
}

.nav-item.active {
  background-color: var(--primary-light);
  border-left: 3px solid var(--primary-color);
  color: var(--primary-color);
  font-weight: 500;
}

.nav-item.active .nav-icon {
  color: var(--primary-color);
}

.nav-icon {
  font-size: 18px;
  margin-right: 12px;
  color: var(--text-secondary);
  flex-shrink: 0;
}

.nav-text {
  font-size: 14px;
  line-height: 1.4;
}

.sidebar-divider {
  font-size: 11px;
  color: var(--text-secondary);
  padding: 12px 12px 6px;
  text-transform: uppercase;
  letter-spacing: 1px;
  border-top: 1px solid var(--border-color);
  margin-top: 8px;
}
</style>