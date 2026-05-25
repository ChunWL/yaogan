# 公开模型市场 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用户可上传带简介描述的公开模型，其他用户可在"获取模型"市场浏览并有选择地下载使用。

**Architecture:** 后端新增 AcquiredScene 表跟踪用户获取记录，CustomScene 增加 description 字段。前端 SceneSelector 增加 Tab 切换（我的场景/获取模型），侧边栏增加已获取场景区域。获取时立即从 MinIO 下载 .pt 文件。

**Tech Stack:** FastAPI + SQLAlchemy + Vue 3 + Element Plus + MinIO

---

## 文件变更清单

| 操作 | 文件 | 说明 |
|------|------|------|
| 新建 | `backend/app/models/acquired_scene.py` | AcquiredScene 模型 |
| 修改 | `backend/app/models/custom_scene.py` | 加 description 字段 |
| 修改 | `backend/main.py` | 加 migration、注册新路由 |
| 修改 | `backend/app/api/scenes.py` | 场景列表范围调整、新增 marketplace/acquire 等端点 |
| 修改 | `frontend/src/api/scenes.js` | 新增 marketplace/acquire 接口 |
| 修改 | `frontend/src/views/SceneSelector.vue` | 加 Tab、市场卡片、上传加描述 |
| 修改 | `frontend/src/components/Sidebar.vue` | 加已获取场景区域 |

---

### Task 1: 新建 AcquiredScene 模型

**Files:**
- Create: `backend/app/models/acquired_scene.py`

- [ ] **Step 1: 创建 acquired_scene.py**

```python
import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from app.utils.db import Base
from datetime import datetime


def china_now():
    return datetime.utcnow()


class AcquiredScene(Base):
    __tablename__ = "acquired_scenes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    custom_scene_id = Column(UUID(as_uuid=True), ForeignKey("custom_scenes.id"), nullable=False)
    created_at = Column(DateTime, default=china_now)

    __table_args__ = (
        UniqueConstraint("user_id", "custom_scene_id", name="uq_user_acquired_scene"),
    )
```

- [ ] **Step 2: 验证导入**

Run: `wsl -d Ubuntu -- bash -c "cd /home/cwl/yaogan/backend && .venv/bin/python3 -c 'from app.models.acquired_scene import AcquiredScene; print(\"OK\")'"`
Expected: `OK`

---

### Task 2: CustomScene 加 description 字段

**Files:**
- Modify: `backend/app/models/custom_scene.py`

- [ ] **Step 1: 添加 description 字段**

在 `class_names` 行后加：
```python
    description = Column(String(500), default="")
```

- [ ] **Step 2: 验证导入**

Run: `wsl -d Ubuntu -- bash -c "cd /home/cwl/yaogan/backend && .venv/bin/python3 -c 'from app.models.custom_scene import CustomScene; print(\"OK\")'"`
Expected: `OK`

---

### Task 3: migration + 路由注册

**Files:**
- Modify: `backend/main.py`

- [ ] **Step 1: 添加 description 列 migration**

在 `_run_migrations()` 函数中 `custom_scenes` 表检测部分内添加：
```python
        if "description" not in custom_columns:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE custom_scenes ADD COLUMN description VARCHAR(500) DEFAULT ''"))
```

找到：
```python
        if "group_id" not in custom_columns:
```
在该 if 块之后添加。

- [ ] **Step 2: 验证 migration 导入**

Run: `wsl -d Ubuntu -- bash -c "cd /home/cwl/yaogan/backend && .venv/bin/python3 -c 'from main import app; print(\"OK\")'"`
Expected: `OK`

---

### Task 4: 后端 API — marketplace + acquire + 场景列表调整

**Files:**
- Modify: `backend/app/api/scenes.py`

涉及改动的部分：

1. 上传端点加 `description` 参数
2. 场景列表改为：内置 + 自己的 + 已获取的
3. 新增 GET /api/models/marketplace
4. 新增 POST /api/models/acquire/{scene_id}
5. 新增 DELETE /api/models/acquire/{scene_id}

- [ ] **Step 1: 在 scenes.py 顶部增加导入**

```python
import uuid as uuid_lib
from sqlalchemy import or_
from app.models.acquired_scene import AcquiredScene
from app.models.user import User
```

注意 `uuid as uuid_lib` 可能已存在，检查后再加。`or_` 可能也已有导入。

- [ ] **Step 2: 修改上传端点，接受 description**

找到 `upload_scene` 函数，在 `name: str = Form(...)` 后加：
```python
    description: str = Form(""),
```

在 `original_name = (file.filename or "").replace(".pt", "")` 行后，创建 record 时增加：
```python
        description=description,
```

- [ ] **Step 3: 修改场景列表 — 只返回内置 + 自己的 + 已获取的**

将 `list_scenes` 函数中的：
```python
    custom = (
        db.query(CustomScene)
        .filter(
            (CustomScene.is_public == True) | (CustomScene.user_id == user_id)
        )
        .all()
    )
```

替换为：
```python
    # 自己的自定义场景
    own_scenes = db.query(CustomScene).filter(
        CustomScene.user_id == user_id
    ).all()

    # 已获取的公开场景（其他用户的）
    acquired_ids = [
        a.custom_scene_id
        for a in db.query(AcquiredScene).filter(AcquiredScene.user_id == user_id).all()
    ]
    acquired_scenes = []
    if acquired_ids:
        acquired_scenes = db.query(CustomScene).filter(
            CustomScene.id.in_(acquired_ids)
        ).all()

    custom = own_scenes + acquired_scenes
```

- [ ] **Step 4: 新增 marketplace 端点**

在文件末尾（`assign_scene_group` 之后）添加：

```python
@router.get("/marketplace")
async def list_marketplace(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """列出当前用户可获取的公开模型（非自己上传、未获取的）"""
    user_id = current_user["sub"]

    # 已获取的 id 列表
    acquired_ids = [
        a.custom_scene_id
        for a in db.query(AcquiredScene).filter(AcquiredScene.user_id == user_id).all()
    ]

    # 公开 + 非自己 + 未获取
    query = db.query(CustomScene).filter(
        CustomScene.is_public == True,
        CustomScene.user_id != user_id,
    )
    if acquired_ids:
        query = query.filter(CustomScene.id.notin_(acquired_ids))

    scenes = query.order_by(CustomScene.created_at.desc()).all()

    # 获取上传者用户名
    user_ids = list(set(str(s.user_id) for s in scenes))
    users = {
        str(u.id): u.username
        for u in db.query(User).filter(User.id.in_([uuid_lib.UUID(uid) for uid in user_ids])).all()
    } if user_ids else {}

    result = []
    for s in scenes:
        d = _custom_scene_to_dict(s)
        d["creator_name"] = users.get(str(s.user_id), "未知用户")
        d["description"] = s.description or ""
        result.append(d)

    return {"success": True, "data": result}
```

- [ ] **Step 5: 新增 acquire 端点**

```python
@router.post("/acquire/{scene_id}")
async def acquire_scene(
    scene_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取一个公开模型：下载 .pt + 创建获取记录"""
    try:
        uid = uuid_lib.UUID(scene_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的场景 ID")

    scene = db.query(CustomScene).filter(CustomScene.id == uid).first()
    if not scene:
        raise HTTPException(status_code=404, detail="场景不存在")
    if not scene.is_public:
        raise HTTPException(status_code=403, detail="该场景不是公开的")
    if str(scene.user_id) == current_user["sub"]:
        raise HTTPException(status_code=400, detail="不能获取自己的模型")

    # 检查是否已获取
    existing = db.query(AcquiredScene).filter(
        AcquiredScene.user_id == current_user["sub"],
        AcquiredScene.custom_scene_id == uid,
    ).first()
    if existing:
        return {"success": True, "message": "已获取过该模型"}

    # 下载 .pt 文件（从 MinIO 到本地）
    model_filename = scene.model_filename
    model_path = os.path.join(MODELS_DIR, model_filename)
    if not os.path.exists(model_path):
        from app.utils.minio_client import download_file
        downloaded = download_file(settings.MINIO_BUCKET, model_filename, model_path)
        if not downloaded:
            raise HTTPException(status_code=500, detail="模型文件下载失败")

    # 创建获取记录
    record = AcquiredScene(
        user_id=current_user["sub"],
        custom_scene_id=uid,
    )
    db.add(record)
    db.commit()

    return {"success": True, "message": "模型获取成功"}
```

- [ ] **Step 6: 新增 unacquire 端点**

```python
@router.delete("/acquire/{scene_id}")
async def unacquire_scene(
    scene_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """移除已获取的模型"""
    try:
        uid = uuid_lib.UUID(scene_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的场景 ID")

    record = db.query(AcquiredScene).filter(
        AcquiredScene.user_id == current_user["sub"],
        AcquiredScene.custom_scene_id == uid,
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="未获取过该模型")

    db.delete(record)
    db.commit()

    return {"success": True, "message": "已移除"}
```

- [ ] **Step 7: 新增已获取列表端点**

```python
@router.get("/acquired")
async def list_acquired_scenes(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """列出当前用户已获取的模型（供侧边栏使用）"""
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
            })

    return {"success": True, "data": result}
```

- [ ] **Step 8: 验证修改**

Run: `wsl -d Ubuntu -- bash -c "cd /home/cwl/yaogan/backend && .venv/bin/python3 -c \"from app.api.scenes import router; print('OK')\""`
Expected: `OK`

---

### Task 5: 前端 API 层

**Files:**
- Modify: `frontend/src/api/scenes.js`

- [ ] **Step 1: 追加新接口**

```javascript
export const getModelMarketplace = () => {
  return request({
    url: "/scenes/marketplace",
    method: "get",
  });
};

export const acquireModel = (sceneId) => {
  return request({
    url: `/scenes/acquire/${sceneId}`,
    method: "post",
  });
};

export const unacquireModel = (sceneId) => {
  return request({
    url: `/scenes/acquire/${sceneId}`,
    method: "delete",
  });
};

export const getAcquiredModels = () => {
  return request({
    url: "/scenes/acquired",
    method: "get",
  });
};
```

---

### Task 6: 侧边栏 — 已获取场景

**Files:**
- Modify: `frontend/src/components/Sidebar.vue`

- [ ] **Step 1: 在 script setup 中增加已获取场景加载**

在 `onMounted` 中已有的逻辑后，增加：
```javascript
import { getAcquiredModels } from "../api/scenes";

const acquiredScenes = ref([]);

onMounted(async () => {
  // ... existing code ...
  try {
    const res = await getAcquiredModels();
    if (res.success && res.data) {
      acquiredScenes.value = res.data;
    }
  } catch {
    // ignore
  }
});
```

- [ ] **Step 2: 在模板中增加已获取场景区域**

在"更多功能"菜单项之后，`</div>` 之前插入：
```html
<div v-if="acquiredScenes.length > 0" class="sidebar-divider">已获取场景</div>
<div
  v-for="item in acquiredScenes"
  :key="item.key"
  class="nav-item"
  :class="{ active: currentPath === '/detection' && (route.query.scene === item.key || sceneKey === item.key) }"
  @click="handleAcquiredSceneClick(item)"
>
  <el-icon :size="18" class="nav-icon"><Picture /></el-icon>
  <span class="nav-text">{{ item.name }}</span>
</div>
```

侧边栏底部样式新增：
```css
.sidebar-divider {
  font-size: 11px;
  color: var(--text-secondary);
  padding: 12px 12px 6px;
  text-transform: uppercase;
  letter-spacing: 1px;
  border-top: 1px solid var(--border-color);
  margin-top: 8px;
}
```

- [ ] **Step 3: 添加点击事件处理**

```javascript
const acquiredSceneKey = computed(() => {
  return localStorage.getItem("scene") || "";
});

const handleAcquiredSceneClick = (item) => {
  router.push({ path: "/detection", query: { scene: item.key } });
};
```

---

### Task 7: SceneSelector 页面 — 获取模型 Tab 等

**Files:**
- Modify: `frontend/src/views/SceneSelector.vue`

- [ ] **Step 1: 读取当前文件完整内容**

Run: `cat` 确认当前 SceneSelector.vue 内容。

- [ ] **Step 2: 增加 Tab 切换（el-tabs + el-tab-pane）**

在 `<div class="scene-selector-container">` 内顶部增加：
```html
<div class="scene-tabs">
  <el-tabs v-model="activeTab">
    <el-tab-pane label="我的场景" name="mine" />
    <el-tab-pane label="获取模型" name="marketplace" />
  </el-tabs>
</div>
```

script setup 增加：
```javascript
const activeTab = ref("mine");
```

- [ ] **Step 3: 将原有场景列表用 `v-if="activeTab === 'mine'"` 包裹**

场景列表容器外包裹 `<div v-if="activeTab === 'mine'">`

- [ ] **Step 4: 新增 marketplace 网格**

```html
<div v-else-if="activeTab === 'marketplace'" class="marketplace-container">
  <div v-if="marketplaceLoading" class="loading-state">
    <el-skeleton :rows="3" animated />
  </div>
  <div v-else-if="marketplaceList.length === 0" class="empty-state">
    <el-empty description="暂无更多公开模型" />
  </div>
  <div v-else class="scene-grid">
    <div
      v-for="item in marketplaceList"
      :key="item.key"
      class="scene-card marketplace-card"
    >
      <div class="card-content">
        <div class="card-title">{{ item.name }}</div>
        <el-tag size="small" type="warning" class="scene-badge">公开</el-tag>
      </div>
      <div class="card-creator">上传者: {{ item.creator_name || '未知' }}</div>
      <div class="card-desc">{{ item.description || '暂无描述' }}</div>
      <div class="card-actions">
        <el-button
          type="primary"
          size="small"
          :disabled="item.acquired"
          @click="handleAcquire(item)"
        >
          {{ item.acquired ? '已获取' : '获取模型' }}
        </el-button>
      </div>
    </div>
  </div>
</div>
```

- [ ] **Step 5: script setup 中增加 marketplace 逻辑**

```javascript
import { getModelMarketplace, acquireModel } from "../api/scenes";

const marketplaceList = ref([]);
const marketplaceLoading = ref(false);

async function loadMarketplace() {
  marketplaceLoading.value = true;
  try {
    const res = await getModelMarketplace();
    if (res.success && res.data) {
      marketplaceList.value = res.data;
    }
  } catch {
    // ignore
  } finally {
    marketplaceLoading.value = false;
  }
}

async function handleAcquire(item) {
  try {
    const res = await acquireModel(item.scene_id);
    if (res.success) {
      ElMessage.success("模型获取成功");
      item.acquired = true;
      // 刷新已获取列表
      emitRefreshAcquired();
    }
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || "获取失败");
  }
}

// 监听 tab 切换
watch(activeTab, (tab) => {
  if (tab === "marketplace") {
    loadMarketplace();
  }
});
```

- [ ] **Step 6: 上传对话框增加 description 字段**

在已有上传对话框模板中，名称输入框后加：
```html
<el-form-item label="简介描述" prop="description">
  <el-input
    v-model="uploadForm.description"
    type="textarea"
    :rows="3"
    placeholder="简要描述模型的检测能力（公开时其他用户将看到此描述）"
    maxlength="500"
    show-word-limit
  />
</el-form-item>
```

script 中 uploadForm 加字段：
```javascript
const uploadForm = reactive({
  name: "",
  description: "",
  isPublic: false,
});
```

上传时传 description：
```javascript
formData.append("description", uploadForm.description);
```

---

### Task 8: 前后端联调验证

- [ ] **Step 1: 重启后端**

```bash
wsl -d Ubuntu -- bash -c "kill \$(lsof -ti:8000) 2>/dev/null; sleep 1; cd /home/cwl/yaogan/backend && .venv/bin/python3 main.py &>/tmp/yaogan.log &"
sleep 8
```

- [ ] **Step 2: 构建前端**

```bash
wsl -d Ubuntu bash -c "export PATH=\"/home/cwl/.nvm/versions/node/v24.15.0/bin:\$PATH\" && cd /home/cwl/yaogan/frontend && npm run build"
```

- [ ] **Step 3: 测试场景 — 上传公开模型**

用 curl 或浏览器登录后用两个不同账号测试：
1. 账号 A 上传一个模型（带 description），设为公开
2. 账号 B 打开"获取模型"Tab → 应看到 A 的模型 + 描述
3. 账号 B 点击"获取" → 成功
4. 账号 B 侧边栏出现已获取场景
5. 账号 B 可切换到该场景进行检测
