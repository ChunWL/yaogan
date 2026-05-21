import os
import uuid
import shutil
from app.config import settings


def ensure_directories():
    os.makedirs(settings.STATIC_DIR, exist_ok=True)
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs(settings.RESULT_DIR, exist_ok=True)
    os.makedirs(settings.VIDEO_RESULT_DIR, exist_ok=True)


def get_file_url(filename: str, directory: str) -> str:
    return f"/{directory}/{filename}"


async def save_upload_file(file, upload_dir: str) -> str:
    ext = os.path.splitext(file.filename)[1] or ".jpg"
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(upload_dir, filename)
    with open(filepath, "wb") as f:
        f.write(await file.read())
    return filename
