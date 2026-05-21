# Auth System Design

## Overview

实现完整的登录/注册/忘记密码功能，前后端打通。当前前端 auth 页面 UI 完整但逻辑为 mock（直接写死 `localStorage.setItem("token", "mock-token")`），后端无任何认证相关代码。

## Architecture

```
LoginPage ──POST /api/auth/login────→ 验证凭证 → 签发JWT → 返回{token, user}
RegisterPage ──POST /api/auth/register──→ 创建用户 → 返回成功
ForgotPasswordPage ──POST /api/auth/forgot-password──→ 占位响应（邮件发送后续实现）
路由守卫 ←── localStorage.token（现有逻辑不变）
Axios拦截器 ←── 请求头 Authorization: Bearer <token>
```

## Backend Changes

### New dependencies
- `python-jose[cryptography]>=3.3.0` — JWT 签发/验证
- `passlib[bcrypt]>=1.7.4` — 密码 bcrypt 哈希

### New files

**`app/utils/db.py`** — SQLAlchemy engine + session factory，连接 docker-compose 中的 PostgreSQL（`rsod_user:rsod_password@localhost:5432/rsod_db`）

**`app/models/user.py`** — User 模型，字段：id (UUID), username (unique), email (unique), hashed_password, created_at, is_active

**`app/utils/auth.py`** — 三个工具函数：
- `hash_password(password) -> str`
- `verify_password(plain, hashed) -> bool`
- `create_access_token(data: dict) -> str` — 签发 JWT，过期时间从 config 读取
- `verify_token(token: str) -> dict` — 验证并解码 JWT

**`app/api/auth.py`** — 三个端点：
- `POST /api/auth/login` — 接收 username+password，校验后返回 JWT token + 用户信息
- `POST /api/auth/register` — 接收 username+email+password，创建用户，返回成功
- `POST /api/auth/forgot-password` — 接收 email，暂返回占位成功消息

### Modified files

**`app/config.py`** — 追加：
- `DATABASE_URL: str = "postgresql://rsod_user:rsod_password@localhost:5432/rsod_db"`
- `JWT_SECRET_KEY: str = "change-me-in-production"`
- `JWT_ALGORITHM: str = "HS256"`
- `JWT_EXPIRE_MINUTES: int = 1440`

**`app/models/schemas.py`** — 追加 Pydantic schema：
- `LoginRequest(username, password)`
- `RegisterRequest(username, email, password)`
- `ForgotPasswordRequest(email)`
- `TokenResponse(access_token, token_type, user: UserInfo)`
- `UserInfo(id, username, email)`

**`main.py`** — 注册 auth router：`app.include_router(auth_router, prefix="/api")`，启动时创建数据库表

## Frontend Changes

### Modified files

**`src/utils/request.js`** — 请求拦截器添加：
```js
const token = localStorage.getItem("token")
if (token) config.headers.Authorization = `Bearer ${token}`
```

**`src/views/LoginPage.vue`** — `handleLogin` 改为调用 API：
- `POST /api/auth/login` with {username, password}
- 成功后存 `localStorage.setItem("token", data.access_token)` 和 `localStorage.setItem("user", JSON.stringify(data.user))`
- 失败时显示后端返回的错误消息

**`src/views/RegisterPage.vue`** — `handleRegister` 改为调用 API：
- `POST /api/auth/register` with {username, email, password}
- 成功后提示并跳转 `/login`
- 失败时显示错误消息

**`src/views/ForgotPasswordPage.vue`** — `handleSubmit` 改为调用 API：
- `POST /api/auth/forgot-password` with {email}
- 后端暂返回占位成功

**`src/views/ProfilePage.vue`** — 从 localStorage 读取用户信息显示真实用户名（最小改动）

## Error Handling

- 后端：用户名已存在 → 409，用户名或密码错误 → 401，参数校验失败 → 422
- 前端：ElMessage 显示后端返回的 detail/message，网络错误由现有响应拦截器处理
- JWT 过期：前端收到 401 时清除 token 跳转登录页

## What's NOT in scope

- 邮件发送（忘记密码的邮件功能暂为占位）
- Token 刷新机制（单 token，过期需重新登录）
- 角色/权限系统
- 用户头像上传
