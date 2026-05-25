# Scene Permissions and Admin Model Management — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix three issues: missing "remove" button on acquired scenes, wrong model list, and missing admin tools for public model management.

**Architecture:** Backend changes in `main.py`, `scenes.py`, `admin.py`, `custom_scene.py`; frontend changes in `SceneSelector.vue` and `scenes.js`. The key design principle: suspended != blocked (already-acquired users keep using), deleted = orphaned AcquiredScene records with gray card UI.

**Tech Stack:** FastAPI + SQLAlchemy (backend), Vue 3 + Element Plus (frontend), MinIO for model storage

---

### Task 1: Add `status` field to CustomScene model + migration

**Files:**
- Modify: `backend/app/models/custom_scene.py`
- Modify: `backend/main.py`

- [ ] **Step 1: Add status column to CustomScene model**

```python
# In backend/app/models/custom_scene.py, add after is_public:
status = Column(String(20), default="active", nullable=False)
```

Edit [custom_scene.py](backend/app/models/custom_scene.py) to add the new `status` field.

- [ ] **Step 2: Add migration for the new column**

In [main.py](backend/main.py), inside `_run_migrations()` and after the `description` migration, add:

```python
if "status" not in custom_columns:
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE custom_scenes ADD COLUMN status VARCHAR(20) DEFAULT 'active' NOT NULL"))
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/models/custom_scene.py backend/main.py
git commit -m "feat: add status field to custom_scenes model"
```

---

### Task 2: Rewrite `GET /api/models/list` to filter by user permissions

**Files:**
- Modify: `backend/main.py`

- [ ] **Step 1: Rewrite the endpoint**

Replace the entire `get_models_list` function in [main.py](backend/main.py) (lines 93-123):

```python
@app.get("/api/models/list")
async def get_models_list(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.models.custom_scene import CustomScene
    from app.models.acquired_scene import AcquiredScene

    user_id = current_user["sub"]

    # 1. Built-in models (always available)
    result = [
        {"name": "gt", "displayName": "钢铁缺陷检测"},
        {"name": "yolo11n", "displayName": "通用目标检测"},
    ]

    # 2. User's own custom scenes
    own_scenes = db.query(CustomScene).filter(
        CustomScene.user_id == user_id
    ).all()

    # 3. Acquired scenes (public models from other users)
    acquired_ids = [
        a.custom_scene_id
        for a in db.query(AcquiredScene).filter(AcquiredScene.user_id == user_id).all()
    ]
    acquired_scenes = []
    if acquired_ids:
        acquired_scenes = db.query(CustomScene).filter(
            CustomScene.id.in_(acquired_ids)
        ).all()

    for s in own_scenes + acquired_scenes:
        result.append({
            "name": s.model_filename.replace(".pt", ""),
            "displayName": s.original_model_name or s.name,
        })

    return {"success": True, "data": result}
```

Also add the `Session` import at the top of main.py:

```python
from sqlalchemy.orm import Session
```

And add `Depends` to the FastAPI import if not there.

- [ ] **Step 2: Commit**

```bash
git add backend/main.py
git commit -m "fix: filter models/list by user permissions instead of filesystem scan"
```

---

### Task 3: Backend — Filter marketplace to exclude suspended models

**Files:**
- Modify: `backend/app/api/scenes.py`

- [ ] **Step 1: Modify marketplace query**

In [scenes.py](backend/app/api/scenes.py), the `list_marketplace` function, add `CustomScene.status == "active"` filter:

```python
query = db.query(CustomScene).filter(
    CustomScene.is_public == True,
    CustomScene.status == "active",  # exclude suspended
    CustomScene.user_id != user_id,
)
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/api/scenes.py
git commit -m "fix: hide suspended models from marketplace"
```

---

### Task 4: Backend — Update `GET /api/scenes/acquired` to detect orphaned scenes

**Files:**
- Modify: `backend/app/api/scenes.py`

- [ ] **Step 1: Update the endpoint**

Replace the `list_acquired_scenes` function in [scenes.py](backend/app/api/scenes.py) to include orphaned (deleted) acquired scenes:

```python
@router.get("/acquired")
async def list_acquired_scenes(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """列出当前用户已获取的模型（供侧边栏使用），包括已被管理员删除的场景"""
    user_id = current_user["sub"]
    records = db.query(AcquiredScene).filter(
        AcquiredScene.user_id == user_id
    ).order_by(AcquiredScene.created_at.desc()).all()

    scene_ids = [r.custom_scene_id for r in records]
    scenes = db.query(CustomScene).filter(CustomScene.id.in_(scene_ids)).all() if scene_ids else []
    scene_map = {str(s.id): s for s in scenes}

    result = []
    for r in records:
        s = scene_map.get(str(r.custom_scene_id))
        if s:
            scene_key = f"custom_{s.id.hex}"
            result.append({
                "key": scene_key,
                "name": s.name,
                "originalModelName": s.original_model_name or s.name,
                "defaultModel": s.model_filename.replace(".pt", ""),
                "status": s.status,
                "deleted": False,
                "scene_id": str(s.id),
            })
        else:
            # Orphaned AcquiredScene — model was deleted by admin
            result.append({
                "key": f"orphaned_{r.id.hex}",
                "name": "（已删除的模型）",
                "originalModelName": "已删除",
                "defaultModel": "",
                "deleted": True,
                "acquired_scene_id": str(r.custom_scene_id),
            })

    return {"success": True, "data": result}
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/api/scenes.py
git commit -m "feat: report orphaned acquired scenes as deleted"
```

---

### Task 5: Backend — Add admin model management endpoints

**Files:**
- Create: none (modify existing)
- Modify: `backend/app/api/admin.py`
- Modify: `backend/app/api/scenes.py` (need to export `_custom_scene_to_dict` or inline it)

- [ ] **Step 1: Export `_custom_scene_to_dict` from scenes.py**

In [scenes.py](backend/app/api/scenes.py), `_custom_scene_to_dict` is a module-level function. It's already available for import. We'll import it in admin.py.

- [ ] **Step 2: Add admin endpoints**

Add to [admin.py](backend/app/api/admin.py):

```python
import os
import uuid as uuid_lib
from fastapi import APIRouter, Depends, HTTPException, status, Form
from sqlalchemy.orm import Session
from app.utils.db import get_db
from app.utils.auth import require_admin
from app.models.user import User
from app.models.custom_scene import CustomScene
from app.models.acquired_scene import AcquiredScene
from app.models.detection import DetectionRecord
from app.models.schemas import (
    UserListItem,
    UserListResponse,
    UserStatusRequest,
    MessageResponse,
)
from app.api.scenes import _custom_scene_to_dict
from app.config import settings
from app.utils.minio_client import delete_file as minio_delete

router = APIRouter(prefix="/admin", tags=["admin"])

# ... existing /users and /users/{user_id}/status endpoints ...


@router.get("/models")
async def admin_list_models(
    db: Session = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    """List all public models across all users (admin only)."""
    scenes = db.query(CustomScene).filter(
        CustomScene.is_public == True
    ).order_by(CustomScene.created_at.desc()).all()

    user_ids = list(set(str(s.user_id) for s in scenes))
    users = {}
    if user_ids:
        for u in db.query(User).filter(User.id.in_([uuid_lib.UUID(uid) for uid in user_ids])).all():
            users[str(u.id)] = u.username

    result = []
    for s in scenes:
        d = _custom_scene_to_dict(s)
        d["status"] = s.status
        d["creator_name"] = users.get(str(s.user_id), "未知")
        result.append(d)

    return {"success": True, "data": result}


@router.put("/models/{scene_id}/status")
async def admin_toggle_model_status(
    scene_id: str,
    status: str = Form(...),
    db: Session = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    """Toggle model status between 'active' and 'suspended'."""
    if status not in ("active", "suspended"):
        raise HTTPException(status_code=400, detail="状态值无效，仅支持 active/suspended")

    try:
        uid = uuid_lib.UUID(scene_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的场景 ID")

    scene = db.query(CustomScene).filter(CustomScene.id == uid).first()
    if not scene:
        raise HTTPException(status_code=404, detail="场景不存在")
    if not scene.is_public:
        raise HTTPException(status_code=400, detail="只能管理公开模型")

    scene.status = status
    db.commit()

    action = "已暂停" if status == "suspended" else "已恢复"
    return {"success": True, "message": f"模型已{action}"}


@router.delete("/models/{scene_id}")
async def admin_delete_model(
    scene_id: str,
    db: Session = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    """Permanently delete a public model. Keeps AcquiredScene records (orphaned)."""
    try:
        uid = uuid_lib.UUID(scene_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的场景 ID")

    scene = db.query(CustomScene).filter(CustomScene.id == uid).first()
    if not scene:
        raise HTTPException(status_code=404, detail="场景不存在")

    MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")

    # Delete .pt from local filesystem
    model_path = os.path.join(MODELS_DIR, scene.model_filename)
    if os.path.exists(model_path):
        os.remove(model_path)

    # Delete .pt from MinIO
    minio_delete(settings.MINIO_BUCKET, scene.model_filename)

    # Delete the CustomScene record (AcquiredScene records remain orphaned)
    db.delete(scene)
    db.commit()

    return {"success": True, "message": "模型已永久删除"}
```

Note: Need to add `MODELS_DIR` calculation and minio_delete import.

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/admin.py
git commit -m "feat: add admin model management endpoints (list/toggle/delete)"
```

---

### Task 6: Frontend — Add admin API functions

**Files:**
- Modify: `frontend/src/api/scenes.js`

- [ ] **Step 1: Add admin API calls**

Add to [scenes.js](frontend/src/api/scenes.js):

```javascript
// Admin model management
export const getAdminModels = () => {
  return request({
    url: "/admin/models",
    method: "get",
  });
};

export const toggleModelStatus = (sceneId, status) => {
  const formData = new FormData();
  formData.append("status", status);
  return request({
    url: `/admin/models/${sceneId}/status`,
    method: "put",
    data: formData,
  });
};

export const adminDeleteModel = (sceneId) => {
  return request({
    url: `/admin/models/${sceneId}`,
    method: "delete",
  });
};
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/api/scenes.js
git commit -m "feat: add admin model management API functions"
```

---

### Task 7: Frontend — Update SceneSelector (remove button, admin tab, gray card)

**Files:**
- Modify: `frontend/src/views/SceneSelector.vue`

This is the largest task. Changes:

1. Remove button on acquired scenes
2. Admin "管理模型" tab
3. Gray card for deleted acquired scenes

- [ ] **Step 1: Add computed property for isAdmin**

After `currentUserId` computed, add:

```javascript
const isAdmin = computed(() => {
  try {
    const u = JSON.parse(localStorage.getItem("user") || "{}")
    return u.is_admin === true
  } catch {
    return false
  }
})
```

- [ ] **Step 2: Add imports for new API functions and icons**

Update the import line:

```javascript
import { getScenes, uploadCustomScene, deleteCustomScene, getSceneGroups, createSceneGroup, renameSceneGroup, deleteSceneGroup, assignSceneGroup, getModelMarketplace, acquireModel, unacquireModel, getAcquiredModels, getAdminModels, toggleModelStatus, adminDeleteModel } from "../api/scenes"
```

Add `Remove` to the icon imports:

```javascript
import { Monitor, Picture, ArrowRight, Plus, Delete, Edit, MoreFilled, Remove } from "@element-plus/icons-vue"
```

- [ ] **Step 3: Add admin tab to the template**

After the marketplace `el-tab-pane`, add:

```html
<el-tab-pane v-if="isAdmin" label="管理模型" name="admin" />
```

- [ ] **Step 4: Add admin tab content**

After the marketplace container `</div>`, before the upload dialog, add:

```html
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
```

- [ ] **Step 5: Add admin tab state and event handlers in script**

Add state variables:

```javascript
const adminModels = ref([])
const adminLoading = ref(false)
```

Add watcher for admin tab:

```javascript
watch(activeTab, (tab) => {
  if (tab === "marketplace") {
    loadMarketplace()
  } else if (tab === "admin") {
    loadAdminModels()
  }
})
```

Add load and handler functions:

```javascript
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
```

- [ ] **Step 6: Add "移除" button on acquired scene cards**

In the template, for the scene card's badges area, after the visibility tag, add a remove button for acquired scenes:

```html
<el-button
  v-if="scene.is_custom && scene.scene_id && scene.user_id !== currentUserId"
  size="small"
  type="info"
  link
  @click.stop="confirmRemoveAcquired(scene)"
>
  <el-icon><Remove /></el-icon> 移除
</el-button>
```

- [ ] **Step 7: Add remove acquired handler**

```javascript
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
```

- [ ] **Step 8: Add gray card rendering for deleted scenes**

In the scene card template, modify the card wrapper to handle `deleted: true`:

```html
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
```

Inside the card, for deleted scenes, replace the normal content with:

```html
<!-- Deleted scene (admin removed the model) -->
<template v-if="scene.deleted">
  <div class="deleted-overlay">
    <el-icon :size="32" style="color:#999"><WarningFilled /></el-icon>
    <p class="deleted-text">该模型已被管理员删除</p>
    <el-button size="small" type="danger" plain @click.stop="confirmRemoveDeletedAcquired(scene)">
      删除
    </el-button>
  </div>
</template>
<template v-else>
  <!-- existing card content -->
</template>
```

Add `WarningFilled` to icon imports.

And add the handler:

```javascript
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
```

Wait — the `unacquireModel` expects a `scene_id` which is the `custom_scene_id` in AcquiredScene. But in the orphaned case, the CustomScene has been deleted. So we can't use the existing `DELETE /api/scenes/acquire/{scene_id}` endpoint since it looks up by `custom_scene_id = uid`.

I need a different approach. Let me check the existing endpoint:

```python
@router.delete("/acquire/{scene_id}")
async def unacquire_scene(
    scene_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    import uuid as uuid_lib
    try:
        uid = uuid_lib.UUID(scene_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的场景 ID")

    record = db.query(AcquiredScene).filter(
        AcquiredScene.user_id == current_user["sub"],
        AcquiredScene.custom_scene_id == uid,
    ).first()
```

It queries by `custom_scene_id`. If the CustomScene is deleted, we can still find the AcquiredScene since AcquiredScene still has the `custom_scene_id`. So this should work even if the CustomScene is deleted! The DB still has the FK value.

So I can pass the `acquired_scene_id` (which is the `custom_scene_id` from the orphaned record) to `unacquireModel`. That's fine.

Actually wait, looking at the data format from the spec:
```python
result.append({
    "key": f"orphaned_{r.id.hex}",
    "name": "（已删除的模型）",
    "originalModelName": "已删除",
    "defaultModel": "",
    "deleted": True,
    "acquired_scene_id": str(r.custom_scene_id),
})
```

I set `acquired_scene_id` to `str(r.custom_scene_id)`. So calling `unacquireModel(scene.acquired_scene_id)` will hit `DELETE /api/scenes/acquire/{acquired_scene_id}` which queries `AcquiredScene.custom_scene_id == uid`. This should work even if the CustomScene record is gone.

OK that's fine. Let me also fix the import — need to add `WarningFilled` icon.

- [ ] **Step 9: Add pending-delete confirmation for owner's scene delete**

Actually, the existing delete logic for the scene owner is fine. No changes needed there.

- [ ] **Step 10: Add CSS for deleted card and admin suspended card**

Add to the `<style>` section:

```css
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
```

- [ ] **Step 11: Commit**

```bash
git add frontend/src/views/SceneSelector.vue
git commit -m "feat: add remove button, admin model tab, and deleted scene gray card"
```

---

### Task 8: Rebuild frontend and restart backend

**Files:** None (build step)

- [ ] **Step 1: Rebuild frontend**

```bash
wsl -d Ubuntu bash -c "export PATH=\"/home/cwl/.nvm/versions/node/v24.15.0/bin:\$PATH\" && cd /home/cwl/yaogan/frontend && npm run build"
```

- [ ] **Step 2: Restart backend**

```bash
wsl -d Ubuntu -- bash -c "fuser -k 8000/tcp 2>/dev/null; sleep 1; cd /home/cwl/yaogan/backend && .venv/bin/python3 main.py &>/tmp/yaogan.log & sleep 8"
```

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "chore: rebuild frontend dist after scene management changes"
```
