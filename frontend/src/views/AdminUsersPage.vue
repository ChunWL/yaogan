<template>
  <div class="admin-users-page">
    <div class="page-header">
      <h1 class="page-title">用户管理</h1>
      <p class="page-subtitle">管理系统中的所有用户账号</p>
    </div>

    <div class="content-card">
      <el-table :data="users" style="width: 100%" v-loading="loading" empty-text="暂无用户数据">
        <el-table-column prop="username" label="用户名" min-width="120" />
        <el-table-column prop="email" label="邮箱" min-width="180" />
        <el-table-column label="角色" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_admin ? 'danger' : 'info'" size="small">
              {{ row.is_admin ? '管理员' : '普通用户' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'danger'" size="small">
              {{ row.is_active ? '正常' : '已禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="注册时间" width="160" />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-switch
              :model-value="row.is_active"
              :disabled="row.is_admin"
              @change="(val) => handleToggleStatus(row, val)"
            />
            <el-button
              v-if="!row.is_admin"
              type="danger"
              size="small"
              style="margin-left: 8px"
              @click="handleDelete(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import request from "../utils/request.js";

const users = ref([]);
const loading = ref(false);

const fetchUsers = async () => {
  loading.value = true;
  try {
    const res = await request.get("/admin/users");
    users.value = res.data;
  } catch {
    // error handled by interceptor
  } finally {
    loading.value = false;
  }
};

const handleToggleStatus = async (row, isActive) => {
  try {
    const res = await request.put(`/admin/users/${row.id}/status`, {
      is_active: isActive,
    });
    ElMessage.success(res.message);
    row.is_active = isActive;
  } catch {
    // error handled by interceptor
  }
};

const handleDelete = async (row) => {
  await ElMessageBox.confirm(
    `确定删除用户「${row.username}」？该用户的所有数据将被永久清除，且不可恢复。`,
    "删除确认",
    {
      confirmButtonText: "确定删除",
      cancelButtonText: "取消",
      type: "warning",
      confirmButtonClass: "el-button--danger",
    }
  );
  try {
    const res = await request.delete(`/admin/users/${row.id}`);
    ElMessage.success(res.message);
    await fetchUsers();
  } catch {
    // error handled by interceptor
  }
};

onMounted(() => {
  fetchUsers();
});
</script>

<style scoped>
.admin-users-page {
  width: 100%;
}

.page-header {
  margin-bottom: 24px;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: var(--text-primary, #1f2937);
  margin-bottom: 8px;
}

.page-subtitle {
  font-size: 14px;
  color: var(--text-secondary, #6b7280);
}

.content-card {
  background-color: #ffffff;
  border-radius: 10px;
  padding: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}
</style>
