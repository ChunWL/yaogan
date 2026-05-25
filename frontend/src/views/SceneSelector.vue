<template>
  <div class="scene-selector">
    <div class="page-header">
      <div class="breadcrumb">
        <span>工作台</span>
        <span class="separator">›</span>
        <span class="active">更多功能</span>
      </div>
      <h1 class="page-title">选择检测场景</h1>
      <p class="page-subtitle">选择不同的检测场景，系统将自动切换对应的检测模型</p>
    </div>

    <!-- Tab 切换 -->
    <el-tabs v-model="activeTab" class="scene-tabs">
      <el-tab-pane label="我的场景" name="mine" />
      <el-tab-pane label="获取模型" name="marketplace" />
      <el-tab-pane v-if="isAdmin" label="管理模型" name="admin" />
    </el-tabs>

    <div v-if="activeTab === 'mine'" class="scene-layout">
      <!-- 左侧分组栏 -->
      <div class="group-sidebar">
        <div class="group-sidebar-header">
          <span class="group-sidebar-title">场景分组</span>
        </div>
        <div class="group-list">
          <div
            class="group-item"
            :class="{ active: selectedGroupId === null }"
            @click="selectedGroupId = null"
          >
            <span>全部场景</span>
            <el-tag size="small" round>{{ allScenes.length }}</el-tag>
          </div>
          <div
            class="group-item"
            :class="{ active: selectedGroupId === '__ungrouped' }"
            @click="selectedGroupId = '__ungrouped'"
          >
            <span>未分组</span>
            <el-tag size="small" round>{{ ungroupedCount }}</el-tag>
          </div>
          <el-divider style="margin: 4px 0" />
          <div
            v-for="group in groups"
            :key="group.id"
            class="group-item"
            :class="{ active: selectedGroupId === group.id }"
            @click="selectedGroupId = group.id"
          >
            <span class="group-name">{{ group.name }}</span>
            <div style="display:flex;align-items:center;gap:4px">
              <el-tag size="small" round>{{ group.scene_count }}</el-tag>
              <el-dropdown trigger="click" @command="(cmd) => handleGroupAction(cmd, group)">
                <el-button size="small" link>
                  <el-icon><MoreFilled /></el-icon>
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="rename">重命名</el-dropdown-item>
                    <el-dropdown-item command="delete" divided>删除分组</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </div>
        </div>
        <div class="group-sidebar-footer">
          <el-button text size="small" @click="showCreateGroup = true">
            <el-icon><Plus /></el-icon> 新建分组
          </el-button>
        </div>
      </div>

      <!-- 右侧场景卡片区域 -->
      <div class="scene-grid-container">
        <div class="section-header">
          <span class="section-title">{{ selectedGroupName }}</span>
        </div>

        <div class="scene-grid">
          <div
            v-for="scene in filteredScenes"
            :key="scene.key"
            class="scene-card"
            :class="{
              'custom-scene': scene.is_custom,
              'deleted-scene': scene.deleted
            }"
            @click="!scene.deleted && goToScene(scene)"
          >
            <template v-if="!scene.deleted">
            <div class="scene-icon-wrapper">
              <el-icon :size="32"><component :is="sceneIconMap[scene.icon] || sceneIconMap.Monitor" /></el-icon>
            </div>
            <div class="scene-info">
              <div class="scene-name-row">
                <h3 class="scene-name">{{ scene.name }}</h3>
                <div class="scene-badges">
                  <el-tag v-if="!scene.is_custom" size="small" type="primary" effect="plain">内置</el-tag>
                  <el-tag v-if="scene.is_custom" size="small" type="warning" effect="dark" class="custom-badge">自定义</el-tag>
                  <el-tag v-if="scene.is_custom && scene.is_public" size="small" type="success" effect="plain">公开</el-tag>
                  <el-tag v-if="scene.is_custom && !scene.is_public" size="small" type="info" effect="plain">私有</el-tag>
                  <el-button
                    v-if="scene.is_custom && scene.scene_id && scene.user_id === currentUserId"
                    size="small"
                    type="danger"
                    link
                    @click.stop="confirmDelete(scene)"
                  >
                    <el-icon><Delete /></el-icon>
                  </el-button>
                  <el-button
                    v-if="scene.is_custom && scene.scene_id && scene.user_id !== currentUserId"
                    size="small"
                    type="info"
                    link
                    @click.stop="confirmRemoveAcquired(scene)"
                  >
                    <el-icon><Remove /></el-icon> 移除
                  </el-button>
                </div>
              </div>
              <p class="scene-desc">{{ scene.description }}</p>
            </div>
            <div class="scene-footer">
              <el-tag size="small" type="info" effect="plain">
                模型: {{ scene.is_custom ? (scene.originalModelName || scene.defaultModel) : scene.defaultModel }}
              </el-tag>
              <div class="scene-footer-right">
                <el-select
                  v-if="scene.is_custom"
                  size="small"
                  :model-value="scene.group_id"
                  placeholder="分组"
                  style="width: 110px"
                  @click.stop
                  @change="(val) => handleSceneGroupChange(scene, val)"
                >
                  <el-option label="未分组" :value="null" />
                  <el-option v-for="g in groups" :key="g.id" :label="g.name" :value="g.id" />
                </el-select>
              </div>
            </div>
            </template>
            <template v-else>
              <div class="deleted-overlay">
                <el-icon :size="32" style="color:#999"><WarningFilled /></el-icon>
                <p class="deleted-text">该模型已被管理员删除</p>
                <el-button size="small" type="danger" plain @click.stop="confirmRemoveDeletedAcquired(scene)">
                  删除
                </el-button>
              </div>
            </template>
          </div>

          <!-- 上传模型卡片 -->
          <div class="scene-card upload-card" @click="showUploadDialog = true">
            <div class="scene-icon-wrapper upload-icon">
              <el-icon :size="32"><Plus /></el-icon>
            </div>
            <div class="scene-info">
              <h3 class="scene-name">上传模型</h3>
              <p class="scene-desc">上传自定义 .pt 模型创建新的检测场景</p>
            </div>
            <div class="scene-footer">
              <el-tag size="small" type="success" effect="plain">点击上传</el-tag>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 获取模型 Tab -->
    <div v-if="activeTab === 'marketplace'" class="marketplace-container">
      <div v-if="marketplaceLoading" class="loading-state">
        <el-skeleton :rows="3" animated />
      </div>
      <div v-else-if="marketplaceList.length === 0" class="empty-state">
        <el-empty description="暂无更多公开模型" />
      </div>
      <div v-else class="marketplace-grid">
        <div
          v-for="item in marketplaceList"
          :key="item.key"
          class="marketplace-card"
        >
          <div class="marketplace-card-header">
            <div class="marketplace-icon">
              <el-icon :size="28"><Monitor /></el-icon>
            </div>
            <div>
              <h3 class="marketplace-name">{{ item.name }}</h3>
              <span class="marketplace-creator">上传者: {{ item.creator_name || '未知用户' }}</span>
            </div>
          </div>
          <p class="marketplace-desc">{{ item.description || '暂无描述' }}</p>
          <div class="marketplace-footer">
            <el-tag size="small" type="warning">公开</el-tag>
            <el-button
              type="primary"
              size="small"
              plain
              :loading="item._acquiring"
              @click="handleAcquire(item)"
            >
              获取模型
            </el-button>
          </div>
        </div>
      </div>
    </div>

    <!-- 管理员管理模型 Tab -->
    <div v-if="activeTab === 'admin'" class="marketplace-container">
      <div v-if="adminLoading" class="loading-state">
        <el-skeleton :rows="3" animated />
      </div>
      <div v-else-if="adminModels.length === 0" class="empty-state">
        <el-empty description="暂无公开模型" />
      </div>
      <div v-else class="marketplace-grid">
        <div
          v-for="item in adminModels"
          :key="item.key"
          class="marketplace-card"
          :class="{ 'suspended-card': item.status === 'suspended' }"
        >
          <div class="marketplace-card-header">
            <div class="marketplace-icon">
              <el-icon :size="28"><Monitor /></el-icon>
            </div>
            <div>
              <h3 class="marketplace-name">{{ item.name }}</h3>
              <span class="marketplace-creator">上传者: {{ item.creator_name || '未知' }}</span>
            </div>
          </div>
          <p class="marketplace-desc">{{ item.description || '暂无描述' }}</p>
          <div class="marketplace-footer">
            <el-tag v-if="item.status === 'active'" size="small" type="success">正常</el-tag>
            <el-tag v-else size="small" type="warning">已暂停</el-tag>
            <div style="display:flex;gap:8px">
              <el-button
                size="small"
                :type="item.status === 'active' ? 'warning' : 'success'"
                plain
                :loading="item._toggling"
                @click="handleToggleStatus(item)"
              >
                {{ item.status === 'active' ? '暂停' : '恢复' }}
              </el-button>
              <el-button
                size="small"
                type="danger"
                plain
                :loading="item._deleting"
                @click="handleAdminDelete(item)"
              >
                删除
              </el-button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 上传对话框 -->
    <el-dialog v-model="showUploadDialog" title="上传自定义模型" width="500px" :close-on-click-modal="false">
      <el-form :model="uploadForm" label-width="100px">
        <el-form-item label="场景名称" required>
          <el-input v-model="uploadForm.name" placeholder="输入场景名称" maxlength="50" />
        </el-form-item>
        <el-form-item label="模型文件" required>
          <el-upload
            ref="uploadRef"
            :auto-upload="false"
            :limit="1"
            accept=".pt"
            :on-change="handleFileChange"
            :file-list="uploadForm.fileList"
          >
            <el-button type="primary" plain>选择 .pt 文件</el-button>
            <template #tip>
              <span class="upload-tip">仅支持 YOLO 格式的 .pt 模型文件</span>
            </template>
          </el-upload>
        </el-form-item>
        <el-form-item label="简介描述">
          <el-input
            v-model="uploadForm.description"
            type="textarea"
            :rows="3"
            placeholder="简要描述模型的检测能力（公开时其他用户将看到此描述）"
            maxlength="500"
            show-word-limit
          />
        </el-form-item>
        <el-form-item label="公开场景">
          <el-switch
            v-model="uploadForm.isPublic"
            active-text="公开（所有人可见）"
            inactive-text="私有（仅自己可见）"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showUploadDialog = false">取消</el-button>
        <el-button type="primary" :loading="uploading" @click="handleUpload">
          {{ uploading ? "上传中..." : "开始上传" }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 新建分组对话框 -->
    <el-dialog v-model="showCreateGroup" title="新建分组" width="360px">
      <el-form @submit.prevent="handleCreateGroup">
        <el-form-item label="分组名称">
          <el-input v-model="newGroupName" placeholder="输入分组名称" maxlength="50" @keyup.enter="handleCreateGroup" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateGroup = false">取消</el-button>
        <el-button type="primary" @click="handleCreateGroup">创建</el-button>
      </template>
    </el-dialog>

    <!-- 重命名分组对话框 -->
    <el-dialog v-model="showRenameGroup" title="重命名分组" width="360px">
      <el-form @submit.prevent="handleRenameGroup">
        <el-form-item label="分组名称">
          <el-input v-model="newGroupName" placeholder="输入新名称" maxlength="50" @keyup.enter="handleRenameGroup" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showRenameGroup = false">取消</el-button>
        <el-button type="primary" @click="handleRenameGroup">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from "vue"
import { useRouter } from "vue-router"
import { ElMessage, ElMessageBox } from "element-plus"
import { Monitor, Picture, ArrowRight, Plus, Delete, Edit, MoreFilled, Remove, WarningFilled } from "@element-plus/icons-vue"
import { getSceneList, buildCustomSceneConfig, getSceneConfig, registerCustomScenes } from "../config/scenes"
import { getScenes, uploadCustomScene, deleteCustomScene, getSceneGroups, createSceneGroup, renameSceneGroup, deleteSceneGroup, assignSceneGroup, getModelMarketplace, acquireModel, unacquireModel, getAdminModels, toggleModelStatus, adminDeleteModel } from "../api/scenes"

const router = useRouter()

const customSceneList = ref([])
const groups = ref([])
const selectedGroupId = ref(null) // null = all, '__ungrouped' = ungrouped
const showCreateGroup = ref(false)
const showRenameGroup = ref(false)
const renameTarget = ref(null)
const newGroupName = ref("")

const activeTab = ref("mine")
const marketplaceList = ref([])
const marketplaceLoading = ref(false)
const adminModels = ref([])
const adminLoading = ref(false)

async function loadMarketplace() {
  marketplaceLoading.value = true
  try {
    const res = await getModelMarketplace()
    if (res.success && res.data) {
      marketplaceList.value = res.data.map(item => ({ ...item, _acquiring: false }))
    }
  } catch {
    // ignore
  } finally {
    marketplaceLoading.value = false
  }
}

async function handleAcquire(item) {
  item._acquiring = true
  try {
    const res = await acquireModel(item.scene_id)
    if (res.success) {
      ElMessage.success("模型获取成功")
      marketplaceList.value = marketplaceList.value.filter(i => i.key !== item.key)
    }
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "获取失败")
  } finally {
    item._acquiring = false
  }
}

async function loadAdminModels() {
  adminLoading.value = true
  try {
    const res = await getAdminModels()
    if (res.success && res.data) {
      adminModels.value = res.data.map(item => ({ ...item, _toggling: false, _deleting: false }))
    }
  } catch {
    // ignore
  } finally {
    adminLoading.value = false
  }
}

async function handleToggleStatus(item) {
  item._toggling = true
  try {
    const newStatus = item.status === 'active' ? 'suspended' : 'active'
    const res = await toggleModelStatus(item.scene_id, newStatus)
    if (res.success) {
      ElMessage.success(res.message || '操作成功')
      item.status = newStatus
    }
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  } finally {
    item._toggling = false
  }
}

async function handleAdminDelete(item) {
  try {
    await ElMessageBox.confirm(
      `确定要永久删除模型 "${item.name}" 吗？<br><br>
       <strong style="color:#dc2626">此操作将：</strong><br>
       • 从 MinIO 和服务器删除模型文件<br>
       • 删除该模型的自定义场景记录<br>
       • 已获取该模型的用户将看到灰卡提示<br><br>
       此操作不可撤销。`,
      "确认删除模型",
      { confirmButtonText: "确定删除", cancelButtonText: "取消", type: "danger", dangerouslyUseHTMLString: true }
    )
  } catch { return }

  item._deleting = true
  try {
    const res = await adminDeleteModel(item.scene_id)
    if (res.success) {
      ElMessage.success("模型已永久删除")
      adminModels.value = adminModels.value.filter(i => i.key !== item.key)
    }
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '删除失败')
  } finally {
    item._deleting = false
  }
}

async function confirmRemoveAcquired(scene) {
  try {
    await ElMessageBox.confirm(
      `确定要从场景列表中移除 "${scene.name}" 吗？`,
      "确认移除",
      { confirmButtonText: "确定移除", cancelButtonText: "取消", type: "info" }
    )
  } catch { return }

  try {
    const res = await unacquireModel(scene.scene_id)
    if (res.success) {
      ElMessage.success("已移除")
      await loadCustomScenes()
      await loadGroups()
    }
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "移除失败")
  }
}

async function confirmRemoveDeletedAcquired(scene) {
  try {
    await ElMessageBox.confirm(
      `确定要删除此条已失效的场景记录吗？`,
      "确认删除",
      { confirmButtonText: "确定", cancelButtonText: "取消", type: "info" }
    )
  } catch { return }

  try {
    const res = await unacquireModel(scene.acquired_scene_id)
    if (res.success) {
      ElMessage.success("已删除")
      await loadCustomScenes()
      await loadGroups()
    }
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "删除失败")
  }
}

watch(activeTab, (tab) => {
  if (tab === "marketplace") {
    loadMarketplace()
  } else if (tab === "admin") {
    loadAdminModels()
  }
})

const sceneIconMap = {
  Monitor,
  Picture,
}

const currentUserId = computed(() => {
  try {
    const u = JSON.parse(localStorage.getItem("user") || "{}")
    return u.sub || u.id || ""
  } catch {
    return ""
  }
})

const isAdmin = computed(() => {
  try {
    const u = JSON.parse(localStorage.getItem("user") || "{}")
    return u.is_admin === true
  } catch {
    return false
  }
})

const allScenes = computed(() => getSceneList(customSceneList.value))

const filteredScenes = computed(() => {
  if (selectedGroupId.value === null) return allScenes.value
  if (selectedGroupId.value === '__ungrouped') {
    return allScenes.value.filter(s => !s.group_id)
  }
  return allScenes.value.filter(s => s.group_id === selectedGroupId.value)
})

const ungroupedCount = computed(() => {
  return allScenes.value.filter(s => !s.group_id).length
})

const selectedGroupName = computed(() => {
  if (selectedGroupId.value === null) return "全部场景"
  if (selectedGroupId.value === "__ungrouped") return "未分组场景"
  const g = groups.value.find(g => g.id === selectedGroupId.value)
  return g ? g.name : "全部场景"
})

// Group management
async function loadGroups() {
  try {
    const res = await getSceneGroups()
    if (res.success) groups.value = res.data
  } catch { /* silent */ }
}

async function handleCreateGroup() {
  if (!newGroupName.value.trim()) {
    ElMessage.warning("请输入分组名称")
    return
  }
  try {
    const res = await createSceneGroup(newGroupName.value.trim())
    if (res.success) {
      ElMessage.success("分组创建成功")
      newGroupName.value = ""
      showCreateGroup.value = false
      await loadGroups()
    }
  } catch { ElMessage.error("创建失败") }
}

function promptRenameGroup(group) {
  renameTarget.value = group
  newGroupName.value = group.name
  showRenameGroup.value = true
}

async function handleRenameGroup() {
  if (!newGroupName.value.trim()) return
  try {
    const res = await renameSceneGroup(renameTarget.value.id, newGroupName.value.trim())
    if (res.success) {
      ElMessage.success("重命名成功")
      showRenameGroup.value = false
      renameTarget.value = null
      newGroupName.value = ""
      await loadGroups()
    }
  } catch { ElMessage.error("重命名失败") }
}

async function confirmDeleteGroup(group) {
  try {
    await ElMessageBox.confirm(
      `确定要删除分组 "${group.name}" 吗？分组内的场景将变为未分组状态。`,
      "确认删除",
      { confirmButtonText: "确定", cancelButtonText: "取消", type: "warning" }
    )
  } catch { return }
  try {
    const res = await deleteSceneGroup(group.id)
    if (res.success) {
      ElMessage.success("分组已删除")
      if (selectedGroupId.value === group.id) selectedGroupId.value = null
      await loadGroups()
      await loadCustomScenes()
    }
  } catch { ElMessage.error("删除失败") }
}

async function handleSceneGroupChange(scene, groupId) {
  try {
    await assignSceneGroup(scene.key, groupId || null)
    await loadCustomScenes()
    await loadGroups()
  } catch { ElMessage.error("分配分组失败") }
}

function handleGroupAction(cmd, group) {
  if (cmd === "rename") promptRenameGroup(group)
  else if (cmd === "delete") confirmDeleteGroup(group)
}

// Upload dialog
const showUploadDialog = ref(false)
const uploadRef = ref(null)
const uploading = ref(false)
const uploadForm = ref({
  name: "",
  description: "",
  isPublic: false,
  fileList: [],
  file: null,
})

function handleFileChange(file) {
  uploadForm.value.file = file.raw
}

async function handleUpload() {
  if (!uploadForm.value.name.trim()) {
    ElMessage.warning("请输入场景名称")
    return
  }
  if (!uploadForm.value.file) {
    ElMessage.warning("请选择 .pt 模型文件")
    return
  }

  uploading.value = true
  try {
    const formData = new FormData()
    formData.append("file", uploadForm.value.file)
    formData.append("name", uploadForm.value.name.trim())
    formData.append("is_public", uploadForm.value.isPublic ? "true" : "false")
    formData.append("description", uploadForm.value.description.trim())

    const res = await uploadCustomScene(formData)
    if (res.success) {
      ElMessage.success("场景创建成功！")
      showUploadDialog.value = false
      uploadForm.value = { name: "", description: "", isPublic: false, fileList: [], file: null }
      await loadCustomScenes()
    } else {
      ElMessage.error(res.message || "上传失败")
    }
  } catch (e) {
    ElMessage.error("上传失败: " + (e.message || "未知错误"))
  } finally {
    uploading.value = false
  }
}

async function loadCustomScenes() {
  try {
    const res = await getScenes()
    if (res.success && res.data) {
      const configs = res.data
        .filter((s) => s.is_custom)
        .map(buildCustomSceneConfig)
      customSceneList.value = configs
      registerCustomScenes(configs)
    }
  } catch { /* silent */ }
}

async function confirmDelete(scene) {
  try {
    await ElMessageBox.confirm(
      `确定要删除场景 "${scene.name}" 吗？<br><br>
       <strong style="color:#dc2626">此操作将同时删除：</strong><br>
       • 该场景的模型文件<br>
       • 该场景的所有检测历史记录<br><br>
       此操作不可撤销。`,
      "确认删除场景",
      { confirmButtonText: "确定删除", cancelButtonText: "取消", type: "warning", dangerouslyUseHTMLString: true }
    )
  } catch { return }
  try {
    const res = await deleteCustomScene(scene.scene_id)
    if (res.success) {
      ElMessage.success(res.message || "删除成功")
      await loadCustomScenes()
      await loadGroups()
    }
  } catch {
    ElMessage.error("删除失败")
  }
}

function goToScene(scene) {
  localStorage.setItem("scene", scene.key)
  router.push({ path: "/detection", query: { scene: scene.key } })
}

onMounted(() => {
  loadCustomScenes()
  loadGroups()
})
</script>

<style scoped>
.scene-selector {
  width: 100%;
}

.page-header {
  margin-bottom: 32px;
}

.breadcrumb {
  font-size: 14px;
  color: var(--text-secondary);
  margin-bottom: 12px;
}

.separator {
  margin: 0 6px;
}

.active {
  color: var(--text-primary);
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

.scene-layout {
  display: flex;
  gap: 24px;
  align-items: flex-start;
}

.group-sidebar {
  width: 220px;
  min-width: 220px;
  background: #fff;
  border-radius: 12px;
  padding: 16px;
  border: 1px solid var(--border-color);
  position: sticky;
  top: 0;
}

.group-sidebar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border-color);
}

.group-sidebar-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.group-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.group-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 10px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 13px;
  color: var(--text-primary);
  transition: all 0.15s;
}

.group-item:hover {
  background: var(--primary-light);
}

.group-item.active {
  background: var(--primary-light);
  color: var(--primary-color);
  font-weight: 500;
}

.group-sidebar-footer {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--border-color);
}

.scene-grid-container {
  flex: 1;
  min-width: 0;
}

.section-header {
  margin-bottom: 16px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.scene-name-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.scene-badges {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}

.group-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100px;
}

.scene-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 20px;
}

.scene-card {
  background: #ffffff;
  border-radius: 12px;
  padding: 24px;
  cursor: pointer;
  transition: all 0.25s;
  border: 2px solid transparent;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.scene-card:hover {
  border-color: var(--primary-color);
  box-shadow: 0 4px 20px rgba(26, 86, 219, 0.12);
  transform: translateY(-2px);
}

.scene-card.custom-scene {
  border-color: #f0ad4e40;
}

.scene-card.custom-scene:hover {
  border-color: #f0ad4e;
}

.upload-card {
  border: 2px dashed #d9d9d9;
  cursor: pointer;
}

.upload-card:hover {
  border-color: var(--primary-color);
  background-color: #f0f5ff;
}

.scene-icon-wrapper {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  background: var(--primary-light);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--primary-color);
}

.upload-icon {
  background: #f0f5ff;
  color: var(--primary-color);
}

.scene-info h3 {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 6px;
}

.scene-info p {
  font-size: 14px;
  color: var(--text-secondary);
  line-height: 1.5;
}

.scene-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 12px;
  border-top: 1px solid var(--border-color);
}

.scene-footer-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.custom-badge {
  font-size: 11px;
}

.upload-tip {
  font-size: 12px;
  color: var(--text-secondary);
}

.scene-tabs {
  margin-bottom: 20px;
}

.marketplace-container {
  min-height: 300px;
}

.loading-state {
  padding: 60px 20px;
}

.empty-state {
  padding: 60px 20px;
  display: flex;
  justify-content: center;
}

.marketplace-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 20px;
}

.marketplace-card {
  background: #ffffff;
  border-radius: 12px;
  padding: 24px;
  border: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  gap: 16px;
  transition: all 0.25s;
}

.marketplace-card:hover {
  border-color: var(--primary-color);
  box-shadow: 0 4px 20px rgba(26, 86, 219, 0.12);
  transform: translateY(-2px);
}

.marketplace-card-header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.marketplace-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  background: var(--primary-light);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--primary-color);
  flex-shrink: 0;
}

.marketplace-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 2px;
}

.marketplace-creator {
  font-size: 12px;
  color: var(--text-secondary);
}

.marketplace-desc {
  font-size: 14px;
  color: var(--text-secondary);
  line-height: 1.6;
  margin: 0;
  flex: 1;
}

.marketplace-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 12px;
  border-top: 1px solid var(--border-color);
}

.deleted-scene {
  opacity: 0.5;
  cursor: default;
  border-color: #ddd;
  background: #f9f9f9;
}

.deleted-scene:hover {
  transform: none;
  box-shadow: none;
  border-color: #ddd;
}

.deleted-overlay {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 24px;
  text-align: center;
}

.deleted-text {
  color: #999;
  font-size: 14px;
  margin: 0;
}

.suspended-card {
  border-color: #e6a23c40;
}

.suspended-card:hover {
  border-color: #e6a23c;
}
</style>
