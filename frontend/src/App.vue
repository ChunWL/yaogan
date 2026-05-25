<template>
  <router-view v-if="isAuthPage" />
  <MainLayout v-else>
    <template #sidebar>
      <Sidebar />
    </template>
    <template #header>
      <Header />
    </template>
    <template #content>
      <router-view />
    </template>
  </MainLayout>
</template>

<script setup>
import { computed, onMounted } from "vue";
import { useRoute } from "vue-router";
import MainLayout from "./layouts/MainLayout.vue";
import Sidebar from "./components/Sidebar.vue";
import Header from "./components/Header.vue";
import { registerCustomScenes, buildCustomSceneConfig } from "./config/scenes";
import { getScenes } from "./api/scenes";

const route = useRoute();

const isAuthPage = computed(() => {
  const authPaths = ["/login", "/register", "/forgot-password"];
  return authPaths.includes(route.path);
});

onMounted(async () => {
  try {
    const res = await getScenes();
    if (res.success && res.data) {
      const configs = res.data
        .filter((s) => s.is_custom)
        .map(buildCustomSceneConfig);
      registerCustomScenes(configs);
    }
  } catch {
    // API not available yet (e.g. login page)
  }
});
</script>

<style scoped></style>