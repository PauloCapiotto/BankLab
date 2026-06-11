import os

os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://banklab:banklab@localhost:5432/banklab_test",
)
os.environ["TESTING"] = "1"
os.environ["REDIS_URL"] = "redis://localhost:6399/0"

import uuid
from decimal import Decimal

import httpx
import pytest

from app import models
from app.core.database import Base, SessionLocal, engine
from app.core.security import create_access_token, hash_password
from app.main import app


@pytest.fixture(autouse=True)
async def db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest.fixture
async def session():
    async with SessionLocal() as s:
        yield s


@pytest.fixture
async def client():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def create_user(
    session,
    *,
    name="Maria Silva",
    email="maria@banklab.local",
    password="BankLab@123",
    status="active",
):
    user = models.User(
        name=name, email=email, password_hash=hash_password(password), status=status
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def create_account(
    session,
    user,
    *,
    branch="0001",
    number=None,
    balance=Decimal("1000.00"),
    status="active",
    type="checking",
):
    account = models.Account(
        user_id=user.id,
        branch=branch,
        number=number or uuid.uuid4().hex[:8],
        type=type,
        balance=balance,
        status=status,
    )
    session.add(account)
    await session.commit()
    await session.refresh(account)
    return account


def auth_headers(user) -> dict:
    return {"Authorization": f"Bearer {create_access_token(str(user.id))}"}
