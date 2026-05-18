<template>
  <div class="wrap">
    <h1>🎯 目标检测系统</h1>
    <button @click="testConnect">测试前后端连接</button>
    <div class="result" v-if="res">{{ res }}</div>
  </div>
</template>

<script setup>
import { ref } from "vue";

const res = ref("");

const testConnect = async () => {
  try {
    const response = await fetch("http://localhost:8000/api/connect");
    const data = await response.json();
    res.value = data.message;
  } catch (e) {
    res.value = "连接后端失败，请检查后端是否启动";
  }
};
</script>

<style scoped>
.wrap {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
}

button {
  padding: 10px 20px;
  font-size: 16px;
  margin: 20px 0;
  cursor: pointer;
}

.result {
  font-size: 18px;
  color: green;
  font-weight: bold;
}
</style>