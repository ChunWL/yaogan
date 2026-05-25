<template>
  <div class="announcements-page">
    <div class="page-header">
      <div class="page-header-row">
        <div>
          <h1 class="page-title">系统公告</h1>
          <p class="page-subtitle">管理员发布的公告通知</p>
        </div>
        <el-button v-if="isAdmin" type="primary" @click="openCreate">
          <el-icon><Plus /></el-icon> 发布公告
        </el-button>
      </div>
    </div>

    <div v-if="loading" class="loading-state">
      <el-skeleton :rows="3" animated />
    </div>

    <div v-else-if="list.length === 0" class="empty-state">
      <el-empty description="暂无公告" />
    </div>

    <div v-else class="announcement-list">
      <div
        v-for="item in list"
        :key="item.id"
        class="announcement-card"
      >
        <div class="announcement-icon">
          <el-icon :size="24"><WarningFilled /></el-icon>
        </div>
        <div class="announcement-body">
          <div v-if="item.title" class="announcement-title">{{ item.title }}</div>
          <div class="announcement-message">{{ item.message }}</div>
          <div class="announcement-time">{{ item.created_at }}</div>
        </div>
        <div v-if="isAdmin" class="announcement-actions">
          <el-button size="small" link type="primary" @click="openEdit(item)">
            <el-icon><Edit /></el-icon>
          </el-button>
          <el-button size="small" link type="danger" @click="handleDelete(item)">
            <el-icon><Delete /></el-icon>
          </el-button>
        </div>
      </div>
    </div>

    <!-- Create/Edit Dialog -->
    <el-dialog
      v-model="showDialog"
      :title="editingItem ? '编辑公告' : '发布公告'"
      width="560px"
      :close-on-click-modal="false"
    >
      <el-form label-position="top">
        <el-form-item label="标题（可选）">
          <el-input v-model="form.title" placeholder="输入公告标题" maxlength="100" />
        </el-form-item>
        <el-form-item label="公告内容" required>
          <el-input
            v-model="form.message"
            type="textarea"
            :rows="4"
            placeholder="输入公告内容"
            maxlength="500"
            show-word-limit
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">
          {{ editingItem ? '保存' : '发布' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue"
import { ElMessage, ElMessageBox } from "element-plus"
import { WarningFilled, Plus, Edit, Delete } from "@element-plus/icons-vue"
import { getAnnouncements, createAnnouncement, updateAnnouncement, deleteAnnouncement } from "../api/scenes"

const list = ref([])
const loading = ref(false)

const showDialog = ref(false)
const saving = ref(false)
const editingItem = ref(null)
const form = ref({ title: "", message: "" })

const isAdmin = computed(() => {
  try {
    const u = JSON.parse(localStorage.getItem("user") || "{}")
    return u.is_admin === true
  } catch {
    return false
  }
})

async function loadList() {
  loading.value = true
  try {
    const res = await getAnnouncements()
    if (res.success && res.data) {
      list.value = res.data
    }
  } catch {
    // ignore
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingItem.value = null
  form.value = { title: "", message: "" }
  showDialog.value = true
}

function openEdit(item) {
  editingItem.value = item
  form.value = { title: item.title || "", message: item.message }
  showDialog.value = true
}

async function handleSave() {
  if (!form.value.message.trim()) {
    ElMessage.warning("请输入公告内容")
    return
  }
  saving.value = true
  try {
    if (editingItem.value) {
      const res = await updateAnnouncement(editingItem.value.id, form.value.title, form.value.message)
      if (res.success) {
        ElMessage.success("公告已更新")
      }
    } else {
      const res = await createAnnouncement(form.value.title, form.value.message)
      if (res.success) {
        ElMessage.success("公告已发布")
      }
    }
    showDialog.value = false
    await loadList()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "操作失败")
  } finally {
    saving.value = false
  }
}

async function handleDelete(item) {
  try {
    await ElMessageBox.confirm(
      `确定要删除这条公告吗？`,
      "确认删除",
      { confirmButtonText: "确定删除", cancelButtonText: "取消", type: "warning" }
    )
  } catch { return }

  try {
    const res = await deleteAnnouncement(item.id)
    if (res.success) {
      ElMessage.success("公告已删除")
      await loadList()
    }
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "删除失败")
  }
}

onMounted(loadList)
</script>

<style scoped>
.announcements-page {
  width: 100%;
}

.page-header {
  margin-bottom: 32px;
}

.page-header-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.page-title {
  font-size: 28px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.page-subtitle {
  font-size: 14px;
  color: var(--text-secondary);
}

.loading-state, .empty-state {
  padding: 60px 20px;
  display: flex;
  justify-content: center;
}

.announcement-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.announcement-card {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  background: #ffffff;
  border-radius: 12px;
  padding: 20px 24px;
  border: 1px solid var(--border-color);
  transition: all 0.2s;
}

.announcement-card:hover {
  border-color: #e6a23c;
  box-shadow: 0 2px 12px rgba(230, 162, 60, 0.1);
}

.announcement-icon {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  background: #fef3e8;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #e6a23c;
  flex-shrink: 0;
}

.announcement-body {
  flex: 1;
  min-width: 0;
}

.announcement-title {
  font-size: 17px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 6px;
}

.announcement-message {
  font-size: 15px;
  color: var(--text-primary);
  line-height: 1.5;
  margin-bottom: 6px;
}

.announcement-time {
  font-size: 12px;
  color: var(--text-secondary);
}

.announcement-actions {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
  padding-top: 2px;
}
</style>
