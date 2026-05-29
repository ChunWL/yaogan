from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
from app.config import settings
from app.api.detection import router as detection_router
from app.api.auth import router as auth_router
from app.api.admin import router as admin_router
from app.api.scenes import router as scenes_router
from app.api.announcements import router as announcements_router
from sqlalchemy import inspect
from sqlalchemy import text as sa_text
from sqlalchemy.orm import Session
from app.utils.db import engine, Base, get_db
from app.utils.file_utils import ensure_directories
from app.utils.s3_client import ensure_buckets, get_file_response
from app.utils.auth import get_current_user, hash_password
from app.models.detection import DetectionRecord
from app.models.scene_group import SceneGroup
from app.models.user_scene_group_mapping import UserSceneGroupMapping
from app.models.announcement import Announcement
from app.models.password_reset import PasswordResetToken


ensure_directories()


def _run_migrations():
    """Add new columns to existing tables without dropping data."""
    inspector = inspect(engine)
    detection_columns = [c["name"] for c in inspector.get_columns("detection_records")]
    if "scene" not in detection_columns:
        with engine.begin() as conn:
            conn.execute(sa_text("ALTER TABLE detection_records ADD COLUMN scene VARCHAR(50) DEFAULT 'steel'"))
            conn.execute(sa_text("CREATE INDEX ix_detection_records_scene ON detection_records (scene)"))

    # 检查 custom_scenes 表是否存在再迁移
    table_names = inspector.get_table_names()
    if "custom_scenes" in table_names:
        custom_columns = [c["name"] for c in inspector.get_columns("custom_scenes")]
        if "original_model_name" not in custom_columns:
            with engine.begin() as conn:
                conn.execute(sa_text("ALTER TABLE custom_scenes ADD COLUMN original_model_name VARCHAR(255)"))
        if "group_id" not in custom_columns:
            with engine.begin() as conn:
                conn.execute(sa_text("ALTER TABLE custom_scenes ADD COLUMN group_id UUID REFERENCES scene_groups(id)"))
                conn.execute(sa_text("CREATE INDEX ix_custom_scenes_group_id ON custom_scenes (group_id)"))
        if "description" not in custom_columns:
            with engine.begin() as conn:
                conn.execute(sa_text("ALTER TABLE custom_scenes ADD COLUMN description VARCHAR(500) DEFAULT ''"))
        if "status" not in custom_columns:
            with engine.begin() as conn:
                conn.execute(sa_text("ALTER TABLE custom_scenes ADD COLUMN status VARCHAR(20) DEFAULT 'active' NOT NULL"))
        if "precision" not in custom_columns:
            with engine.begin() as conn:
                conn.execute(sa_text("ALTER TABLE custom_scenes ADD COLUMN precision FLOAT"))
                conn.execute(sa_text("ALTER TABLE custom_scenes ADD COLUMN recall FLOAT"))
                conn.execute(sa_text("ALTER TABLE custom_scenes ADD COLUMN map50 FLOAT"))
                conn.execute(sa_text("ALTER TABLE custom_scenes ADD COLUMN map50_95 FLOAT"))

        # After all other custom_scenes migrations, check and drop NOT NULL on user_id
        with engine.begin() as conn:
            result = conn.execute(
                sa_text("SELECT is_nullable FROM information_schema.columns WHERE table_name='custom_scenes' AND column_name='user_id'")
            ).scalar()
            if result == "NO":
                conn.execute(sa_text("ALTER TABLE custom_scenes ALTER COLUMN user_id DROP NOT NULL"))

    # 检查 announcements 表并迁移
    if "announcements" in table_names:
        ann_columns = [c["name"] for c in inspector.get_columns("announcements")]
        if "title" not in ann_columns:
            with engine.begin() as conn:
                conn.execute(sa_text("ALTER TABLE announcements ADD COLUMN title VARCHAR(200)"))
        # model_name currently nullable=False, make nullable
        # Only run if we need to; safe to run multiple times
        with engine.begin() as conn:
            conn.execute(sa_text("ALTER TABLE announcements ALTER COLUMN model_name DROP NOT NULL"))

    # Add avatar_url column to users table
    user_columns = [c["name"] for c in inspector.get_columns("users")]
    if "avatar_url" not in user_columns:
        with engine.begin() as conn:
            conn.execute(sa_text("ALTER TABLE users ADD COLUMN avatar_url VARCHAR(255) DEFAULT NULL"))


def _seed_admin():
    """Create default admin user on first startup."""
    from app.models.user import User
    from app.utils.db import SessionLocal
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == "admin").first()
        if existing:
            existing.is_admin = True
            db.commit()
        else:
            admin = User(
                username="admin",
                email="admin@yaogan.com",
                hashed_password=hash_password("admin123"),
                is_admin=True,
            )
            db.add(admin)
            db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    _run_migrations()
    _seed_admin()
    ensure_buckets()
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


@app.get("/api/files/{bucket}/{filename:path}")
async def serve_file(bucket: str, filename: str, download: str = ""):
    return get_file_response(bucket, filename, download=download.lower() == "1")


app.include_router(detection_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(admin_router, prefix="/api")
app.include_router(scenes_router, prefix="/api")
app.include_router(announcements_router, prefix="/api")


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
