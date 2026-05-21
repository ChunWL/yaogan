"""Seed admin user into the database. Run once after first deploy."""
import sys
sys.path.insert(0, ".")

from app.utils.db import SessionLocal, engine, Base
from app.models.user import User
from app.utils.auth import hash_password

Base.metadata.create_all(bind=engine)

db = SessionLocal()
try:
    existing = db.query(User).filter(User.username == "admin").first()
    if existing:
        existing.is_admin = True
        existing.hashed_password = hash_password("admin123")
        db.commit()
        print("Admin user updated.")
    else:
        admin = User(
            username="admin",
            email="admin@yaogan.com",
            hashed_password=hash_password("admin123"),
            is_admin=True,
        )
        db.add(admin)
        db.commit()
        print(f"Admin user created: admin / admin123")
finally:
    db.close()
