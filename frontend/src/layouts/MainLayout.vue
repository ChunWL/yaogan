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
  background-color: var(--app-sidebar-bg);
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  box-shadow: 1px 0 8px rgba(0, 0, 0, 0.04);
}

.main-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.header {
  height: 64px;
  background: var(--app-header-gradient);
  border-bottom: none;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  color: #ffffff;
}

.content {
  flex: 1;
  padding: 24px 32px;
  overflow-y: auto;
  background-color: var(--app-bg);
}
</style>