// router/index.js
import { createRouter, createWebHistory } from "vue-router";
import index from "@/components/jiance.vue"; // 你的检测页面

// 路由配置
const routes = [
  {
    path: "/",
    name: "index",
    component: index, // 默认打开就是检测页面
  },
];

// 创建路由实例
const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router;