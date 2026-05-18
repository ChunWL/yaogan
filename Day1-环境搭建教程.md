# Day 1: 环境搭建 + YOLO11基础推理

> 学习目标：掌握项目初始化、Git版本控制、Docker部署、FastAPI框架搭建的完整流程

---

## 📋 今日任务清单

- [ ] Git与GitHub版本控制配置
- [ ] Docker Compose部署（PostgreSQL/Redis/MinIO）
- [ ] FastAPI后端框架初始化
- [ ] 虚拟环境配置与依赖安装
- [ ] 健康检查接口测试

---

## 一、Git与GitHub版本控制

### 1.1 安装Git（如未安装）

```bash
# macOS 使用 Homebrew 安装
brew install git

# 验证安装
git --version
```

### 1.2 配置Git用户信息

```bash
# 配置用户名
git config --global user.name "Your Name"

# 配置邮箱（使用GitHub注册邮箱）
git config --global user.email "your.email@example.com"

# 查看配置
git config --list
```

### 1.3 创建GitHub仓库

**步骤1**: 登录GitHub → New Repository

**仓库设置**:
- Repository name: `rsod-web-platform`
- Description: `遥感目标智能检测平台`
- Public/Private: 根据需求选择
- Initialize with: 勾选 `Add a README file`

**步骤2**: 复制仓库URL

```bash
# HTTPS方式（推荐）
https://github.com/your-username/rsod-web-platform.git

# SSH方式（需要配置SSH密钥）
git@github.com:your-username/rsod-web-platform.git
```

### 1.4 克隆仓库到本地

```bash
# 克隆仓库
git clone https://github.com/your-username/rsod-web-platform.git

# 进入项目目录
cd rsod-web-platform

# 查看仓库状态
git status
```

### 1.5 Git基础操作

```bash
# 查看当前分支
git branch

# 创建开发分支
git checkout -b feature/day1-setup

# 添加文件到暂存区
git add .

# 推送分支到远程
git push origin feature/day1-setup

# 提交修改
git commit -m "feat: 完成Day1环境搭建"

# 切换回主分支
git checkout main
```

### 1.6 .gitignore配置

创建 `.gitignore` 文件：

```gitignore
# Python虚拟环境
.venv/
__pycache__/
*.pyc
*.pyo
*.pyd

# 环境变量
.env
.env.local

# 数据文件
data/
uploads/
results/

# Docker数据
storage/

# 模型文件
models/*.pt

# IDE配置
.vscode/
.idea/
*.swp
*.swo

# 日志文件
*.log
```

---

## 二、Docker Compose部署

### 2.1 安装Docker（如未安装）

```bash
# macOS 使用 Homebrew 安装
brew install --cask docker

# 启动Docker Desktop
open /Applications/Docker.app

# 验证安装
docker --version
docker-compose --version
```

### 2.2 创建docker-compose.yml

```yaml
version: '3.8'

services:
  # PostgreSQL数据库
  postgres:
    image: postgres:15
    container_name: rsod-postgres
    ports:
      - "5432:5432"
    environment:
      POSTGRES_USER: rsod_user
      POSTGRES_PASSWORD: rsod_password
      POSTGRES_DB: rsod_db
    volumes:
      - ./storage/postgres/data:/var/lib/postgresql/data
      - ./storage/postgres/init:/docker-entrypoint-initdb.d
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U rsod_user -d rsod_db"]
      interval: 5s
      timeout: 5s
      retries: 5

  # Redis缓存
  redis:
    image: redis:7
    container_name: rsod-redis
    ports:
      - "6379:6379"
    volumes:
      - ./storage/redis/data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

  # MinIO对象存储
  minio:
    image: minio/minio:latest
    container_name: rsod-minio
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    volumes:
      - ./storage/minio/data:/data
      - ./storage/minio/config:/root/.minio
    command: server /data --console-address ":9001"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  postgres-data:
  redis-data:
  minio-data:
```

### 2.3 创建存储目录

```bash
# 创建目录结构
mkdir -p storage/postgres/data storage/postgres/init
mkdir -p storage/redis/data
mkdir -p storage/minio/data storage/minio/config
```

### 2.4 启动服务

```bash
# 启动所有服务（后台运行）
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 2.5 配置MinIO存储桶

**步骤1**: 访问MinIO控制台

```
http://localhost:9001
用户名: minioadmin
密码: minioadmin
```

**步骤2**: 创建存储桶

1. 点击 `Create Bucket`
2. Bucket Name: `rsod-bucket`
3. 点击 `Create Bucket`

---

## 三、FastAPI后端框架初始化

### 3.1 创建项目结构

```bash
# 创建后端目录
mkdir -p backend/app/api backend/app/models backend/app/services
mkdir -p backend/app/utils backend/models backend/data

# 创建空文件
touch backend/app/__init__.py
touch backend/app/api/__init__.py
touch backend/app/models/__init__.py
touch backend/app/services/__init__.py
touch backend/app/utils/__init__.py
```

### 3.2 创建main.py入口文件

```python
# 导入FastAPI框架核心类，用于创建Web应用
from fastapi import FastAPI
# 导入CORS中间件，处理跨域资源共享问题
from fastapi.middleware.cors import CORSMiddleware

# ==================== FastAPI应用实例化 ====================
# 创建FastAPI应用对象，配置API文档信息
# 参数说明：
# - title: API文档显示的标题
# - description: API文档的详细描述
# - version: API版本号，便于版本管理
app = FastAPI(
    title="遥感目标智能检测平台",
    description="基于YOLO11的遥感图像目标检测系统API，支持飞机、油罐、立交桥、操场等目标检测",
    version="1.0.0"
)

# ==================== CORS跨域中间件配置 ====================
# 配置跨域访问规则，允许前端应用访问后端API
# 参数说明：
# - allow_origins: 允许访问的源地址列表，["*"]表示允许所有来源（生产环境需限制）
# - allow_credentials: 是否允许携带身份凭证（如Cookie、Token）
# - allow_methods: 允许的HTTP方法（GET、POST、PUT、DELETE等）
# - allow_headers: 允许的请求头字段
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # 开发环境允许所有来源，生产环境应指定具体域名
    allow_credentials=True,       # 启用凭证支持
    allow_methods=["*"],          # 允许所有HTTP方法
    allow_headers=["*"],          # 允许所有请求头
)

# ==================== API接口定义 ====================

# 健康检查接口 - GET请求
# @app.get装饰器定义GET请求接口
# tags参数用于在Swagger文档中分组显示
@app.get("/health", tags=["健康检查"])
async def health_check():
    """
    健康检查接口
    用于检测服务运行状态，支持负载均衡器健康检查
    
    返回值说明：
    - status: 服务状态（healthy表示正常）
    - service: 服务名称标识
    - version: 当前服务版本号
    """
    return {
        "status": "healthy",           # 服务健康状态
        "service": "rsod-web-platform", # 服务名称
        "version": "1.0.0"             # 服务版本
    }

# 根路径接口 - GET请求
@app.get("/", tags=["根路径"])
async def root():
    """
    根路径欢迎接口
    返回平台欢迎信息
    """
    return {"message": "欢迎使用遥感目标智能检测平台"}

# ==================== 应用启动入口 ====================
# 判断是否直接运行本文件（而非被导入）
if __name__ == "__main__":
    # 导入UVicorn ASGI服务器
    import uvicorn
    # 启动Web服务
    # 参数说明：
    # - app: FastAPI应用对象
    # - host: 监听地址，0.0.0.0表示监听所有网络接口
    # - port: 服务端口号
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### 3.3 创建配置文件

```python
# backend/app/config.py
import os
from pydantic import BaseModel

class Settings(BaseModel):
    """应用配置类"""
    
    # 应用基本信息
    app_name: str = os.getenv("APP_NAME", "RSOD Detection Platform")
    app_version: str = os.getenv("APP_VERSION", "1.0.0")
    debug: bool = os.getenv("DEBUG", "true").lower() in ("true", "1", "yes")
    
    # PostgreSQL配置
    db_host: str = os.getenv("DB_HOST", "localhost")
    db_port: int = int(os.getenv("DB_PORT", "5432"))
    db_user: str = os.getenv("DB_USER", "rsod_user")
    db_password: str = os.getenv("DB_PASSWORD", "rsod_password")
    db_name: str = os.getenv("DB_NAME", "rsod_db")
    
    # Redis配置
    redis_host: str = os.getenv("REDIS_HOST", "localhost")
    redis_port: int = int(os.getenv("REDIS_PORT", "6379"))
    redis_password: str = os.getenv("REDIS_PASSWORD", "")
    
    # MinIO配置
    minio_endpoint: str = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    minio_access_key: str = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    minio_secret_key: str = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    minio_bucket: str = os.getenv("MINIO_BUCKET", "rsod-bucket")
    minio_secure: bool = os.getenv("MINIO_SECURE", "false").lower() in ("true", "1", "yes")
    
    # YOLO模型配置
    yolo_model_path: str = os.getenv("YOLO_MODEL_PATH", "models/yolo11n.pt")
    confidence_threshold: float = float(os.getenv("CONFIDENCE_THRESHOLD", "0.5"))
    iou_threshold: float = float(os.getenv("IOU_THRESHOLD", "0.45"))
    
    # 文件存储配置
    upload_dir: str = os.getenv("UPLOAD_DIR", "uploads")
    result_dir: str = os.getenv("RESULT_DIR", "results")
    
    # CORS配置
    cors_origins: list = ["*"]

# 实例化配置对象
settings = Settings()
```

### 3.4 创建.env环境变量文件

```bash
# =============================================================================
# 应用基本配置
# =============================================================================
# 应用名称，显示在API文档和日志中
APP_NAME=RSOD Detection Platform
# 应用版本号，用于版本管理和API文档显示
APP_VERSION=1.0.0
# 调试模式开关（true/false），开发环境设为true，生产环境设为false
DEBUG=true

# =============================================================================
# PostgreSQL数据库配置
# 数据库连接信息，需与docker-compose.yml中的配置保持一致
# =============================================================================
# 数据库主机地址（Docker环境下使用容器名称，本地环境使用localhost）
DB_HOST=localhost
# 数据库端口号（PostgreSQL默认端口5432）
DB_PORT=5432
# 数据库用户名（与docker-compose.yml中POSTGRES_USER一致）
DB_USER=rsod_user
# 数据库密码（与docker-compose.yml中POSTGRES_PASSWORD一致）
DB_PASSWORD=rsod_password
# 数据库名称（与docker-compose.yml中POSTGRES_DB一致）
DB_NAME=rsod_db

# =============================================================================
# Redis缓存配置
# 用于会话管理、缓存热点数据等
# =============================================================================
# Redis主机地址
REDIS_HOST=localhost
# Redis端口号（默认6379）
REDIS_PORT=6379
# Redis密码（默认为空，生产环境建议设置密码）
REDIS_PASSWORD=

# =============================================================================
# MinIO对象存储配置
# 用于存储上传的图片、检测结果等非结构化数据
# =============================================================================
# MinIO服务端点（主机:端口）
MINIO_ENDPOINT=localhost:9000
# MinIO访问密钥（与docker-compose.yml中MINIO_ROOT_USER一致）
MINIO_ACCESS_KEY=minioadmin
# MinIO秘密密钥（与docker-compose.yml中MINIO_ROOT_PASSWORD一致）
MINIO_SECRET_KEY=minioadmin
# 默认存储桶名称（需提前在MinIO控制台创建）
MINIO_BUCKET=rsod-bucket
# 是否使用HTTPS（开发环境设为false，生产环境建议设为true）
MINIO_SECURE=false

# =============================================================================
# YOLO目标检测模型配置
# =============================================================================
# YOLO模型文件路径（相对于backend目录）
YOLO_MODEL_PATH=models/yolo11n.pt
# 置信度阈值（0.0-1.0），低于此值的检测结果将被过滤
CONFIDENCE_THRESHOLD=0.5
# IOU阈值（0.0-1.0），用于非极大值抑制算法
IOU_THRESHOLD=0.45

# =============================================================================
# 文件存储配置
# 本地临时存储目录，用于处理上传文件和生成结果
# =============================================================================
# 上传文件临时存储目录
UPLOAD_DIR=uploads
# 检测结果存储目录
RESULT_DIR=results
```

---

## 四、虚拟环境配置与依赖安装

### 4.1 创建虚拟环境

```bash
cd backend

# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境
# macOS/Linux
source .venv/bin/activate

# Windows
# .venv\Scripts\activate
```

### 4.2 创建requirements.txt

```bash
# =============================================================================
# FastAPI Web框架
# =============================================================================
# Web应用核心框架，提供异步API路由、请求验证等
fastapi>=0.104.0

# ASGI服务器，用于运行FastAPI应用
uvicorn[standard]>=0.24.0

# 文件上传支持，FastAPI处理multipart/form-data必需
python-multipart>=0.0.6

# 数据验证和配置管理
pydantic>=2.5.0
pydantic-settings>=2.1.0

# =============================================================================
# 数据库
# =============================================================================
# SQLAlchemy ORM框架
sqlalchemy>=2.0.0

# PostgreSQL数据库驱动
psycopg2-binary>=2.9.0

# =============================================================================
# Redis缓存
# =============================================================================
# Redis Python客户端
redis>=5.0.0

# =============================================================================
# MinIO对象存储
# =============================================================================
# MinIO Python SDK（S3兼容的对象存储）
minio>=7.2.0

# =============================================================================
# YOLO目标检测与图像处理
# =============================================================================
# Ultralytics YOLO框架（包含PyTorch）
ultralytics>=8.0.0

# OpenCV图像处理库
opencv-python>=4.8.0

# Pillow图像处理库
pillow>=10.0.0

# =============================================================================
# 工具库
# =============================================================================
# 环境变量加载
python-dotenv>=1.0.0

# NumPy数值计算（ultralytics自动安装，此处指定版本范围）
numpy>=1.23.0,<2.0.0
```

### 4.3 安装依赖

```bash
# 进入项目后端目录
cd backend

# 安装所有依赖
pip install -r requirements.txt

# 验证安装
pip list
```

---

## 五、启动后端服务

### 5.1 启动开发服务器

```bash
cd backend

# 方式1: 使用uvicorn直接启动
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 方式2: 使用python启动
python main.py
```

### 5.2 访问API文档

```
# Swagger UI
http://localhost:8000/docs
```

### 5.3 测试健康检查接口

```bash
# 使用curl测试
curl http://localhost:8000/health

# 预期输出
{
  "status": "healthy",
  "service": "rsod-web-platform",
  "version": "1.0.0"
}
```

---

## 六、今日总结

### ✅ 已完成任务

1. **Git版本控制**: 配置Git、创建GitHub仓库、克隆项目
2. **Docker部署**: 部署PostgreSQL、Redis、MinIO服务
3. **FastAPI框架**: 创建项目结构、配置文件、入口文件
4. **虚拟环境**: 配置虚拟环境、安装依赖
5. **服务测试**: 启动服务、测试健康检查接口

### 📁 项目结构

```
rsod-web-platform/
├── docker-compose.yml             # Docker Compose配置
├── backend/                       # 后端代码目录
│   ├── app/                        # 应用核心模块
│   │   ├── __init__.py
│   │   ├── api/                     # API路由层
│   │   ├── models/                  # 数据模型层
│   │   ├── services/                # 业务逻辑层
│   │   ├── utils/                   # 工具函数层
│   │   └── config.py                # 配置管理
│   ├── models/                      # 模型文件目录
│   ├── data/                        # 数据存储目录
│   ├── .venv/                       # Python虚拟环境
│   ├── main.py                      # FastAPI应用入口
│   └── requirements.txt             # Python依赖列表
│   └── .env                     # 环境变量配置  
│   └── .env.example             # 环境变量配置示例
└── storage/                     # 持久化存储目录 
    ├── postgres/                # PostgreSQL数据库
    ├── redis/                   # Redis缓存数据
    └── minio/                   # MinIO对象存储数据
```

### 🎯 明日任务

- 单图检测API开发
- YOLO模型集成
- 前端模板对接
- 检测结果展示
