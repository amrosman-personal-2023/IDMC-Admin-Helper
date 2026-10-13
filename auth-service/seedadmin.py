# seed_admin.py  (run once, then delete)
import asyncio, bcrypt
from app.database import AsyncSessionLocal, engine
from app.models import Base, Admin
from datetime import datetime, timezone

async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSessionLocal() as db:
        db.add(Admin(
            username="sysadmin",
            bcrypt_password_hash=bcrypt.hashpw(b"changeme!", bcrypt.gensalt(12)).decode(),
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
            active=True,
        ))
        await db.commit()

asyncio.run(main())