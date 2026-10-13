from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import load_required_settings
from app.database import engine
from app.models import Base
from app.routers import admin_auth, admin_mgmt, vendor_auth


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_required_settings()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title="IDMC Auth Service", lifespan=lifespan)

app.include_router(vendor_auth.router)
app.include_router(admin_auth.router)
app.include_router(admin_mgmt.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
