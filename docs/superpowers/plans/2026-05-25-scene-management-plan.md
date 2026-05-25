# Scene Management Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add scene grouping, public/private visibility display, and cascade delete to the SceneSelector page.

**Architecture:** New DB table `scene_groups` + mapping table for built-in scene grouping. Frontend SceneSelector gets a left sidebar for group filter and management. Delete is extended to cascade to detection history.

**Tech Stack:** FastAPI + SQLAlchemy + PostgreSQL on backend, Vue 3 + Element Plus on frontend.

---

### Task 1: SceneGroup Model

**Files:**
- Create: `backend/app/models/scene_group.py`
- Modify: `backend/app/models/custom_scene.py`

- [ ] **Step 1: Create SceneGroup model**

Write to `backend/app/models/scene_group.py`:

```python
import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.utils.db import Base
from datetime import datetime


def china_now():
    return datetime.utcnow()


class SceneGroup(Base):
    __tablename__ = "scene_groups"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=china_now)
```

- [ ] **Step 2: Add group_id to CustomScene model**

Modify `backend/app/models/custom_scene.py`: add `group_id` column after `original_model_name`:

```python
    original_model_name = Column(String(255), nullable=True)
    group_id = Column(UUID(as_uuid=True), ForeignKey("scene_groups.id"), nullable=True, index=True)
    class_names = Column(JSON, nullable=False, default=dict)
```

---

### Task 2: User Scene Group Mapping Model

**Files:**
- Create: `backend/app/models/user_scene_group_mapping.py`

- [ ] **Step 1: Create the mapping model**

Write to `backend/app/models/user_scene_group_mapping.py`:

```python
import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from app.utils.db import Base
from datetime import datetime


def china_now():
    return datetime.utcnow()


class UserSceneGroupMapping(Base):
    __tablename__ = "user_scene_group_mappings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    scene_key = Column(String(100), nullable=False)
    group_id = Column(UUID(as_uuid=True), ForeignKey("scene_groups.id"), nullable=False)
    created_at = Column(DateTime, default=china_now)

    __table_args__ = (UniqueConstraint("user_id", "scene_key", name="uq_user_scene_group"),)
```

---

### Task 3: Migration for New Tables/Columns

**Files:**
- Modify: `backend/main.py`

- [ ] **Step 1: Update migrations in main.py**

Modify `backend/main.py` `_run_migrations()` to add the new columns to `custom_scenes` table (if not already added from previous fix) and `scene_groups`/`user_scene_group_mappings` are handled by `Base.metadata.create_all()` since they're new tables.

Replace existing migration block with:

```python
def _run_migrations():
    """Add new columns to existing tables without dropping data."""
    inspector = inspect(engine)
    table_names = inspector.get_table_names()

    # detection_records: scene column
    if "detection_records" in table_names:
        detection_columns = [c["name"] for c in inspector.get_columns("detection_records")]
        if "scene" not in detection_columns:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE detection_records ADD COLUMN scene VARCHAR(50) DEFAULT 'steel'"))
                conn.execute(text("CREATE INDEX ix_detection_records_scene ON detection_records (scene)"))

    # custom_scenes: original_model_name + group_id
    if "custom_scenes" in table_names:
        custom_columns = [c["name"] for c in inspector.get_columns("custom_scenes")]
        if "original_model_name" not in custom_columns:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE custom_scenes ADD COLUMN original_model_name VARCHAR(255)"))
        if "group_id" not in custom_columns:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE custom_scenes ADD COLUMN group_id UUID REFERENCES scene_groups(id)"))
                conn.execute(text("CREATE INDEX ix_custom_scenes_group_id ON custom_scenes (group_id)"))
```

---

### Task 4: Backend Group CRUD + Group Assignment Endpoints

**Files:**
- Modify: `backend/app/api/scenes.py`

- [ ] **Step 1: Add group CRUD endpoints**

Add these endpoints to `backend/app/api/scenes.py`:

```python
@router.get("/groups")
async def list_groups(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_id = current_user["sub"]
    from app.models.scene_group import SceneGroup
    groups = db.query(SceneGroup).filter(SceneGroup.user_id == user_id).all()
    # Count scenes per group
    from app.models.custom_scene import CustomScene
    result = []
    for g in groups:
        scene_count = db.query(CustomScene).filter(CustomScene.group_id == g.id).count()
        # Also count scene mappings for built-in scenes
        from app.models.user_scene_group_mapping import UserSceneGroupMapping
        mapping_count = db.query(UserSceneGroupMapping).filter(
            UserSceneGroupMapping.group_id == g.id
        ).count()
        result.append({
            "id": str(g.id),
            "name": g.name,
            "scene_count": scene_count + mapping_count,
        })
    return {"success": True, "data": result}


@router.post("/groups")
async def create_group(
    name: str = Form(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.models.scene_group import SceneGroup
    record = SceneGroup(user_id=current_user["sub"], name=name)
    db.add(record)
    db.commit()
    db.refresh(record)
    return {
        "success": True,
        "data": {"id": str(record.id), "name": record.name, "scene_count": 0},
    }


@router.put("/groups/{group_id}")
async def rename_group(
    group_id: str,
    name: str = Form(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.models.scene_group import SceneGroup
    import uuid as uuid_lib
    try:
        uid = uuid_lib.UUID(group_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的分组 ID")
    record = db.query(SceneGroup).filter(SceneGroup.id == uid, SceneGroup.user_id == current_user["sub"]).first()
    if not record:
        raise HTTPException(status_code=404, detail="分组不存在")
    record.name = name
    db.commit()
    return {"success": True, "data": {"id": str(record.id), "name": record.name}}


@router.delete("/groups/{group_id}")
async def delete_group(
    group_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.models.scene_group import SceneGroup
    from app.models.custom_scene import CustomScene
    from app.models.user_scene_group_mapping import UserSceneGroupMapping
    import uuid as uuid_lib
    try:
        uid = uuid_lib.UUID(group_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的分组 ID")
    record = db.query(SceneGroup).filter(SceneGroup.id == uid, SceneGroup.user_id == current_user["sub"]).first()
    if not record:
        raise HTTPException(status_code=404, detail="分组不存在")

    # Reassign custom scenes to default (NULL)
    db.query(CustomScene).filter(CustomScene.group_id == uid).update({"group_id": None})
    # Remove mappings
    db.query(UserSceneGroupMapping).filter(UserSceneGroupMapping.group_id == uid).delete()
    # Delete group
    db.delete(record)
    db.commit()
    return {"success": True}
```

- [ ] **Step 2: Add scene group assignment endpoint**

```python
@router.put("/{scene_key}/group")
async def assign_scene_group(
    scene_key: str,
    group_id: str = Form(None),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_id = current_user["sub"]
    import uuid as uuid_lib

    if group_id:
        try:
            uid = uuid_lib.UUID(group_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="无效的分组 ID")

    # Check if scene is custom (has DB record) or built-in
    if scene_key.startswith("custom_"):
        # Custom scene: update group_id directly
        record = db.query(CustomScene).filter(CustomScene.id.hex == scene_key.replace("custom_", "")).first()
        if not record:
            raise HTTPException(status_code=404, detail="场景不存在")
        record.group_id = uid if group_id else None
        db.commit()
    else:
        # Built-in scene: use mapping table
        from app.models.user_scene_group_mapping import UserSceneGroupMapping
        existing = db.query(UserSceneGroupMapping).filter(
            UserSceneGroupMapping.user_id == user_id,
            UserSceneGroupMapping.scene_key == scene_key,
        ).first()
        if group_id:
            if existing:
                existing.group_id = uid
            else:
                mapping = UserSceneGroupMapping(user_id=user_id, scene_key=scene_key, group_id=uid)
                db.add(mapping)
        else:
            if existing:
                db.delete(existing)
        db.commit()

    return {"success": True}
```

- [ ] **Step 3: Extend `_custom_scene_to_dict` to include group_id**

Modify `_custom_scene_to_dict` to include group information:

```python
def _custom_scene_to_dict(scene: CustomScene) -> dict:
    group_info = {}
    if scene.group_id:
        group_info["group_id"] = str(scene.group_id)
        from app.models.scene_group import SceneGroup
        group = db.query(SceneGroup).filter(SceneGroup.id == scene.group_id).first()
        group_info["group_name"] = group.name if group else None
    else:
        group_info["group_id"] = None
        group_info["group_name"] = None

    return {
        "key": f"custom_{scene.id.hex}",
        "name": scene.name,
        "description": f"自定义场景: {scene.name}",
        "defaultModel": scene.model_filename.replace(".pt", ""),
        "originalModelName": scene.original_model_name or scene.model_filename.replace(".pt", ""),
        "icon": "Monitor",
        "classNames": scene.class_names if isinstance(scene.class_names, dict) else json.loads(scene.class_names),
        "is_public": scene.is_public,
        "is_custom": True,
        "scene_id": str(scene.id),
        "user_id": str(scene.user_id),
        **group_info,
    }
```

Wait - `_custom_scene_to_dict` currently doesn't have access to `db`. I need to either pass `db` as an argument or lazy-load group info.

Actually, looking at how it's called - both in `upload_scene` (where we have `db`) and `list_scenes` (where we have `db`). But the function signature doesn't take a `db` parameter. I should change it to accept an optional `db` parameter, or just do a simpler approach: store the group name directly on the scene object via a relationship, or just include `group_id` and let the frontend look up the name.

Simplest approach: just include `group_id` in the response dict and let the frontend map group_id → group_name. The group list is already fetched by the frontend anyway.

Let me revise:

```python
def _custom_scene_to_dict(scene: CustomScene) -> dict:
    return {
        "key": f"custom_{scene.id.hex}",
        "name": scene.name,
        "description": f"自定义场景: {scene.name}",
        "defaultModel": scene.model_filename.replace(".pt", ""),
        "originalModelName": scene.original_model_name or scene.model_filename.replace(".pt", ""),
        "icon": "Monitor",
        "classNames": scene.class_names if isinstance(scene.class_names, dict) else json.loads(scene.class_names),
        "is_public": scene.is_public,
        "is_custom": True,
        "scene_id": str(scene.id),
        "user_id": str(scene.user_id),
        "group_id": str(scene.group_id) if scene.group_id else None,
    }
```

And also update `BUILT_IN_SCENES` to include `is_public: True` and `group_id: null` for consistency.

- [ ] **Step 4: Extend the delete endpoint for cascade delete**

Modify the `delete_scene` endpoint to also delete detection records:

```python
@router.delete("/{scene_id}")
async def delete_scene(
    scene_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    import uuid as uuid_lib
    try:
        uid = uuid_lib.UUID(scene_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的场景 ID")

    record = db.query(CustomScene).filter(CustomScene.id == uid).first()
    if not record:
        raise HTTPException(status_code=404, detail="场景不存在")
    if str(record.user_id) != current_user["sub"]:
        raise HTTPException(status_code=403, detail="只能删除自己的场景")

    # Delete model file
    model_path = os.path.join(MODELS_DIR, record.model_filename)
    if os.path.exists(model_path):
        os.remove(model_path)

    # Delete from MinIO
    from app.utils.minio_client import delete_file as minio_delete
    minio_delete(settings.MINIO_BUCKET, record.model_filename)

    # Delete related detection history
    scene_key = f"custom_{record.id.hex}"
    from app.models.detection import DetectionRecord
    deleted = db.query(DetectionRecord).filter(DetectionRecord.scene == scene_key).delete()

    # Delete DB record
    db.delete(record)
    db.commit()

    return {"success": True, "message": f"场景已删除，同时清理了 {deleted} 条检测记录"}
```

- [ ] **Step 5: Add `is_public` and `group_id` to built-in scenes**

```python
BUILT_IN_SCENES = [
    {
        "key": "steel",
        "name": "钢铁表面缺陷检测",
        "description": "对钢铁表面图像进行缺陷识别与定位",
        "defaultModel": "gt",
        "icon": "Monitor",
        "is_public": True,
        "is_custom": False,
        "group_id": None,
        "classNames": {
            "rolled-in_scale": "轧制氧化皮",
            "patches": "斑块",
            "crazing": "开裂",
            "pitted_surface": "点蚀表面",
            "inclusion": "内含物",
            "scratches": "划痕",
        },
    },
    {
        "key": "general",
        "name": "通用目标检测",
        "description": "基于 COCO 数据集的通用目标识别",
        "defaultModel": "yolo11n",
        "icon": "Picture",
        "is_public": True,
        "is_custom": False,
        "group_id": None,
        "classNames": {},
    },
]
```

- [ ] **Step 6: Fix `_custom_scene_to_dict` — needs db session for group name**

Actually, let me reconsider. The `_custom_scene_to_dict` function is called without a `db` session in some code paths (e.g., after `db.commit()` the object is detached but available). Since we can't access the group relationship easily without session, I'll just return `group_id` and let the frontend map it.

The existing function stays simple:

```python
def _custom_scene_to_dict(scene: CustomScene) -> dict:
    return {
        "key": f"custom_{scene.id.hex}",
        "name": scene.name,
        "description": f"自定义场景: {scene.name}",
        "defaultModel": scene.model_filename.replace(".pt", ""),
        "originalModelName": scene.original_model_name or scene.model_filename.replace(".pt", ""),
        "icon": "Monitor",
        "classNames": scene.class_names if isinstance(scene.class_names, dict) else json.loads(scene.class_names),
        "is_public": scene.is_public,
        "is_custom": True,
        "scene_id": str(scene.id),
        "user_id": str(scene.user_id),
        "group_id": str(scene.group_id) if scene.group_id else None,
    }
```

And the `list_scenes` endpoint also needs to return group mappings for built-in scenes. After getting the mappings:

```python
@router.get("")
async def list_scenes(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_id = current_user["sub"]
    custom = (
        db.query(CustomScene)
        .filter(
            (CustomScene.is_public == True) | (CustomScene.user_id == user_id)
        )
        .all()
    )

    # Get group mappings for built-in scenes
    from app.models.user_scene_group_mapping import UserSceneGroupMapping
    mappings = {
        m.scene_key: str(m.group_id)
        for m in db.query(UserSceneGroupMapping).filter(
            UserSceneGroupMapping.user_id == user_id
        ).all()
    }

    # Annotate built-in scenes with group_id
    builtins = []
    for s in BUILT_IN_SCENES:
        s_copy = dict(s)
        s_copy["group_id"] = mappings.get(s["key"])
        builtins.append(s_copy)

    return {
        "success": True,
        "data": builtins + [_custom_scene_to_dict(s) for s in custom],
    }
```

---

### Task 5: Frontend — Group API

**Files:**
- Modify: `frontend/src/api/scenes.js`

- [ ] **Step 1: Add group API functions**

Add to `frontend/src/api/scenes.js`:

```javascript
export const getSceneGroups = () => {
  return request({
    url: "/scenes/groups",
    method: "get",
  });
};

export const createSceneGroup = (name) => {
  const formData = new FormData();
  formData.append("name", name);
  return request({
    url: "/scenes/groups",
    method: "post",
    data: formData,
  });
};

export const renameSceneGroup = (id, name) => {
  const formData = new FormData();
  formData.append("name", name);
  return request({
    url: `/scenes/groups/${id}`,
    method: "put",
    data: formData,
  });
};

export const deleteSceneGroup = (id) => {
  return request({
    url: `/scenes/groups/${id}`,
    method: "delete",
  });
};

export const assignSceneGroup = (sceneKey, groupId) => {
  const formData = new FormData();
  if (groupId) formData.append("group_id", groupId);
  return request({
    url: `/scenes/${sceneKey}/group`,
    method: "put",
    data: formData,
  });
};
```

---

### Task 6: Frontend — SceneSelector Major Rewrite

**Files:**
- Modify: `frontend/src/views/SceneSelector.vue`

- [ ] **Step 1: Add left sidebar panel for groups**

The template needs restructuring — wrap the existing grid in a flex container with a left sidebar:

```vue
<template>
  <div class="scene-selector">
    <div class="page-header">
      <!-- existing header -->
    </div>

    <div class="scene-layout">
      <!-- Left sidebar: groups -->
      <div class="group-sidebar">
        <div class="group-sidebar-header">
          <span class="group-sidebar-title">场景分组</span>
          <el-button size="small" circle @click="showCreateGroup = true">
            <el-icon><Plus /></el-icon>
          </el-button>
        </div>
        <div class="group-list">
          <div
            class="group-item"
            :class="{ active: selectedGroupId === null }"
            @click="selectedGroupId = null"
          >
            <span>📁 全部场景</span>
            <span class="group-count">{{ allScenes.length }}</span>
          </div>
          <div
            class="group-item"
            :class="{ active: selectedGroupId === '__ungrouped' }"
            @click="selectedGroupId = '__ungrouped'"
          >
            <span>📁 未分组</span>
            <span class="group-count">{{ ungroupedCount }}</span>
          </div>
          <div
            v-for="group in groups"
            :key="group.id"
            class="group-item"
            :class="{ active: selectedGroupId === group.id }"
            @click="selectedGroupId = group.id"
          >
            <span>📁 {{ group.name }}</span>
            <span class="group-count">{{ group.scene_count }}</span>
          </div>
        </div>
        <div class="group-sidebar-footer">
          <el-button text size="small" @click="showCreateGroup = true">
            <el-icon><Plus /></el-icon> 新建分组
          </el-button>
        </div>
      </div>

      <!-- Right: scene grid -->
      <div class="scene-grid-container">
        <div class="scene-grid">
          <div v-for="scene in filteredScenes" :key="scene.key" class="scene-card" ...>
            <!-- existing card with new badges and group tag -->
          </div>
          <!-- upload card -->
        </div>
      </div>
    </div>
  </div>
</template>
```

Full template and script details:

```vue
<script setup>
import { ref, computed, onMounted } from "vue"
import { useRouter } from "vue-router"
import { ElMessage, ElMessageBox } from "element-plus"
import { Monitor, Picture, ArrowRight, Plus, Delete, Edit } from "@element-plus/icons-vue"
import { getSceneList, buildCustomSceneConfig, getSceneConfig, registerCustomScenes } from "../config/scenes"
import { getScenes, uploadCustomScene, deleteCustomScene, getSceneGroups, createSceneGroup, renameSceneGroup, deleteSceneGroup, assignSceneGroup } from "../api/scenes"

const router = useRouter()

const customSceneList = ref([])
const groups = ref([])
const selectedGroupId = ref(null) // null = all, '__ungrouped' = ungrouped
const showCreateGroup = ref(false)
const showRenameGroup = ref(false)
const renameTarget = ref(null)
const newGroupName = ref("")

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

// Scene CRUD (existing + enhanced)
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
       • 该场景的所有检测历史记录<br>
       • 关联的检测结果图片<br><br>
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
```

- [ ] **Step 2: Update the template — restructure with sidebar**

The full template structure with sidebar:

```vue
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

    <div class="scene-layout">
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
          <span class="section-title" v-if="selectedGroupId === null">全部场景</span>
          <span class="section-title" v-else-if="selectedGroupId === '__ungrouped'">未分组场景</span>
          <span class="section-title" v-else>{{ selectedGroupName }}</span>
        </div>

        <div class="scene-grid">
          <div
            v-for="scene in filteredScenes"
            :key="scene.key"
            class="scene-card"
            :class="{ 'custom-scene': scene.is_custom }"
            @click="goToScene(scene)"
          >
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
                  :placeholder="'分组'"
                  style="width: 110px"
                  @click.stop
                  @change="(val) => handleSceneGroupChange(scene, val)"
                >
                  <el-option label="未分组" :value="null" />
                  <el-option v-for="g in groups" :key="g.id" :label="g.name" :value="g.id" />
                </el-select>
                <el-button
                  v-if="scene.is_custom && scene.scene_id && scene.user_id === currentUserId"
                  size="small"
                  type="danger"
                  link
                  @click.stop="confirmDelete(scene)"
                >
                  <el-icon><Delete /></el-icon>
                </el-button>
              </div>
            </div>
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

    <!-- 上传对话框 -->
    <el-dialog v-model="showUploadDialog" title="上传自定义模型" width="500px" ...>
      <!-- existing upload dialog content -->
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
```

- [ ] **Step 3: Add sidebar styles**

Add to the `<style scoped>` section:

```css
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
```

- [ ] **Step 4: Add group action handler**

```javascript
function handleGroupAction(cmd, group) {
  if (cmd === "rename") promptRenameGroup(group)
  else if (cmd === "delete") confirmDeleteGroup(group)
}

const selectedGroupName = computed(() => {
  if (selectedGroupId.value === null) return "全部场景"
  if (selectedGroupId.value === "__ungrouped") return "未分组场景"
  const g = groups.value.find(g => g.id === selectedGroupId.value)
  return g ? g.name : "全部场景"
})
```

Also need to add `MoreFilled` to the icon imports.

---

### Task 7: Frontend — Update scenes.js config

**Files:**
- Modify: `frontend/src/config/scenes.js`

- [ ] **Step 1: Update buildCustomSceneConfig to include group_id**

```javascript
export function buildCustomSceneConfig(custom) {
  const names = custom.classNames || {}
  const targets = Object.entries(names).map(([nameKey, name], i) => ({
    id: i + 1,
    name: name,
    categoryId: 1,
    description: name,
    accuracy: "-",
  }))

  return {
    key: custom.key,
    name: custom.name || "自定义场景",
    subtitle: `自定义检测场景 - ${custom.name || ""}`,
    description: custom.description || `自定义场景: ${custom.name || ""}`,
    defaultModel: custom.defaultModel,
    originalModelName: custom.originalModelName || custom.defaultModel,
    icon: custom.icon || "Monitor",
    is_custom: true,
    is_public: custom.is_public !== undefined ? custom.is_public : false,
    group_id: custom.group_id || null,
    labels: GENERIC_LABELS,
    classNames: names,
    targetGroups: targets.length > 0
      ? [{ id: 1, name: "识别目标", icon: "Monitor", color: "#1a56db", targets }]
      : [],
  }
}
```

---

### Task 8: Stop Server, Build Frontend, Restart, Verify

- [ ] **Step 1: Kill current backend**

```bash
wsl -d Ubuntu -- bash -c "fuser -k 8000/tcp 2>/dev/null; echo 'killed'"
```

- [ ] **Step 2: Build frontend**

```bash
wsl -d Ubuntu bash -c "export PATH=\"/home/cwl/.nvm/versions/node/v24.15.0/bin:\$PATH\" && cd /home/cwl/yaogan/frontend && npm run build"
```

- [ ] **Step 3: Start backend**

```bash
wsl -d Ubuntu -- bash -c "cd /home/cwl/yaogan/backend && nohup .venv/bin/python3 main.py &>/tmp/yaogan.log & sleep 3 && lsof -ti:8000"
```

- [ ] **Step 4: Verify endpoints**

```bash
# Health check
wsl -d Ubuntu -- bash -c "curl -s http://127.0.0.1:8000/health"

# Login as admin
wsl -d Ubuntu -- bash -c "curl -s -X POST http://127.0.0.1:8000/api/auth/login -H 'Content-Type: application/json' -d '{\"username\":\"admin\",\"password\":\"admin123\"}'"
```

- [ ] **Step 5: Test group creation and scene grouping**

```bash
# Get token first
TOKEN=$(wsl -d Ubuntu -- bash -c "curl -s -X POST http://127.0.0.1:8000/api/auth/login -H 'Content-Type: application/json' -d '{\"username\":\"admin\",\"password\":\"admin123\"}' | python3 -c \"import sys,json; print(json.load(sys.stdin)['access_token'])\"")

# List scenes
wsl -d Ubuntu -- bash -c "curl -s http://127.0.0.1:8000/api/scenes -H 'Authorization: Bearer $TOKEN' | python3 -m json.tool"
```
