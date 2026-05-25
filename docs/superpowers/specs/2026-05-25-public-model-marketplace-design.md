# 公开模型市场 — 设计文档

## 概述

为钢铁表面缺陷检测平台增加公开模型市场功能，使不同用户可以浏览、获取其他用户上传的公开模型，同时保护隐私（私有模型不泄露）。

## 数据模型变更

### CustomScene 新增字段

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `description` | Text | `""` | 模型简介描述，公开时由上传者填写 |

### 新建 AcquiredScene 表

```python
class AcquiredScene(Base):
    __tablename__ = "acquired_scenes"
    id          = Column(UUID, primary_key=True, default=uuid.uuid4)
    user_id     = Column(UUID, ForeignKey("users.id"), nullable=False, index=True)
    custom_scene_id = Column(UUID, ForeignKey("custom_scenes.id"), nullable=False)
    created_at  = Column(DateTime, default=china_now)
    __table_args__ = (UniqueConstraint("user_id", "custom_scene_id"),)
```

## API 变更

### 1. POST /api/scenes/upload — 新增 description 参数

接受 `description: str = Form("")`，存入 CustomScene。

### 2. GET /api/scenes — 场景列表范围调整

改前：内置 + 全部公开 + 自己的自定义场景
改后：内置 + 自己的自定义场景 + 已获取的公开场景（通过 AcquiredScene 关联）

### 3. GET /api/models/marketplace — 公开模型市场

返回当前用户**未获取**的、**非自己上传**的公开模型列表，含 description + 上传者用户名。

```python
# 查询条件：
CustomScene.is_public == True
AND CustomScene.user_id != current_user["sub"]
AND CustomScene.id NOT IN (acquired scene ids for current user)
```

返回字段：key, name, description, defaultModel, classNames, creator_name, created_at

### 4. POST /api/models/acquire/{scene_id} — 获取模型

1. 校验 scene_id 对应的 CustomScene 存在且 is_public=True
2. 下载 .pt 文件从 MinIO 到 backend/models/（如本地已有则跳过）
3. 创建 AcquiredScene 记录
4. 返回成功

### 5. DELETE /api/models/acquire/{scene_id} — 移除已获取模型

删除 AcquiredScene 记录（不删除本地 .pt 文件，其他已获取用户可能还在用）。

### 6. GET /api/models/acquired — 已获取模型列表

返回当前用户通过 AcquireScene 获取的所有模型列表。供侧边栏渲染使用。

## 侧边栏变更

Sidebar.vue 在"更多功能"下方新增"已获取场景"分区，从 `/api/models/acquired` 获取数据。点击直接跳转到对应场景的检测页面。

## 前端页面变更

### SceneSelector.vue — 新增 Tab 切换

在顶部添加 el-tabs：

- **我的场景** Tab：现有内容不变（分组 + 场景卡片 + 上传卡片）
- **获取模型** Tab：从 `/api/models/marketplace` 拉取数据，卡片网格展示
  - 每张卡片：模型名、简介描述、上传者用户名、获取/已获取按钮
  - 已获取的模型显示"已获取"（disabled），未获取的显示"获取"按钮
  - 获取后卡片自动变为"已获取"状态

### 上传对话框 — 新增简介描述字段

在名称下方添加 el-input type="textarea"，非必填。

## 隐私保障

- 私有模型的 original_model_name、class_names 不暴露给其他用户
- Marketplace 只展示 is_public=True 的模型
- 场景列表不自动拉取所有公开场景
- 获取操作需认证（所有新增 endpoint 都有 Depends(get_current_user)）
