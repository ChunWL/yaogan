<template>
  <div class="main-layout">
    <aside class="sidebar">
      <slot name="sidebar"></slot>
    </aside>

    <div class="main-container">
      <header class="header">
        <slot name="header"></slot>
      </header>

      <main class="content">
        <slot name="content"></slot>
      </main>
    </div>
  </div>
</template>

<script setup></script>

<style scoped>
.main-layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

.sidebar {
  width: 200px;
  background-color: #ffffff;
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
}

.main-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.header {
  height: 64px;
  background-color: #ffffff;
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
}

.content {
  flex: 1;
  padding: 24px 32px;
  overflow-y: auto;
  background-color: #f0f7f2;
}
</style>