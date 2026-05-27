import { createRouter, createWebHistory } from "vue-router";

const routes = [
  {
    path: "/",
    redirect: "/login",
  },
  {
    path: "/login",
    name: "登录",
    component: () => import("../views/LoginPage.vue"),
  },
  {
    path: "/register",
    name: "注册",
    component: () => import("../views/RegisterPage.vue"),
  },
  {
    path: "/forgot-password",
    name: "忘记密码",
    component: () => import("../views/ForgotPasswordPage.vue"),
  },
  {
    path: "/reset-password",
    name: "重置密码",
    component: () => import("../views/ResetPasswordPage.vue"),
  },
  {
    path: "/scenes",
    name: "更多功能",
    component: () => import("../views/SceneSelector.vue"),
  },
  {
    path: "/detection",
    name: "缺陷检测",
    component: () => import("../views/DetectionPage.vue"),
  },
  {
    path: "/history",
    name: "历史记录",
    component: () => import("../views/HistoryPage.vue"),
  },
  {
    path: "/targets",
    name: "缺陷类型库",
    component: () => import("../views/TargetsPage.vue"),
  },
  {
    path: "/profile",
    name: "个人中心",
    component: () => import("../views/ProfilePage.vue"),
  },
  {
    path: "/admin/users",
    name: "用户管理",
    component: () => import("../views/AdminUsersPage.vue"),
  },
  {
    path: "/announcements",
    name: "系统公告",
    component: () => import("../views/AnnouncementsPage.vue"),
  },
];

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
});

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem("token");
  const authPaths = ["/login", "/register", "/forgot-password", "/reset-password"];

  function isTokenExpired(t) {
    try {
      const payload = JSON.parse(atob(t.split(".")[1]));
      return payload.exp * 1000 < Date.now();
    } catch {
      return true;
    }
  }

  function clearAuth() {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
  }

  if (token && isTokenExpired(token)) {
    clearAuth();
    if (authPaths.includes(to.path)) {
      next();
    } else {
      next("/login");
    }
    return;
  }

  // Going to login page clears any existing auth (soft logout)
  if (to.path === "/login") {
    clearAuth();
    next();
    return;
  }

  if (authPaths.includes(to.path)) {
    next();
  } else if (!token) {
    next("/login");
  } else {
    next();
  }
});

export default router;
