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
