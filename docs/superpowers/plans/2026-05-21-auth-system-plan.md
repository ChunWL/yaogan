# Auth System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现完整的登录/注册/忘记密码功能，前后端通过 JWT 认证打通。

**Architecture:** 后端新增 auth API（login/register/forgot-password），用 SQLAlchemy 操作 PostgreSQL 用户表，python-jose 签发 JWT，passlib 做 bcrypt 密码哈希。前端三个 auth 页面从 mock 改为调用真实 API，request.js 拦截器添加 Authorization 头。

**Tech Stack:** FastAPI, SQLAlchemy 2.0, PostgreSQL 15, python-jose, passlib[bcrypt], Vue 3, Axios, Element Plus

---

### Task 1: Add new Python dependencies

**Files:**
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Add dependencies to requirements.txt**

Append to `backend/requirements.txt`:

```
# JWT认证
python-jose[cryptography]>=3.3.0

# 密码哈希
passlib[bcrypt]>=1.7.4
```

- [ ] **Step 2: Install the new dependencies**

```bash
cd backend && source .venv/bin/activate && pip install python-jose[cryptography] passlib[bcrypt]
```

Expected: packages installed without errors

- [ ] **Step 3: Commit**

```bash
git add backend/requirements.txt
git commit -m "feat: add python-jose and passlib dependencies for auth"
```

---

### Task 2: Add auth config settings

**Files:**
- Modify: `backend/app/config.py`

- [ ] **Step 1: Add database and JWT settings**

In `backend/app/config.py`, add these fields to the `Settings` class right after the `CORS_ORIGINS` field:

```python
    DATABASE_URL: str = "postgresql://rsod_user:rsod_password@localhost:5432/rsod_db"
    JWT_SECRET_KEY: str = "yaogan-jwt-secret-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440
```

- [ ] **Step 2: Verify config loads correctly**

```bash
cd backend && source .venv/bin/activate && python -c "from app.config import settings; print(settings.DATABASE_URL); print(settings.JWT_ALGORITHM)"
```

Expected: prints the DATABASE_URL and HS256

- [ ] **Step 3: Commit**

```bash
git add backend/app/config.py
git commit -m "feat: add DATABASE_URL and JWT config settings"
```

---

### Task 3: Create database session utility

**Files:**
- Create: `backend/app/utils/db.py`

- [ ] **Step 1: Write the database utility**

Create `backend/app/utils/db.py`:

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 2: Verify the module imports**

```bash
cd backend && source .venv/bin/activate && python -c "from app.utils.db import engine, SessionLocal, Base, get_db; print('OK')"
```

Expected: OK

- [ ] **Step 3: Commit**

```bash
git add backend/app/utils/db.py
git commit -m "feat: add SQLAlchemy database session utility"
```

---

### Task 4: Create User model

**Files:**
- Create: `backend/app/models/user.py`

- [ ] **Step 1: Write the User model**

Create `backend/app/models/user.py`:

```python
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from app.utils.db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
```

- [ ] **Step 2: Verify the model imports**

```bash
cd backend && source .venv/bin/activate && python -c "from app.models.user import User; print('OK')"
```

Expected: OK

- [ ] **Step 3: Commit**

```bash
git add backend/app/models/user.py
git commit -m "feat: add User SQLAlchemy model"
```

---

### Task 5: Create auth utility (password hashing + JWT)

**Files:**
- Create: `backend/app/utils/auth.py`

- [ ] **Step 1: Write the auth utility**

Create `backend/app/utils/auth.py`:

```python
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def verify_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        return None
```

- [ ] **Step 2: Verify the module works**

```bash
cd backend && source .venv/bin/activate && python -c "
from app.utils.auth import hash_password, verify_password, create_access_token, verify_token
h = hash_password('test123')
assert verify_password('test123', h)
assert not verify_password('wrong', h)
t = create_access_token({'sub': 'testuser'})
p = verify_token(t)
assert p['sub'] == 'testuser'
assert verify_token('bad-token') is None
print('ALL OK')
"
```

Expected: ALL OK

- [ ] **Step 3: Commit**

```bash
git add backend/app/utils/auth.py
git commit -m "feat: add password hashing and JWT utility functions"
```

---

### Task 6: Add auth Pydantic schemas

**Files:**
- Modify: `backend/app/models/schemas.py`

- [ ] **Step 1: Append auth schemas**

Append to `backend/app/models/schemas.py`:

```python


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str


class ForgotPasswordRequest(BaseModel):
    email: str


class UserInfo(BaseModel):
    id: str
    username: str
    email: str

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserInfo


class MessageResponse(BaseModel):
    success: bool
    message: str
```

- [ ] **Step 2: Verify schemas import**

```bash
cd backend && source .venv/bin/activate && python -c "from app.models.schemas import LoginRequest, RegisterRequest, ForgotPasswordRequest, TokenResponse, MessageResponse; print('OK')"
```

Expected: OK

- [ ] **Step 3: Commit**

```bash
git add backend/app/models/schemas.py
git commit -m "feat: add auth Pydantic request/response schemas"
```

---

### Task 7: Create auth API routes

**Files:**
- Create: `backend/app/api/auth.py`

- [ ] **Step 1: Write the auth API**

Create `backend/app/api/auth.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.utils.db import get_db
from app.utils.auth import hash_password, verify_password, create_access_token
from app.models.user import User
from app.models.schemas import (
    LoginRequest,
    RegisterRequest,
    ForgotPasswordRequest,
    TokenResponse,
    UserInfo,
    MessageResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == req.username).first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )
    token = create_access_token({"sub": str(user.id), "username": user.username})
    return TokenResponse(
        access_token=token,
        user=UserInfo(id=str(user.id), username=user.username, email=user.email),
    )


@router.post("/register", response_model=MessageResponse)
async def register(req: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(
        or_(User.username == req.username, User.email == req.email)
    ).first()
    if existing:
        if existing.username == req.username:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="用户名已被注册",
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="邮箱已被注册",
        )
    user = User(
        username=req.username,
        email=req.email,
        hashed_password=hash_password(req.password),
    )
    db.add(user)
    db.commit()
    return MessageResponse(success=True, message="注册成功")


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(req: ForgotPasswordRequest):
    return MessageResponse(success=True, message="密码重置链接已发送到您的邮箱（功能开发中）")
```

- [ ] **Step 2: Verify the router imports**

```bash
cd backend && source .venv/bin/activate && python -c "from app.api.auth import router; print('OK')"
```

Expected: OK

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/auth.py
git commit -m "feat: add auth API routes (login, register, forgot-password)"
```

---

### Task 8: Wire up auth router in main.py

**Files:**
- Modify: `backend/main.py`

- [ ] **Step 1: Register auth router and create tables on startup**

In `backend/main.py`, add the import and router registration, and table creation:

Change the imports section (lines 1-6) to:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.config import settings
from app.api.detection import router as detection_router
from app.api.auth import router as auth_router
from app.utils.file_utils import ensure_directories
from app.utils.db import engine, Base
```

Add after `app.include_router(detection_router, prefix="/api")` (line 26):

```python
app.include_router(auth_router, prefix="/api")


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
```

- [ ] **Step 2: Verify the app starts correctly**

```bash
cd backend && source .venv/bin/activate && timeout 5 python main.py 2>&1 || true
```

Expected: app starts without import errors (may show "Application startup complete" or similar)

- [ ] **Step 3: Commit**

```bash
git add backend/main.py
git commit -m "feat: register auth router and auto-create tables on startup"
```

---

### Task 9: Add auth token to Axios request interceptor

**Files:**
- Modify: `frontend/src/utils/request.js`

- [ ] **Step 1: Add Authorization header in request interceptor**

In `frontend/src/utils/request.js`, change the request interceptor from:

```js
service.interceptors.request.use(
  config => {
    return config
  },
```

to:

```js
service.interceptors.request.use(
  config => {
    const token = localStorage.getItem("token")
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
```

Also add 401 handling in the response interceptor. Change the error handler from:

```js
  error => {
    ElMessage.error('请求失败：' + (error.response?.data?.message || '服务器错误'))
    return Promise.reject(error)
  }
```

to:

```js
  error => {
    if (error.response?.status === 401) {
      localStorage.removeItem("token")
      localStorage.removeItem("user")
      window.location.href = "/login"
      return Promise.reject(error)
    }
    ElMessage.error(error.response?.data?.detail || '请求失败，请稍后重试')
    return Promise.reject(error)
  }
```

- [ ] **Step 2: Verify the file is valid**

```bash
cd frontend && npx eslint src/utils/request.js 2>&1 || true
```

Expected: no new errors (existing warnings OK)

- [ ] **Step 3: Commit**

```bash
git add frontend/src/utils/request.js
git commit -m "feat: add JWT token to request headers and handle 401 responses"
```

---

### Task 10: Connect LoginPage to backend API

**Files:**
- Modify: `frontend/src/views/LoginPage.vue`

- [ ] **Step 1: Add API import**

Add after the existing imports in `<script setup>`:

```js
import request from "../utils/request.js";
```

- [ ] **Step 2: Rewrite handleLogin to call API**

Replace the `handleLogin` function (lines 89-96) with:

```js
const loading = ref(false);

const handleLogin = () => {
  loginFormRef.value.validate(async (valid) => {
    if (!valid) return;
    loading.value = true;
    try {
      const res = await request.post("/auth/login", {
        username: loginForm.username,
        password: loginForm.password,
      });
      localStorage.setItem("token", res.access_token);
      localStorage.setItem("user", JSON.stringify(res.user));
      ElMessage.success("登录成功");
      router.push("/detection");
    } catch (error) {
      // error already handled by interceptor
    } finally {
      loading.value = false;
    }
  });
};
```

- [ ] **Step 3: Add ElMessage import**

Add `ElMessage` to the element-plus imports (not needed if using auto-import, but add for safety):

```js
import { ElMessage } from "element-plus";
```

Wait — Element Plus is auto-imported in this project, so `ElMessage` should be available globally. But to be explicit, check: if `ElMessage` isn't already imported, add it.

- [ ] **Step 4: Add loading state to the button**

Change the login button from:

```html
<el-button type="primary" size="large" class="login-btn" native-type="button" @click="handleLogin">
  登录
</el-button>
```

to:

```html
<el-button type="primary" size="large" class="login-btn" native-type="button" :loading="loading" @click="handleLogin">
  登录
</el-button>
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/LoginPage.vue
git commit -m "feat: connect LoginPage to backend auth API"
```

---

### Task 11: Connect RegisterPage to backend API

**Files:**
- Modify: `frontend/src/views/RegisterPage.vue`

- [ ] **Step 1: Add API import**

Add after the existing imports in `<script setup>`:

```js
import request from "../utils/request.js";
import { ElMessage } from "element-plus";
```

- [ ] **Step 2: Rewrite handleRegister to call API**

Replace the `handleRegister` function (lines 151-159) with:

```js
const loading = ref(false);

const handleRegister = () => {
  registerFormRef.value.validate(async (valid) => {
    if (!valid) return;
    loading.value = true;
    try {
      await request.post("/auth/register", {
        username: registerForm.username,
        email: registerForm.email,
        password: registerForm.password,
      });
      ElMessage.success("注册成功，请登录");
      router.push("/login");
    } catch (error) {
      // error already handled by interceptor
    } finally {
      loading.value = false;
    }
  });
};
```

- [ ] **Step 3: Add loading state to button**

Change the register button from:

```html
<el-button type="primary" size="large" class="register-btn" @click="handleRegister">
  注册
</el-button>
```

to:

```html
<el-button type="primary" size="large" class="register-btn" :loading="loading" @click="handleRegister">
  注册
</el-button>
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/views/RegisterPage.vue
git commit -m "feat: connect RegisterPage to backend auth API"
```

---

### Task 12: Connect ForgotPasswordPage to backend API

**Files:**
- Modify: `frontend/src/views/ForgotPasswordPage.vue`

- [ ] **Step 1: Add API import**

Add after the existing imports in `<script setup>`:

```js
import request from "../utils/request.js";
```

- [ ] **Step 2: Rewrite handleSubmit to call API**

Replace the `handleSubmit` function (lines 64-73) with:

```js
const loading = ref(false);

const handleSubmit = () => {
  forgotFormRef.value.validate(async (valid) => {
    if (!valid) return;
    loading.value = true;
    try {
      const res = await request.post("/auth/forgot-password", {
        email: forgotForm.email,
      });
      ElMessage.success(res.message || "重置链接已发送到您的邮箱");
      setTimeout(() => {
        router.push("/login");
      }, 1500);
    } catch (error) {
      // error already handled by interceptor
    } finally {
      loading.value = false;
    }
  });
};
```

- [ ] **Step 3: Add loading state to button**

Change the submit button from:

```html
<el-button type="primary" size="large" class="submit-btn" @click="handleSubmit">
  发送重置链接
</el-button>
```

to:

```html
<el-button type="primary" size="large" class="submit-btn" :loading="loading" @click="handleSubmit">
  发送重置链接
</el-button>
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/views/ForgotPasswordPage.vue
git commit -m "feat: connect ForgotPasswordPage to backend auth API"
```

---

### Task 13: Update ProfilePage to show real user info

**Files:**
- Modify: `frontend/src/views/ProfilePage.vue`

- [ ] **Step 1: Read user info from localStorage**

In `<script setup>`, add:

```js
import { ref, onMounted } from "vue";

const user = ref({ username: "用户", email: "" });

onMounted(() => {
  const stored = localStorage.getItem("user");
  if (stored) {
    try {
      user.value = JSON.parse(stored);
    } catch {
      // keep defaults
    }
  }
});
```

- [ ] **Step 2: Update template to show real user info**

Change the hardcoded user name and role (lines 18-19) from:

```html
<div class="user-name">示例用户</div>
<div class="user-role">普通用户</div>
```

to:

```html
<div class="user-name">{{ user.username }}</div>
<div class="user-role">{{ user.email }}</div>
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/views/ProfilePage.vue
git commit -m "feat: show real user info in ProfilePage from login data"
```

---

### Task 14: End-to-end smoke test

- [ ] **Step 1: Start infrastructure**

```bash
cd /home/cwl/yaogan && docker-compose up -d postgres
```

Expected: PostgreSQL starts (or is already running)

- [ ] **Step 2: Start backend**

```bash
cd backend && source .venv/bin/activate && python main.py &
sleep 3
curl -s http://localhost:8000/health
```

Expected: `{"status":"healthy"}`

- [ ] **Step 3: Test register endpoint**

```bash
curl -s -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","email":"test@example.com","password":"pass123"}'
```

Expected: `{"success":true,"message":"注册成功"}`

- [ ] **Step 4: Test duplicate register**

```bash
curl -s -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","email":"test@example.com","password":"pass123"}'
```

Expected: 409 with "用户名已被注册"

- [ ] **Step 5: Test login endpoint**

```bash
curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"pass123"}'
```

Expected: JSON with `access_token`, `token_type`, `user` object

- [ ] **Step 6: Test login with wrong password**

```bash
curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"wrongpass"}'
```

Expected: 401 with "用户名或密码错误"

- [ ] **Step 7: Test forgot-password endpoint**

```bash
curl -s -X POST http://localhost:8000/api/auth/forgot-password \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com"}'
```

Expected: `{"success":true,"message":"密码重置链接已发送到您的邮箱（功能开发中）"}`

- [ ] **Step 8: Commit**

```bash
# All tests passed, no code changes to commit
```
