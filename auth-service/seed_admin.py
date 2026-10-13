"""
Run once to create the first admin account.
Usage:
    cd auth-service
    source .venv/bin/activate
    python seed_admin.py
    python seed_admin.py --username alice --password s3cr3t!
"""
import asyncio
import argparse
import os
import sys

# ── Require env vars before importing app modules ─────────────────────────────
os.environ.setdefault("JWT_SIGNING_KEY",        os.environ.get("JWT_SIGNING_KEY", "placeholder"))
os.environ.setdefault("JWT_PUBLIC_KEY",         os.environ.get("JWT_PUBLIC_KEY", "placeholder"))
os.environ.setdefault("ADMIN_API_KEY",          os.environ.get("ADMIN_API_KEY", "placeholder"))
os.environ.setdefault("ADMIN_SESSION_SECRET",   os.environ.get("ADMIN_SESSION_SECRET", "placeholder"))
os.environ.setdefault("DB_URL",                 os.environ.get("DB_URL", "sqlite+aiosqlite:///./dev.db"))

from datetime import datetime, timezone
from sqlalchemy import select
from app.database import AsyncSessionLocal, engine
from app.models import Base, Admin
from app.security import hash_password


async def seed(username: str, password: str) -> None:
    # Create tables if they don't exist yet
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Admin).where(Admin.username == username))
        existing = result.scalar_one_or_none()
        if existing:
            print(f"Admin '{username}' already exists (id={existing.id}). Nothing changed.")
            return

        admin = Admin(
            username=username,
            bcrypt_password_hash=hash_password(password),
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
            active=True,
        )
        db.add(admin)
        await db.commit()
        await db.refresh(admin)
        print(f"Created admin account:  username={username}  id={admin.id}")
        print("Login at: http://localhost:5173/admin/login")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed the first admin account")
    parser.add_argument("--username", default="sysadmin")
    parser.add_argument("--password", default="changeme!")
    args = parser.parse_args()

    if args.password == "changeme!":
        print("WARNING: using default password 'changeme!' — change it after first login.")

    asyncio.run(seed(args.username, args.password))
