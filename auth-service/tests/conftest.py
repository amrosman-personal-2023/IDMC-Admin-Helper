"""
Shared test fixtures.
- in_memory_db: fresh async SQLite per test
- fake_clock: injectable datetime replacing clock.now()
- rfc6238_vectors: official RFC 6238 TOTP test vectors
- seeded: convenience factory that creates a vendor + device + admin in the DB
"""
import asyncio
import base64
import os
from datetime import datetime, timezone
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

# ── Set required env vars before any app import ───────────────────────────────
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization

_private_key = rsa.generate_private_key(
    public_exponent=65537, key_size=2048, backend=default_backend()
)
_private_pem = _private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.TraditionalOpenSSL,
    encryption_algorithm=serialization.NoEncryption(),
).decode()
_public_pem = _private_key.public_key().public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo,
).decode()

os.environ.setdefault("JWT_SIGNING_KEY", _private_pem)
os.environ.setdefault("JWT_PUBLIC_KEY", _public_pem)
os.environ.setdefault("ADMIN_API_KEY", "test-admin-api-key-32bytes-xxxxxxx")
os.environ.setdefault("ADMIN_SESSION_SECRET", "test-session-secret-32bytes-xxxxx")
os.environ.setdefault("DB_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("ENROLLMENT_LINK_BASE_URL", "http://testserver/enroll")

# ── Now safe to import app modules ────────────────────────────────────────────
from app import clock
from app.config import settings, load_required_settings
from app.database import Base
from app.main import app
from app.models import Admin, Device, EnrollmentToken, Vendor
from app.security import hash_password, generate_totp_seed, sha256_hex
from app.seed_crypto import encrypt_seed

load_required_settings()


# ── Fake clock ────────────────────────────────────────────────────────────────

class FakeClock:
    def __init__(self, initial: datetime):
        self._dt = initial

    @property
    def dt(self) -> datetime:
        return self._dt

    def advance(self, **kwargs) -> None:
        from datetime import timedelta
        self._dt = self._dt + timedelta(**kwargs)

    def __call__(self) -> datetime:
        return self._dt.replace(tzinfo=None)


@pytest.fixture
def fake_clock():
    fc = FakeClock(datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc))
    clock.set_provider(fc)
    yield fc
    clock.reset_provider()


# ── In-memory DB per test ─────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with factory() as session:
        yield session


# ── HTTP test client wired to the in-memory DB ────────────────────────────────

@pytest_asyncio.fixture
async def client(db_engine) -> AsyncGenerator[AsyncClient, None]:
    from app import database as db_module
    # Override the engine and session factory used by the app
    test_engine = db_engine
    test_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    db_module.engine = test_engine
    db_module.AsyncSessionLocal = test_factory

    async def override_get_db():
        async with test_factory() as session:
            yield session

    from app.database import get_db
    app.dependency_overrides[get_db] = override_get_db

    # follow_redirects=True and a shared cookie jar so Set-Cookie is persisted
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        follow_redirects=True,
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# ── Seed helpers ──────────────────────────────────────────────────────────────

async def _create_vendor(db_session, username="testvendor", password="pass123!",
                          role="vendor_standard") -> tuple:
    """Return (vendor, device, seed_b32, raw_enrollment_token)."""
    from datetime import timedelta
    from app.security import generate_secure_token
    now = clock.now().replace(tzinfo=None)

    vendor = Vendor(
        username=username,
        bcrypt_password_hash=hash_password(password),
        role=role,
        created_at=now,
        active=True,
    )
    db_session.add(vendor)
    await db_session.flush()

    seed_bytes = generate_totp_seed()
    seed_b32 = base64.b32encode(seed_bytes).decode()
    uuid = "device-uuid-test-1234"
    uuid_hash = sha256_hex(uuid)
    seed_enc = encrypt_seed(seed_b32)

    device = Device(
        vendor_id=vendor.id,
        uuid_hash=uuid_hash,
        totp_seed_hash=seed_enc,
        enrolled_at=now,
        revoked=False,
    )
    db_session.add(device)

    raw_token = generate_secure_token(32)
    token_hash = sha256_hex(raw_token)
    token_record = EnrollmentToken(
        token_hash=token_hash,
        vendor_id=vendor.id,
        expires_at=now + timedelta(hours=24),
        used=False,
    )
    db_session.add(token_record)
    await db_session.commit()
    return vendor, device, seed_b32, uuid, raw_token


async def _create_admin(db_session, username="testadmin", password="adminpass!") -> Admin:
    from datetime import timedelta
    now = clock.now().replace(tzinfo=None)
    admin = Admin(
        username=username,
        bcrypt_password_hash=hash_password(password),
        created_at=now,
        active=True,
    )
    db_session.add(admin)
    await db_session.commit()
    return admin


# ── RFC 6238 TOTP reference vectors ──────────────────────────────────────────
# Seed for SHA-1 vectors: "12345678901234567890"
_RFC6238_SEED_BYTES = b"12345678901234567890"
_RFC6238_SEED_B32 = base64.b32encode(_RFC6238_SEED_BYTES).decode()

RFC6238_VECTORS = [
    # (unix_timestamp, expected_6digit_code)
    (59,          "287082"),
    (1111111109,  "081804"),
    (1111111111,  "050471"),
    (1234567890,  "005924"),
    (2000000000,  "279037"),
    (20000000000, "353130"),
]


@pytest.fixture(params=RFC6238_VECTORS, ids=[f"ts={v[0]}" for v in RFC6238_VECTORS])
def rfc6238_vector(request):
    ts, expected = request.param
    return {"seed_b32": _RFC6238_SEED_B32, "timestamp": ts, "expected": expected}
