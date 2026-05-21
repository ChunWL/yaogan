from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
from app.config import settings
from app.api.detection import router as detection_router
from app.api.auth import router as auth_router
from app.api.admin import router as admin_router
from app.utils.db import engine, Base
from app.utils.file_utils import ensure_directories
from app.models.detection import DetectionRecord

ensure_directories()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="遥感目标检测平台后端API",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static/videos", StaticFiles(directory=settings.VIDEO_RESULT_DIR), name="videos")
app.mount("/static", StaticFiles(directory=settings.STATIC_DIR), name="static")

FRONTEND_DIST = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "dist")
if os.path.isdir(FRONTEND_DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="assets")

app.include_router(detection_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(admin_router, prefix="/api")


@app.get("/api/models/list")
async def get_models_list():
    from app.services.detection_service import detection_service as ds
    models = ds.get_available_models()
    if not models:
        models = ["yolo11n", "gt"]
    return {"success": True, "data": models}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if os.path.isdir(FRONTEND_DIST):
    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str, request: Request):
        file_path = os.path.join(FRONTEND_DIST, full_path) if full_path else None
        if file_path and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))

    @app.get("/")
    async def root():
        return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))


if __name__ == "__main__":
    import faulthandler
    import signal
    import sys
    faulthandler.enable()
    faulthandler.register(signal.SIGUSR1)

    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=False,
    )