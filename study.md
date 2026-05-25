# 钢铁表面缺陷检测平台 — 技术学习指南

> 项目路径: `~/yaogan` （WSL Ubuntu）
> 完整名称: 基于 YOLO 的目标检测平台

---

## 一、项目架构总览

```
┌──────────────────────────────────────────────────────────────────┐
│                     浏览器 (Chrome/Edge)                         │
│   http://localhost:8000                                          │
│   Vue 3 SPA — 单页应用 (frontend/dist/)                          │
└──────────────────┬───────────────────────────────────────────────┘
                   │ HTTP REST (JSON) / WebSocket (binary frames)
                   ▼
┌──────────────────────────────────────────────────────────────────┐
│              FastAPI (backend/main.py — :8000)                    │
│                                                                  │
│   路由分组:                                                       │
│   ┌─ /api/auth/*          — 登录 / 注册 / JWT 认证              │
│   ├─ /api/detection/*     — 单图 / 批量 / 视频 / 摄像头检测      │
│   ├─ /api/scenes/*        — 场景管理 / 分组 / 上传模型           │
│   ├─ /api/admin/*         — 管理员用户管理                       │
│   ├─ /api/files/*         — MinIO 图片代理（流式返回）            │
│   └─ /api/models/list     — 可用模型列表                         │
│                                                                  │
│   服务层:                                                        │
│   DetectionService (YOLO 推理引擎，懒加载模型)                    │
│   process_video_task.py (独立子进程，视频检测)                    │
│                                                                  │
│   数据层:                                                        │
│   SQLAlchemy ORM → PostgreSQL :5432                              │
│   MinIO Client → MinIO :9000（S3 兼容对象存储）                  │
│   Redis :6379（已配置但尚未使用）                                 │
└──────┬─────────────────┬────────────────────┬────────────────────┘
       │                 │                    │
       ▼                 ▼                    ▼
┌──────────────┐ ┌────────────┐ ┌────────────────────────────┐
│  PostgreSQL  │ │   Redis    │ │  MinIO 对象存储             │
│  :5432       │ │  :6379     │ │  :9000 API / :9001 Console │
│              │ │  (未使用)   │ │                            │
│  6 张表:     │ │            │ │  3 个 bucket:              │
│  users       │ │            │ │  models/ (模型文件)        │
│  detection_  │ │            │ │  uploads/ (用户上传原图)    │
│  records     │ │            │ │  results/ (检测结果图)      │
│  custom_     │ │            │ │                            │
│  scenes      │ │            │ │  数据持久化:                │
│  scene_      │ │            │ │  ./storage/minio/data      │
│  groups      │ │            │ │                            │
│  user_scene_ │ │            │ │                            │
│  group_mapp- │ │            │ │                            │
│  ings        │ │            │ │                            │
└──────────────┘ └────────────┘ └────────────────────────────┘
```

**三个 Docker 容器**（通过 docker-compose 编排）：
- `rsod-postgres` — 数据存储
- `rsod-redis` — 缓存（基础设施就绪，代码尚未使用）
- `rsod-minio` — 文件/图片/模型存储

**运行环境拓扑**:
```
Windows 浏览器 ← localhost:8000 → WSL Ubuntu (FastAPI)
                                      │
                              Docker Compose (PostgreSQL + Redis + MinIO)
```

---

## 二、核心技术栈清单

| # | 技术 | 版本 | 角色 | 难度 | 建议学习时间 |
|---|------|------|------|------|------------|
| 1 | **Docker / Docker Compose** | latest | 容器编排基础设施 | ⭐⭐ | 2-3天 |
| 2 | **Python FastAPI** | ≥0.104.0 | 后端 Web 框架 | ⭐⭐⭐ | 1周 |
| 3 | **SQLAlchemy 2.0** | ≥2.0.0 | ORM 数据库框架 | ⭐⭐⭐ | 1周 |
| 4 | **PostgreSQL 15** | 15 | 关系型数据库 | ⭐⭐ | 3天 |
| 5 | **JWT (python-jose)** | ≥3.3.0 | 认证方案 | ⭐⭐ | 1天 |
| 6 | **Vue 3 (Composition API)** | ^3.5.34 | 前端框架 | ⭐⭐⭐⭐ | 2周 |
| 7 | **Vite** | ^8.0.12 | 前端构建工具 | ⭐⭐ | 1天 |
| 8 | **Element Plus** | ^2.7.6 | UI 组件库 | ⭐⭐ | 3天 |
| 9 | **Axios** | ^1.7.2 | HTTP 客户端 | ⭐ | 0.5天 |
| 10 | **Vue Router** | ^4.4.0 | 前端路由 | ⭐⭐ | 1天 |
| 11 | **YOLO (Ultralytics)** | ≥8.0.0 | 目标检测 AI 引擎 | ⭐⭐⭐ | 3天 |
| 12 | **MinIO (S3 SDK)** | ≥7.2.0 | 对象存储 | ⭐⭐ | 1天 |
| 13 | **WebSocket** | 内置 FastAPI | 实时通信 | ⭐⭐⭐ | 1天 |
| 14 | **OpenCV (cv2)** | ≥4.8.0 | 图像处理 | ⭐⭐ | 2天 |
| 15 | **Pydantic** | ≥2.5.0 | 数据验证 | ⭐⭐ | 1天 |
| 16 | **passlib (bcrypt)** | ≥1.7.4 | 密码哈希 | ⭐ | 0.5天 |

---

## 三、逐技术深度解析

---

### 1. Docker & Docker Compose

**文件**: [docker-compose.yaml](docker-compose.yaml)

#### 你需要在项目中看到什么

三个服务定义在同一个 yaml 文件中：

```yaml
services:
  postgres:
    image: postgres:15
    ports: ["5432:5432"]
    environment:
      POSTGRES_USER: rsod_user
      POSTGRES_PASSWORD: rsod_password
      POSTGRES_DB: rsod_db
    volumes:
      - ./storage/postgres/data:/var/lib/postgresql/data
    healthcheck: ...
```

#### 核心概念

| 概念 | 解释 | 本项目用法 |
|------|------|-----------|
| **image** | 镜像（模板） | `postgres:15`, `redis:7`, `minio/minio:latest` |
| **container** | 镜像的运行实例 | 每个服务一个容器 |
| **ports** | 宿主机端口:容器端口 | 宿主机 5432 → 容器 PostgreSQL |
| **volumes** | 数据持久化 | WSL 目录映射到容器内，容器删数据不丢 |
| **environment** | 环境变量 | 数据库账号密码、MinIO 密钥 |
| **healthcheck** | 健康检查 | 确保依赖服务就绪后才启动 |
| **depends_on** | 启动顺序 | （本项目未使用，因为 FastAPI 不是容器） |

#### 关键命令

```bash
# 启动所有服务（后台）
docker-compose up -d

# 查看运行状态
docker ps

# 查看日志
docker-compose logs postgres

# 停止所有服务
docker-compose down

# 进入容器内部
docker exec -it rsod-postgres psql -U rsod_user -d rsod_db
```

#### 学习要点

1. 理解**容器 vs 虚拟机**的区别：共享宿主机内核，更轻量
2. 理解**数据卷 (volumes)** 为什么重要：容器删除后数据还在
3. 理解**端口映射**：WSL 内部端口 → Windows localhost 访问
4. 这个项目中 FastAPI **不是容器运行**的，而是直接在 WSL 中用 Python 启动。Docker 只跑基础设施（数据库、缓存、存储）

---

### 2. FastAPI（Python 后端）

**相关文件**:
- [backend/main.py](backend/main.py) — 入口
- [backend/app/config.py](backend/app/config.py) — 配置
- [backend/app/api/*.py](backend/app/api/) — 路由
- [backend/app/services/detection_service.py](backend/app/services/detection_service.py) — 服务层
- [backend/app/utils/*.py](backend/app/utils/) — 工具模块
- [backend/app/models/*.py](backend/app/models/) — 数据模型

#### 入口文件 (main.py) 做了 5 件事

```python
# 1. 启动时自动执行
@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)  # 创建所有表
    _run_migrations()                      # 执行增量迁移
    ensure_buckets()                       # 创建 MinIO buckets
    yield

# 2. 注册 4 个路由分组
app.include_router(auth_router, prefix="/api")
app.include_router(detection_router, prefix="/api")
app.include_router(admin_router, prefix="/api")
app.include_router(scenes_router, prefix="/api")

# 3. 挂载静态文件
app.mount("/assets", StaticFiles(...))     # 前端构建产物
app.mount("/static/videos", StaticFiles(...))
app.mount("/static", StaticFiles(...))

# 4. 图片代理（MinIO → 浏览器）
@app.get("/api/files/{bucket}/{filename}")

# 5. SPA fallback（所有未知路径返回 index.html）
@app.get("/{full_path:path}")
```

#### FastAPI 依赖注入模式

这是 FastAPI **最核心**的设计模式：

```python
# 定义依赖：从 HTTP header 提取当前用户
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    payload = verify_token(credentials.credentials)
    if payload is None:
        raise HTTPException(status_code=401)
    return payload

# 在 API 中使用：FastAPI 自动调用 get_current_user()
@app.post("/detection/single")
async def detect(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),   # ← 注入
    db: Session = Depends(get_db),                     # ← 注入
):
    # current_user 已经是认证后的用户信息
    # db 已经是可用的数据库 session
```

**好处**：代码解耦、自动复用、自动错误处理。

#### Pydantic 模型（请求/响应校验）

```python
class DetectionBox(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float
    confidence: float
    class_id: int
    class_name: str

# FastAPI 自动：
# 1. 校验请求体是否符合模型
# 2. 生成 OpenAPI 文档
# 3. 序列化响应为 JSON
```

#### 配置管理

判断一个配置项在哪里设置：

```python
# backend/app/config.py
class Settings(BaseModel):
    HOST: str = "0.0.0.0"           # 默认值（代码硬编码）
    PORT: int = 8000
    DATABASE_URL: str = "postgresql://..."
    JWT_SECRET_KEY: str = "..."

# 自动覆盖：从 .env 文件读取同名变量
settings = get_settings()
# .env 文件中的 DATABASE_URL 会覆盖 Settings 类默认值
```

#### 学习要点

1. 理解 `async/await` — 异步编程的核心概念
2. 理解 `Depends()` — 依赖注入的工作原理
3. 理解 `APIRouter` — 路由分组组织代码
4. 理解 `lifespan` — 应用生命周期的钩子函数
5. 理解 Pydantic `BaseModel` — 数据校验和序列化

---

### 3. PostgreSQL + SQLAlchemy

**相关文件**:
- [backend/app/utils/db.py](backend/app/utils/db.py) — 数据库连接
- [backend/app/models/*.py](backend/app/models/) — 表模型定义

#### 数据库连接

```python
# SQLAlchemy 引擎 + session
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# FastAPI 依赖：每个请求一个 session，用完自动关闭
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

#### 6 张表结构

**users** — 用户表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| username | String(50) | 唯一，索引 |
| email | String(100) | 唯一，索引 |
| hashed_password | String(255) | bcrypt 哈希 |
| is_active | Boolean | 是否激活 |
| is_admin | Boolean | 是否管理员 |
| created_at | DateTime | 北京时间 |

**detection_records** — 检测记录表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| user_id | UUID(FK) | 外键 → users |
| filename | String(255) | 原文件名 |
| image_url / result_image_url | String(500) | 图片 URL |
| image_path / result_path | String(500) | 本地路径 |
| total_objects | Integer | 检测到的目标数 |
| detection_time | Float | 检测耗时 |
| model_name | String | 使用的模型 |
| status | String | completed/failed |
| type | String | single/batch/video |
| scene | String(50) | 所属场景，索引 |
| defect_results | JSON | 检测框数组 |
| created_at | DateTime | 北京时间 |

**custom_scenes** — 自定义场景表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| user_id | UUID(FK) | 上传者 |
| name | String | 场景名称 |
| model_filename | String | 模型文件名 |
| original_model_name | String | 原始文件名 |
| class_names | JSON | 类别映射 |
| is_public | Boolean | 是否公开 |
| group_id | UUID(FK) | 所属分组 |
| created_at | DateTime | |

**scene_groups** — 场景分组表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| user_id | UUID(FK) | 所属用户 |
| name | String | 分组名称 |
| created_at | DateTime | |

**user_scene_group_mappings** — 内置场景分组映射表（内置场景没有 DB 记录，所以用这个表关联分组）
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| user_id | UUID(FK) | 用户 |
| scene_key | String | 场景 key（如 "steel"） |
| group_id | UUID(FK) | 分组 |

#### CRUD 操作模式

```python
# 查询单条
user = db.query(User).filter(User.id == user_id).first()

# 查询多条 + 过滤 + 排序 + 分页
records = (
    db.query(DetectionRecord)
    .filter(DetectionRecord.user_id == user_id)
    .filter(DetectionRecord.scene == scene)
    .order_by(DetectionRecord.created_at.desc())
    .offset((page - 1) * page_size)
    .limit(page_size)
    .all()
)

# 新增
record = DetectionRecord(id=uuid.uuid4(), user_id=user_id, ...)
db.add(record)
db.commit()

# 更新
user.email = new_email
db.commit()

# 删除
db.delete(record)
db.commit()
```

#### migration 策略（无 Alembic）

项目没有用 Alembic 做数据库迁移，而是手动检查+执行：

```python
def _run_migrations():
    inspector = inspect(engine)
    columns = [c["name"] for c in inspector.get_columns("detection_records")]
    if "scene" not in columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE detection_records ADD COLUMN scene VARCHAR(50) DEFAULT 'steel'"))
```

这保证了在**已有数据的数据库上安全加字段**，不会丢数据。

#### 学习要点

1. ORM 概念：Python 类 ↔ 数据库表的映射
2. Session 管理：为什么每个请求要独立的 session
3. CRUD 操作：增删改查的写法
4. JSON 列类型：PostgreSQL 支持 JSON 字段存储
5. UUID 主键 vs 自增 ID：UUID 的优缺点
6. 事务管理：`commit()` / `rollback()`

---

### 4. JWT 认证系统

**文件**: [backend/app/utils/auth.py](backend/app/utils/auth.py)

#### 流程图

```
登录 → 验证用户名密码
     → create_access_token(payload) 生成 JWT
     → 返回 {access_token, user_info} 给前端
     → 前端存 localStorage
     
后续请求 → 前端在 HTTP Header 带 Authorization: Bearer <token>
        → get_current_user() 验证 token
        → 从 payload 提取 user_id, is_admin
        → 注入到 API 函数中使用
```

#### 核心代码

```python
# 生成 token（编码）
def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

# 验证 token（解码）
def verify_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        return None
```

#### JWT Payload 结构

```json
{
  "sub": "uuid-string",      // 用户 ID
  "username": "admin",       // 用户名
  "is_admin": true,          // 管理员标记
  "exp": 1700000000          // 过期时间戳
}
```

#### 重要：JWT 一旦签发不能撤销

- 没有「踢人下线」功能（除非用黑名单，本项目未实现）
- token 过期时间 24 小时
- 隐私信息（如密码）不能放 payload

#### 前端配合

```javascript
// request.js — 请求拦截器自动带 token
service.interceptors.request.use(config => {
  const token = localStorage.getItem("token")
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截器 — 401 自动跳登录
service.interceptors.response.use(
  response => response.data,
  error => {
    if (error.response?.status === 401) {
      localStorage.removeItem("token")
      window.location.href = "/login"
    }
  }
)
```

#### 学习要点

1. 对称加密 vs 非对称加密：本项目用的是对称的 HS256
2. JWT 三个部分：header.payload.signature
3. JWT vs Session：无状态 vs 有状态
4. bcrypt 密码哈希：为什么不能存明文
5. 前端 token 存储：localStorage vs cookie（本项目用 localStorage）

---

### 5. Vue 3 + Vite 前端

**相关文件**:
- [frontend/src/main.js](frontend/src/main.js) — 入口
- [frontend/src/App.vue](frontend/src/App.vue) — 根组件
- [frontend/src/router/index.js](frontend/src/router/index.js) — 路由
- [frontend/src/views/*.vue](frontend/src/views/) — 页面组件
- [frontend/src/components/*.vue](frontend/src/components/) — 通用组件
- [frontend/src/config/scenes.js](frontend/src/config/scenes.js) — 场景配置
- [frontend/src/api/*.js](frontend/src/api/) — API 封装
- [frontend/src/utils/request.js](frontend/src/utils/request.js) — Axios 实例

#### 项目入口流程

```javascript
// main.js — 应用初始化
const app = createApp(App)
app.use(ElementPlus)       // 注册 UI 组件库
app.use(router)            // 注册路由
app.mount("#app")
```

```vue
<!-- App.vue — 根组件 -->
<template>
  <!-- 登录/注册等页面不用 Layout，直接显示 -->
  <router-view v-if="isAuthPage" />
  <!-- 主体页面用 MainLayout 包裹（侧边栏 + 顶栏 + 内容区） -->
  <MainLayout v-else>
    <template #sidebar><Sidebar /></template>
    <template #header><Header /></template>
    <template #content><router-view /></template>
  </MainLayout>
</template>

<script setup>
// 应用启动时加载自定义场景配置
onMounted(async () => {
  const res = await getScenes()
  if (res.success && res.data) {
    const configs = res.data.filter(s => s.is_custom).map(buildCustomSceneConfig)
    registerCustomScenes(configs)
  }
})
</script>
```

#### 路由守卫

```javascript
// router/index.js
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem("token")
  const authPaths = ["/login", "/register", "/forgot-password"]

  if (authPaths.includes(to.path)) {
    next()           // 登录页始终可访问
  } else if (!token) {
    next("/login")   // 其他页面需要 token
  } else {
    next()
  }
})
```

#### 页面对应关系

| URL | 组件 | 功能 |
|-----|------|------|
| `/login` | LoginPage.vue | 登录 |
| `/register` | RegisterPage.vue | 注册 |
| `/scenes` | SceneSelector.vue | 选择检测场景 |
| `/detection?scene=xxx` | DetectionPage.vue | **核心：图片/视频/摄像头检测** |
| `/history?scene=xxx` | HistoryPage.vue | 检测历史记录 |
| `/targets?scene=xxx` | TargetsPage.vue | 目标类型库 |
| `/profile` | ProfilePage.vue | 个人信息 |
| `/admin/users` | AdminUsersPage.vue | 管理员用户管理 |
| `/qa` | QAPage.vue | 智能问答（静态） |

#### Vue 3 Composition API 核心写法

```vue
<script setup>
import { ref, computed, onMounted } from "vue"

// 响应式状态
const count = ref(0)
const user = ref(null)

// 计算属性
const doubleCount = computed(() => count.value * 2)

// 生命周期
onMounted(async () => {
  const res = await fetchData()
  user.value = res.data
})

// 方法
function handleClick() {
  count.value++
}
</script>
```

**ref() vs reactive()**：本项目只用 `ref()`，是更推荐的写法。`ref()` 可以包装任何类型（包括对象），模板中自动解包，script 中要用 `.value` 访问。

#### Vite 构建

```javascript
// vite.config.js
export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0',
    proxy: { '/api': { target: 'http://localhost:8000' } }
  }
})
```

**重要：dev 模式已废弃**。Vite dev server 在 WSL 中进程存活但不响应 HTTP，所以改成了：
```
修改前端代码 → npm run build → FastAPI serve frontend/dist/ → 刷新浏览器
```

#### 学习要点

1. Composition API（`<script setup>`）vs Options API
2. 响应式原理：`ref()` 的 getter/setter
3. Vue Router：路由定义、守卫、参数传递
4. 组件通信：props / emit
5. 生命周期：`onMounted`, `onUnmounted` 等
6. 构建流程：dev vs build

---

### 6. Element Plus UI 组件库

**文件**: [frontend/src/main.js](frontend/src/main.js), [frontend/src/style.css](frontend/src/style.css)

#### 自动导入配置

```javascript
// vite.config.js
plugins: [
  AutoImport({ resolvers: [ElementPlusResolver()] }),
  Components({ resolvers: [ElementPlusResolver()] }),
]
```

自动导入意味着在 `<template>` 中可以直接写 `<el-button>`，不需要手动 `import { ElButton } from 'element-plus'`。但图标需要**全局注册**：

```javascript
// main.js — 全局注册所有图标
import * as ElementPlusIconsVue from "@element-plus/icons-vue"
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}
```

这样模板中可以直接用 `<el-icon><Monitor /></el-icon>`。

#### 项目中用到的组件

| 组件 | 位置 | 用途 |
|------|------|------|
| `<el-form>` | LoginPage, DetectionPage | 表单 |
| `<el-upload>` | DetectionPage | 文件上传 |
| `<el-table>` | HistoryPage, AdminUsersPage | 数据表格 |
| `<el-dropdown>` | Header | 用户菜单 |
| `<el-dialog>` | SceneSelector | 弹窗 |
| `<el-menu>` | Sidebar | 侧边栏菜单（已改为自定义 Nav） |
| `<el-icon>` | 各处 | 图标 |
| `<el-avatar>` | Header | 用户头像 |
| `<el-tooltip>` | Header | 工具提示 |
| `<el-select>` | DetectionPage | 模型选择 |
| `<el-tag>` | SceneSelector | 标签 |

#### 主题色系统

```css
/* style.css — 所有颜色通过 CSS 变量控制 */
:root {
  --app-primary: #1a56db;          /* 品牌蓝 */
  --app-primary-dark: #1e3a5f;     /* 深蓝（header 背景） */
  --app-bg: #f4f5f7;               /* 页面背景 */
  --el-color-primary: #1a56db;     /* 覆盖 Element Plus 主色 */
}
```

一次修改全局生效，所有 Element Plus 组件颜色跟着变。

---

### 7. Axios 封装

**文件**: [frontend/src/utils/request.js](frontend/src/utils/request.js)

#### 做了什么

```javascript
const service = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 30000
})

// 请求拦截器：自动带 JWT token
service.interceptors.request.use(config => {
  const token = localStorage.getItem("token")
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// 响应拦截器：自动解包 data + 401 处理
service.interceptors.response.use(
  response => response.data,      // 直接拿到 data，不需 .data.data
  error => {
    if (error.response?.status === 401) {
      localStorage.removeItem("token")
      window.location.href = "/login"
    }
    ElMessage.error(error.response?.data?.detail || '请求失败')
    return Promise.reject(error)
  }
)
```

#### API 封装模式

```javascript
// src/api/detection.js
export const detectSingleImage = (data) => {
  return request({
    url: "/detection/single",
    method: "post",
    data,
    headers: { "Content-Type": "multipart/form-data" },
  })
}

// 页面中使用：
import { detectSingleImage } from "@/api/detection"
const res = await detectSingleImage(formData)
// res 已经是 response.data，即 {success, message, data}
```

#### 学习要点

1. 请求/响应拦截器的作用
2. `baseURL` 通过环境变量配置
3. 统一的错误处理
4. `multipart/form-data` 上传文件的 header

---

### 8. YOLO + Ultralytics（AI 检测引擎）

**文件**: [backend/app/services/detection_service.py](backend/app/services/detection_service.py)

#### 什么是 YOLO

YOLO = You Only Look Once。一次「看」整张图就能检测出所有目标的位置和类别，不需要像传统方法那样滑动窗口扫描。

**核心输出**：每个检测框包含：
- `xyxy` — 左上角和右下角坐标 (x1, y1, x2, y2)
- `confidence` — 置信度（0~1）
- `class_id` / `class_name` — 类别（如 "person", "car"）

#### 模型懒加载 + 缓存

```python
def _get_model(self, model_name: str):
    if model_name in self.models:         # 已加载 → 直接返回缓存
        return self.models[model_name]

    model_path = f"backend/models/{name}.pt"
    if not os.path.exists(model_path):    # 本地没有 → 从 MinIO 下载
        download_model(model_filename, model_path)

    model = YOLO(model_path)              # 加载模型
    self.models[model_name] = model       # 缓存
    return model
```

#### 检测流程

```python
def detect_single_image(self, image_path, model_name) -> DetectionResult:
    # 1. 加载模型
    model = self._get_model(model_name)

    # 2. 执行推理
    results = model.predict(
        source=image_path,
        conf=settings.CONFIDENCE_THRESHOLD,  # 置信度阈值 0.5
        iou=settings.IOU_THRESHOLD,          # 去重阈值 0.45
        save=False                            # 不自动保存
    )

    # 3. 从 results 提取检测框
    boxes = []
    for result in results:
        for box in result.boxes:
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            confidence = float(box.conf[0])
            class_id = int(box.cls[0])
            # ...

    # 4. 绘制标注图（已标注框和文字的结果图）
    annotated_image = results[0].plot()    # ← 返回 BGR 格式！
    cv2.imwrite(result_path, annotated_image)  # 直接保存，不要转换颜色

    # 5. 返回结果
    return DetectionResult(
        detection_id=str(uuid.uuid4()),
        image_url=...,
        result_image_url=...,
        boxes=boxes,
        total_objects=len(boxes),
        detection_time=round(time.time() - start_time, 3),
        model_name=model_name,
        created_at=datetime.now()
    )
```

#### 两个特别重要的点

**① `plot()` 返回 BGR**（重要！）

```python
# results[0].plot() 内部用 OpenCV，返回的是 BGR
annotated_image = results[0].plot()
# 直接保存：
cv2.imwrite(result_path, annotated_image)
# 绝不要做：
# cv2.cvtColor(annotated_image, cv2.COLOR_RGB2BGR)  ← 会红蓝互换！
```

**② 动态 class names**

```python
def _get_class_names(self, model) -> dict:
    if hasattr(model, "names") and model.names:
        names = model.names
        sample = next(iter(names.values()), "")
        # 检查是否是真名还是数字索引
        if not sample.isdigit():
            return names
    # 兜底：钢铁缺陷的 6 类
    return {0: "rolled-in_scale", 1: "patches", ...}
```

#### 轻量检测（摄像头用）

```python
def detect_frame(self, image_array: np.ndarray, model_name: str) -> dict:
    """无文件 I/O、无 DB 写入，只返回框坐标"""
    model = self._get_model(model_name)
    results = model.predict(source=image_array, ...)
    boxes = [...]
    return {"boxes": boxes, "total_objects": len(boxes)}
```

#### 学习要点

1. YOLO 核心概念：目标检测 = 定位 + 分类
2. 模型文件 (.pt) 是什么：PyTorch 权重文件
3. 推理参数：`conf`（置信度）和 `iou`（去重阈值）
4. 结果对象结构：`results[0].boxes`, `results[0].plot()`
5. 模型加载 → 缓存 → 复用的性能优化

---

### 9. MinIO 对象存储

**文件**: [backend/app/utils/minio_client.py](backend/app/utils/minio_client.py)

#### 为什么需要 MinIO

- 图片文件不能存数据库（太大、太慢）
- 本地文件系统不利于扩展和备份
- MinIO 是 S3 兼容的，未来可无缝切换到 AWS S3

#### 三个 Bucket

| Bucket | 存什么 | 举例 |
|--------|--------|------|
| `models` | 模型文件 | `custom_xxx.pt` |
| `uploads` | 用户上传的原图 | `abc123.jpg` |
| `results` | 检测后的结果图 | `result_def456.jpg` |

#### 数据流（以单图检测为例）

```
用户上传 → save_upload_file()
  ├─ 存本地 static/uploads/xxx.jpg    （给 YOLO 用，YOLO 读本地文件）
  ├─ 上传到 MinIO uploads bucket      （永久存储）
  │
YOLO 检测 → 生成结果图
  ├─ 存本地 static/results/xxx.jpg    （临时）
  ├─ 上传到 MinIO results bucket      （永久存储）
  │
清理 → 删除本地 static/uploads/ 和 static/results/ 中的文件
      （MinIO 中的数据保留）

前端读取 → GET /api/files/uploads/xxx.jpg
         → minio_client.get_file_response()
         → StreamingResponse（流式返回，支持大图）
```

#### MinIO API 封装

```python
# 客户端单例
_minio_client = None
def get_minio_client():
    if _minio_client is None:
        _minio_client = Minio(settings.MINIO_ENDPOINT, ...)
    return _minio_client

# 上传文件
def upload_file(bucket, object_name, file_path):
    client.fput_object(bucket, object_name, file_path)

# 上传字节
def upload_fileobj(bucket, object_name, data):
    client.put_object(bucket, object_name, io.BytesIO(data), len(data))

# 流式返回（给 FastAPI 用）
def get_file_response(bucket, object_name):
    response = client.get_object(bucket, object_name)
    return StreamingResponse(response.stream(32*1024), media_type=content_type)

# 删除
def delete_file(bucket, object_name):
    client.remove_object(bucket, object_name)
```

#### 注意点

- MinIO 数据在 WSL 文件系统中：`~/yaogan/storage/minio/data/`
- 管理控制台：`http://localhost:9001`（账号见 docker-compose.yaml）
- 如果 localhost 访问不了 9001，用 WSL IP 地址
- 图片 URL 格式：`/api/files/results/xxx.jpg`

#### 学习要点

1. 对象存储 vs 文件系统 vs 数据库
2. S3 兼容 API 的意义
3. bucket 概念（类似顶级文件夹）
4. StreamingResponse 流式传输
5. 本地临时文件 + 远程永久存储的两层架构

---

### 10. WebSocket + 摄像头实时检测

**相关文件**:
- [backend/app/api/detection.py:577-616](backend/app/api/detection.py#L577-L616) — 后端
- [frontend/src/views/DetectionPage.vue](frontend/src/views/DetectionPage.vue) — 前端

#### WebSocket 是什么

- HTTP：请求 → 响应 → 断开（单向，每次都要建连接）
- WebSocket：连接建立后可以**双向随时发送**数据（全双工）

#### 摄像头检测流程

```
┌─ 浏览器 ──────────────────────────────────────┐
│                                                │
│  getUserMedia → <video> 显示实时画面            │
│                                                │
│  requestAnimationFrame 循环:                    │
│    每隔一帧:                                    │
│      canvas.toBlob(JPEG, 0.7)                  │
│      WebSocket.send(binary)                    │
│                                                │
│  WebSocket 收到 JSON:                          │
│      {frame_id, boxes, total_objects}          │
│      Canvas 叠加绘制检测框                      │
│                                                │
│  控制: 停止 / 暂停继续 / 保存快照               │
└───────────────────┬────────────────────────────┘
                    │ Binary (JPEG)
                    ▼
┌─ FastAPI 后端 ─────────────────────────────────┐
│                                                 │
│  WS /api/detection/ws/camera?token=xxx          │
│                                                 │
│  1. 验证 token                                   │
│  2. 接收二进制 → cv2.imdecode → numpy array     │
│  3. detection_service.detect_frame()            │
│     → 轻量推理（无文件 I/O、无 DB）              │
│  4. 返回 JSON {frame_id, boxes, total_objects}  │
│                                                 │
│  异常: WebSocketDisconnect → 优雅关闭            │
└─────────────────────────────────────────────────┘
```

#### 关键实现细节

```python
# 后端 WebSocket
@router.websocket("/ws/camera")
async def camera_websocket(
    websocket: WebSocket,
    token: str = Query(...),          # token 在 URL query 中
    model_name: str = Query("yolo11n"),
):
    user = verify_token(token)
    if not user:
        await websocket.close(code=4001)    # 无效 token 直接关闭
        return

    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_bytes()   # 接收 JPEG 二进制
            nparr = np.frombuffer(data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)  # 解码为图像
            result = detection_service.detect_frame(img, model_name)
            await websocket.send_json({...})             # 返回检测结果
    except WebSocketDisconnect:
        pass
```

```javascript
// 前端 WebSocket 连接
const ws = new WebSocket(`ws://${host}/api/detection/ws/camera?token=${token}&model_name=yolo11n`)

// 发送帧
ws.send(blob)  // blob 是 JPEG 编码的二进制数据

// 接收结果
ws.onmessage = (event) => {
  const { boxes } = JSON.parse(event.data)
  drawBoxes(canvas, boxes)  // Canvas 叠加绘制
}
```

#### 学习要点

1. WebSocket vs HTTP 的区别
2. 二进制传输 vs JSON 传输
3. WebSocket 认证方式（不支持 headers，只能用 query）
4. `getUserMedia` 获取摄像头流
5. `requestAnimationFrame` 控制帧率
6. Canvas 叠加层绘制

---

### 11. 视频检测（子进程架构）

**相关文件**:
- [backend/app/api/detection.py:75-105](backend/app/api/detection.py#L75-L105) — 启动子进程
- [backend/app/process_video_task.py](backend/app/process_video_task.py) — 子进程入口

#### 为什么用子进程？

视频检测需要逐帧推理，耗时可能数分钟。如果直接在线程中跑 GPU 推理，**会导致 uvicorn 进程崩溃**。

**解决方案**: 用独立子进程跑检测，主进程只管接受请求、返回 task_id。

#### 流程

```
POST /api/detection/video
  → 保存上传视频到 static/uploads/
  → _run_video_subprocess()
    → subprocess.Popen(cmd, start_new_session=True)
    → 返回 task_id 给前端

子进程独立运行:
  → app/process_video_task.py
    → 逐帧 YOLO 推理（每 frame_interval=5 帧检测一次）
    → 4K → 720p 缩放（max_dim=1280）
    → VP80/WebM 编码输出
    → 每 10 帧写一次 JSON 进度文件
    → 检测完成 → 写 DetectionRecord 到 PostgreSQL

前端轮询:
  GET /api/detection/video/progress/{task_id}
  → 读取 JSON 进度文件 → 返回进度百分比
```

#### 子进程启动代码

```python
def _run_video_subprocess(task_id, video_path, model_name, scene, frame_interval, user_id):
    cmd = [
        python_exe,              # backend/.venv/bin/python3
        task_script,             # app/process_video_task.py
        video_path, task_id, model_name, scene,
        str(frame_interval), user_id, output_dir, status_file,
    ]

    subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,   # 关键！防止子进程随终端关闭被杀死
        cwd=backend_dir,
    )
```

#### JSON 进度文件读写

```python
# 格式: data/videos/.tasks/{task_id}.json
# 内容:
{
    "status": "processing",        # processing / completed / failed
    "progress": 45.0,              # 百分比
    "processed_frames": 450,
    "total_frames": 1000,
    "result_video_url": "/static/videos/xxx.webm",
    "summary": { ... },            # 检测结果摘要
    "user_id": "uuid",
    "scene": "steel"
}
```

#### 学习要点

1. 为什么 GPU 推理要在子进程而非线程中运行
2. `subprocess.Popen` vs `subprocess.run`
3. `start_new_session=True` 的作用（进程保活）
4. 文件进度通信模式（写 JSON 文件 + 轮询）
5. 视频编码选择（VP80/WebM 是因为浏览器兼容性）

---

### 12. 多场景检测系统

**相关文件**:
- [frontend/src/config/scenes.js](frontend/src/config/scenes.js) — 场景配置
- [backend/app/api/scenes.py](backend/app/api/scenes.py) — 场景管理 API

#### 设计思想

把「检测模型」和「UI 表现」解耦。每个场景（Scene）是一个配置单元：

```
场景 = 模型文件(.pt) + 文案配置(labels) + 类别数据(targetGroups)
```

#### 内置场景

```javascript
// scenes.js
export const SCENES = {
  steel: {
    key: "steel",
    name: "钢铁表面缺陷检测",
    defaultModel: "gt",
    labels: {
      target: "缺陷",
      targetUnit: "处缺陷",
      diagnosis: "检测到 {count} 处缺陷，耗时 {time}s",
    },
    classNames: { "rolled-in_scale": "轧制氧化皮", ... },
    targetGroups: [ /* 缺陷分组数据 */ ],
  },
  general: {
    key: "general",
    name: "通用目标检测",
    defaultModel: "yolo11n",
    labels: { target: "目标", targetUnit: "个目标", ... },
    classNames: {},
    targetGroups: [ /* COCO 类别数据 */ ],
  },
}
```

#### 自定义场景（用户上传）

```python
# 用户上传 .pt 模型 → 后端处理流程
1. 保存 .pt 文件到 backend/models/
2. 上传到 MinIO models bucket 备份
3. extraction_service.get_model_class_names() 提取类别
4. 创建 CustomScene 记录到 PostgreSQL
5. 返回场景配置给前端

# 前端注册
// App.vue onMounted()
const res = await getScenes()     // 获取所有场景（内置 + 自定义）
const configs = res.data
  .filter(s => s.is_custom)
  .map(buildCustomSceneConfig)    // 转为统一配置格式
registerCustomScenes(configs)     // 注册到全局场景 Map
```

#### 场景切换持久化

```
选择场景 → 存 localStorage.setItem("scene", "steel")
         → 导航到 /detection?scene=steel

侧边栏点击 → 自动携带 ?scene= 参数
页面刷新 → 从 URL 参数或 localStorage 恢复场景
```

#### 学习要点

1. **配置驱动设计**: 把变化的部分提取为配置，不改代码就扩展
2. 前端全局注册模式：`App.vue` 启动时一次性加载自定义场景
3. 场景隔离：检测记录通过 `scene` 字段隔离，不同场景互不干扰
4. 级联删除：删场景 → 删模型文件 → 删 MinIO → 删检测记录

---

### 13. 路径管理

**文件**: [backend/app/utils/path.py](backend/app/utils/path.py)

项目的 marker 文件模式：

```python
PROJECT_MARKER = "gt_platform"    # 项目根目录下有这个文件

def find_project_root(start_path=None) -> Path:
    """从当前位置向上找 gt_platform 文件，确定项目根目录"""
    current = Path(start_path).resolve()
    for parent in [current, *current.parents]:
        if (parent / PROJECT_MARKER).exists():
            return parent
```

这样任何模块都能定位到项目根，不依赖当前工作目录。

---

### 14. WSL 开发注意事项

**文件**: [CLAUDE.md](CLAUDE.md) 有完整记录

| 问题 | 解决方案 |
|------|---------|
| 文件路径 | 用 `\\wsl.localhost\Ubuntu\home\cwl\yaogan\...` |
| 执行命令 | 包在 `wsl -d Ubuntu -- bash -c "..."` 里 |
| Vite dev 挂死 | 改用 `npm run build` + FastAPI serve |
| 端口转发不稳定 | 后端监听 `0.0.0.0:8000` |
| 子进程保活 | `start_new_session=True` |
| MinIO 控制台 | 如果 localhost 不行，用 WSL IP |

---

## 四、推荐学习路径（按顺序）

```
第一周：基础设施
  Docker → docker-compose → 容器概念
  PostgreSQL → SQL 基础 → 表设计

第二周：后端
  Python FastAPI → 路由 → 依赖注入 → Pydantic
  SQLAlchemy → ORM → CRUD → 模型定义
  JWT → 认证流程 → token 原理

第三周：AI 检测
  YOLO 概念 → Ultralytics → model.predict()
  MinIO → 对象存储 → S3 API

第四周：前端
  Vue 3 Composition API → 组件 → 响应式
  Vue Router → 路由守卫 → 参数传递
  Element Plus → UI 组件 → 主题
  Axios → 请求封装 → 拦截器

第五周：进阶
  WebSocket → 实时通信 → 摄像头检测
  子进程 → 视频检测架构
  多场景系统设计模式
  MinIO + 本地两级存储
```

---

## 五、推荐的教程资源

| 技术 | 免费教程 | 推荐指数 |
|------|---------|---------|
| Docker | [Docker 从入门到实践](https://yeasy.gitbook.io/docker_practice/) | ⭐⭐⭐⭐⭐ |
| FastAPI | [官方文档](https://fastapi.tiangolo.com/zh/) | ⭐⭐⭐⭐⭐ |
| Vue 3 | [官方教程](https://cn.vuejs.org/guide/introduction.html) | ⭐⭐⭐⭐⭐ |
| YOLO | [Ultralytics 文档](https://docs.ultralytics.com/zh) | ⭐⭐⭐⭐ |
| PostgreSQL | [PostgreSQL 教程](http://www.postgresqltutorial.com/) | ⭐⭐⭐⭐ |
| SQLAlchemy | [官方文档](https://docs.sqlalchemy.org/en/20/) | ⭐⭐⭐ |
| MinIO | [MinIO 官方文档](https://min.io/docs/minio/linux/index.html) | ⭐⭐⭐ |
| WebSocket | [MDN WebSocket 教程](https://developer.mozilla.org/zh-CN/docs/Web/API/WebSocket) | ⭐⭐⭐⭐ |

---

## 六、自测问题清单

学完每个技术后，尝试回答以下问题：

**Docker**
- [ ] 容器和虚拟机的区别是什么？
- [ ] `docker-compose up -d` 的 `-d` 代表什么？
- [ ] volumes 的作用是什么？

**FastAPI**
- [ ] `Depends()` 如何工作？
- [ ] `APIRouter` 和 `FastAPI()` 的区别？
- [ ] `lifespan` 在什么时候执行？

**SQLAlchemy**
- [ ] `db.commit()` 不调用会怎样？
- [ ] `filter()` 和 `filter_by()` 的区别？
- [ ] UUID 主键 vs 自增 ID 的优缺点？

**Vue 3**
- [ ] `ref()` 和 `reactive()` 的区别？
- [ ] `computed` 和 `watch` 的区别？
- [ ] 路由守卫 `beforeEach` 的三个参数是什么？

**YOLO**
- [ ] `conf` 参数过高或过低会怎样？
- [ ] `results[0].plot()` 返回什么颜色格式？
- [ ] 为什么模型要缓存（懒加载）？

**WebSocket**
- [ ] WebSocket 为什么比 HTTP 更适合实时检测？
- [ ] WebSocket 如何做认证？
- [ ] `WebSocketDisconnect` 异常如何处理？
