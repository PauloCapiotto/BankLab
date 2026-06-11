# BankLab Fase 2 — Backend E Dados: Plano De Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar todo o backend do BankLab: modelos, migrations, seed, autenticação JWT, contas, depósitos e transferências idempotentes, extrato com filtros, resumo, notificações, auditoria e worker de eventos via Redis Streams.

**Architecture:** FastAPI com SQLAlchemy 2.0 async + asyncpg sobre PostgreSQL. Regras financeiras 100% no backend, com `Decimal`, transações atômicas (locks `FOR UPDATE`) e idempotência via constraint única `(idempotency_key, type)`. Operações financeiras publicam eventos JSON no stream `banklab.transactions`; um worker com consumer group consome e persiste notificações com deduplicação por `dedup_key` único.

**Tech Stack:** FastAPI, Pydantic v2, SQLAlchemy 2.0 async, Alembic, PyJWT, bcrypt, redis-py asyncio, pytest + pytest-asyncio + httpx.

**Pré-requisito:** Fase 1 concluída (`docs/superpowers/plans/2026-06-10-banklab-fase-1-fundacao.md`). Docker Compose com postgres/redis rodando (`docker compose up -d postgres redis`) — os testes de integração usam o banco `banklab_test` criado pelo init script.

**Regras de commit (obrigatórias, do CLAUDE.md):** Conventional Commits em português. NUNCA adicionar `Co-Authored-By: Claude`, "Generated with Claude" ou qualquer referência à Anthropic.

**Convenções deste plano:**
- Todos os comandos de teste rodam de `apps/api` com `.venv/bin/pytest`.
- Valores monetários trafegam no JSON como **string com 2 casas** (ex.: `"6250.00"`), preservando precisão decimal — alinhado aos eventos da spec, que usam `"1500.00"`. Os schemas de resposta usam `str` e o helper `money_str`.
- Erros seguem sempre o formato `{"code", "message", "details"}`.

**Decisões de implementação registradas (justificativas, não requisitos novos):**
1. `transactions` ganha constraint única `(idempotency_key, type)` — implementa "único por usuário/operação" da spec; transferência usa a mesma chave nas duas pernas (`transfer_out`/`transfer_in`).
2. `notifications` ganha coluna `dedup_key varchar unique nullable` — mecanismo necessário para o critério RF08 "reprocessamento do mesmo evento não cria notificação duplicada".
3. Na retentativa idempotente, `new_balance` retorna o saldo atual da conta (a garantia central — não duplicar débito/crédito — é preservada; não há cache de resposta na v1, por simplicidade).

---

### Task 1: Núcleo — erros padronizados, segurança e publicação de eventos

**Files:**
- Create: `apps/api/app/core/errors.py`
- Create: `apps/api/app/core/security.py`
- Create: `apps/api/app/core/database.py`
- Create: `apps/api/app/core/events.py`
- Modify: `apps/api/app/main.py`
- Test: `apps/api/tests/test_security.py`

- [ ] **Step 1: Escrever testes de segurança (falham — módulo não existe)**

`apps/api/tests/test_security.py`:

```python
import jwt as pyjwt
import pytest

from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_e_verificacao_de_senha():
    h = hash_password("BankLab@123")
    assert h != "BankLab@123"
    assert verify_password("BankLab@123", h) is True


def test_senha_incorreta_nao_verifica():
    h = hash_password("BankLab@123")
    assert verify_password("senha-errada", h) is False


def test_token_valido_decodifica_com_sub():
    token = create_access_token("user-id-123")
    payload = decode_access_token(token)
    assert payload["sub"] == "user-id-123"
    assert "exp" in payload


def test_token_expirado_lanca_excecao():
    token = create_access_token("user-id-123", expires_in_minutes=-1)
    with pytest.raises(pyjwt.ExpiredSignatureError):
        decode_access_token(token)
```

- [ ] **Step 2: Rodar e confirmar falha**

Run: `cd apps/api && .venv/bin/pytest tests/test_security.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'app.core.security'`

- [ ] **Step 3: Criar `apps/api/app/core/security.py`**

```python
import datetime as dt

import bcrypt
import jwt

from app.core.config import settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def create_access_token(user_id: str, expires_in_minutes: int | None = None) -> str:
    minutes = (
        expires_in_minutes
        if expires_in_minutes is not None
        else settings.jwt_expires_in_minutes
    )
    now = dt.datetime.now(dt.timezone.utc)
    payload = {"sub": user_id, "iat": now, "exp": now + dt.timedelta(minutes=minutes)}
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
```

- [ ] **Step 4: Rodar testes de segurança**

Run: `.venv/bin/pytest tests/test_security.py -v`
Expected: `4 passed`

- [ ] **Step 5: Criar `apps/api/app/core/errors.py`**

```python
class APIError(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: dict | None = None,
    ):
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or {}
```

- [ ] **Step 6: Criar `apps/api/app/core/database.py`**

`NullPool` em modo de teste evita conexões asyncpg presas a event loops encerrados pelo pytest-asyncio:

```python
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.core.config import settings


class Base(DeclarativeBase):
    pass


engine_kwargs = {"poolclass": NullPool} if settings.testing else {}
engine = create_async_engine(settings.database_url, **engine_kwargs)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session():
    async with SessionLocal() as session:
        yield session
```

- [ ] **Step 7: Criar `apps/api/app/core/events.py`**

Falha de publicação não pode desfazer a operação financeira já persistida — só loga:

```python
import json
import logging

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)

STREAM = "banklab.transactions"


async def publish_event(event: dict) -> None:
    try:
        client = aioredis.from_url(settings.redis_url, decode_responses=True)
        try:
            await client.xadd(STREAM, {"data": json.dumps(event)})
        finally:
            await client.aclose()
    except Exception:
        logger.exception(
            "Falha ao publicar evento no Redis: %s", event.get("event_type")
        )
```

- [ ] **Step 8: Registrar handlers de erro em `apps/api/app/main.py`**

Substituir o conteúdo por:

```python
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.errors import APIError

app = FastAPI(title="BankLab API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(APIError)
async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.code, "message": exc.message, "details": exc.details},
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    errors = [
        {"field": ".".join(str(part) for part in e["loc"]), "message": e["msg"]}
        for e in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={
            "code": "VALIDATION_ERROR",
            "message": "Dados inválidos. Verifique os campos e tente novamente.",
            "details": {"errors": errors},
        },
    )


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
```

- [ ] **Step 9: Rodar toda a suíte**

Run: `.venv/bin/pytest -v`
Expected: `5 passed` (health + 4 de segurança)

- [ ] **Step 10: Commit**

```bash
git add apps/api
git commit -m "feat: adiciona nucleo do backend com seguranca, erros e eventos"
```

---

### Task 2: Modelos, migração inicial e migrations no boot do container

**Files:**
- Create: `apps/api/app/models.py`
- Create: `apps/api/alembic.ini`
- Create: `apps/api/alembic/` (via `alembic init`, com `env.py` substituído)
- Modify: `apps/api/Dockerfile`

- [ ] **Step 1: Criar `apps/api/app/models.py`**

```python
import datetime as dt
import uuid
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    branch: Mapped[str] = mapped_column(String(10))
    number: Mapped[str] = mapped_column(String(20), unique=True)
    type: Mapped[str] = mapped_column(String(20), default="checking")
    balance: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        UniqueConstraint(
            "idempotency_key", "type", name="uq_transactions_idempotency_key_type"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("accounts.id"), index=True
    )
    related_account_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("accounts.id"), nullable=True
    )
    type: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="completed")
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    completed_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    type: Mapped[str] = mapped_column(String(20), default="transaction")
    title: Mapped[str] = mapped_column(String(120))
    message: Mapped[str] = mapped_column(Text)
    dedup_key: Mapped[str | None] = mapped_column(
        String(255), unique=True, nullable=True
    )
    read_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(100))
    entity_type: Mapped[str] = mapped_column(String(50))
    entity_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    meta: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
```

(O atributo Python chama-se `meta` porque `metadata` é reservado pelo SQLAlchemy Declarative; a coluna no banco chama-se `metadata` como na spec.)

- [ ] **Step 2: Inicializar Alembic com template async**

```bash
cd apps/api
.venv/bin/alembic init -t async alembic
```

- [ ] **Step 3: Substituir `apps/api/alembic/env.py` por completo**

```python
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app import models  # noqa: F401  (registra as tabelas no metadata)
from app.core.config import settings
from app.core.database import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", settings.database_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 4: Gerar a migração inicial por autogenerate (postgres do compose deve estar de pé)**

```bash
DATABASE_URL=postgresql+asyncpg://banklab:banklab@localhost:5432/banklab \
  .venv/bin/alembic revision --autogenerate -m "cria tabelas iniciais"
```

Abrir o arquivo gerado em `alembic/versions/` e conferir que cria as 5 tabelas (`users`, `accounts`, `transactions`, `notifications`, `audit_logs`), a unique `uq_transactions_idempotency_key_type` e a unique de `notifications.dedup_key`.

- [ ] **Step 5: Aplicar a migração**

```bash
DATABASE_URL=postgresql+asyncpg://banklab:banklab@localhost:5432/banklab \
  .venv/bin/alembic upgrade head
```

Run: `docker compose exec postgres psql -U banklab -d banklab -c '\dt'`
Expected: as 5 tabelas + `alembic_version`.

- [ ] **Step 6: Atualizar `apps/api/Dockerfile` para rodar migrations no boot**

Substituir por:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml alembic.ini ./
COPY app ./app
COPY alembic ./alembic

RUN pip install --no-cache-dir .

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
```

- [ ] **Step 7: Verificar que o container ainda sobe**

```bash
docker compose up -d --build api
docker compose logs api | tail -5
curl -s http://localhost:8000/health
```

Expected: log mostra alembic rodando sem erro; health responde `{"status":"ok"}`.

- [ ] **Step 8: Commit**

```bash
git add apps/api
git commit -m "feat: adiciona modelos do banco e migracao inicial com alembic"
```

---

### Task 3: Harness de testes de integração

**Files:**
- Create: `apps/api/tests/conftest.py`

- [ ] **Step 1: Criar `apps/api/tests/conftest.py`**

As variáveis de ambiente são definidas ANTES de importar qualquer módulo de `app`, para o engine apontar para `banklab_test`:

```python
import os

os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://banklab:banklab@localhost:5432/banklab_test",
)
os.environ["TESTING"] = "1"

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
```

- [ ] **Step 2: Verificar que o harness funciona com a suíte existente**

Run: `.venv/bin/pytest -v`
Expected: `5 passed` (sem erros de conexão — exige `docker compose up -d postgres`).

- [ ] **Step 3: Commit**

```bash
git add apps/api/tests/conftest.py
git commit -m "test: adiciona harness de testes de integracao com banco de teste"
```

---

### Task 4: Autenticação — login, `/auth/me` e auditoria de login

**Files:**
- Create: `apps/api/app/modules/__init__.py`
- Create: `apps/api/app/modules/audit/__init__.py`
- Create: `apps/api/app/modules/audit/service.py`
- Create: `apps/api/app/modules/auth/__init__.py`
- Create: `apps/api/app/modules/auth/schemas.py`
- Create: `apps/api/app/modules/auth/deps.py`
- Create: `apps/api/app/modules/auth/router.py`
- Modify: `apps/api/app/main.py`
- Test: `apps/api/tests/test_auth.py`

- [ ] **Step 1: Escrever testes (falham)**

`apps/api/tests/test_auth.py`:

```python
from sqlalchemy import select

from app import models
from app.core.security import create_access_token
from tests.conftest import auth_headers, create_user


async def test_login_valido_retorna_token_e_usuario(client, session):
    user = await create_user(session)
    response = await client.post(
        "/auth/login",
        json={"email": "maria@banklab.local", "password": "BankLab@123"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 3600
    assert body["access_token"]
    assert body["user"]["email"] == "maria@banklab.local"
    assert body["user"]["name"] == "Maria Silva"


async def test_login_valido_gera_log_de_auditoria(client, session):
    user = await create_user(session)
    await client.post(
        "/auth/login",
        json={"email": "maria@banklab.local", "password": "BankLab@123"},
    )
    result = await session.execute(
        select(models.AuditLog).where(models.AuditLog.action == "auth.login")
    )
    log = result.scalar_one()
    assert log.actor_user_id == user.id
    assert log.entity_type == "user"


async def test_login_com_senha_errada_retorna_401(client, session):
    await create_user(session)
    response = await client.post(
        "/auth/login",
        json={"email": "maria@banklab.local", "password": "errada"},
    )
    assert response.status_code == 401
    assert response.json()["code"] == "INVALID_CREDENTIALS"


async def test_login_de_usuario_inativo_retorna_401(client, session):
    await create_user(session, status="inactive")
    response = await client.post(
        "/auth/login",
        json={"email": "maria@banklab.local", "password": "BankLab@123"},
    )
    assert response.status_code == 401


async def test_me_retorna_usuario_autenticado(client, session):
    user = await create_user(session)
    response = await client.get("/auth/me", headers=auth_headers(user))
    assert response.status_code == 200
    assert response.json()["email"] == "maria@banklab.local"


async def test_rota_protegida_sem_token_retorna_401(client):
    response = await client.get("/auth/me")
    assert response.status_code == 401
    assert response.json()["code"] == "NOT_AUTHENTICATED"


async def test_token_expirado_retorna_401(client, session):
    user = await create_user(session)
    token = create_access_token(str(user.id), expires_in_minutes=-1)
    response = await client.get(
        "/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401
    assert response.json()["code"] == "TOKEN_EXPIRED"
```

- [ ] **Step 2: Rodar e confirmar falha**

Run: `.venv/bin/pytest tests/test_auth.py -v`
Expected: FAIL (rotas não existem; asserts de status recebem 404).

- [ ] **Step 3: Criar pacotes e o serviço de auditoria**

`apps/api/app/modules/__init__.py`, `apps/api/app/modules/audit/__init__.py` e `apps/api/app/modules/auth/__init__.py` vazios.

`apps/api/app/modules/audit/service.py`:

```python
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app import models


async def record_audit(
    session: AsyncSession,
    *,
    actor_user_id: uuid.UUID | None,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID | None = None,
    metadata: dict | None = None,
) -> None:
    session.add(
        models.AuditLog(
            actor_user_id=actor_user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            meta=metadata,
        )
    )
```

(O commit é responsabilidade de quem chama, para o log entrar na mesma transação da operação.)

- [ ] **Step 4: Criar `apps/api/app/modules/auth/schemas.py`**

```python
from pydantic import BaseModel


class LoginRequest(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    id: str
    name: str
    email: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    user: UserOut
```

- [ ] **Step 5: Criar `apps/api/app/modules/auth/deps.py`**

```python
import uuid

import jwt as pyjwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app import models
from app.core.database import get_session
from app.core.errors import APIError
from app.core.security import decode_access_token

bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    session: AsyncSession = Depends(get_session),
) -> models.User:
    if credentials is None:
        raise APIError(401, "NOT_AUTHENTICATED", "Autenticação necessária.")
    try:
        payload = decode_access_token(credentials.credentials)
    except pyjwt.ExpiredSignatureError:
        raise APIError(401, "TOKEN_EXPIRED", "Sessão expirada. Faça login novamente.")
    except pyjwt.InvalidTokenError:
        raise APIError(401, "INVALID_TOKEN", "Token inválido.")

    user = await session.get(models.User, uuid.UUID(payload["sub"]))
    if user is None or user.status != "active":
        raise APIError(401, "INVALID_TOKEN", "Token inválido.")
    return user
```

- [ ] **Step 6: Criar `apps/api/app/modules/auth/router.py`**

```python
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models
from app.core.config import settings
from app.core.database import get_session
from app.core.errors import APIError
from app.core.security import create_access_token, verify_password
from app.modules.audit.service import record_audit
from app.modules.auth.deps import get_current_user
from app.modules.auth.schemas import LoginRequest, LoginResponse, UserOut

router = APIRouter(tags=["auth"])


@router.post("/auth/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest, session: AsyncSession = Depends(get_session)
) -> LoginResponse:
    result = await session.execute(
        select(models.User).where(models.User.email == payload.email)
    )
    user = result.scalar_one_or_none()
    if (
        user is None
        or not verify_password(payload.password, user.password_hash)
        or user.status != "active"
    ):
        raise APIError(401, "INVALID_CREDENTIALS", "E-mail ou senha inválidos.")

    await record_audit(
        session,
        actor_user_id=user.id,
        action="auth.login",
        entity_type="user",
        entity_id=user.id,
    )
    await session.commit()

    return LoginResponse(
        access_token=create_access_token(str(user.id)),
        token_type="bearer",
        expires_in=settings.jwt_expires_in_minutes * 60,
        user=UserOut(id=str(user.id), name=user.name, email=user.email),
    )


@router.get("/auth/me", response_model=UserOut)
async def me(user: models.User = Depends(get_current_user)) -> UserOut:
    return UserOut(id=str(user.id), name=user.name, email=user.email)
```

- [ ] **Step 7: Registrar o router em `apps/api/app/main.py`**

Adicionar após a criação do `app` e do middleware:

```python
from app.modules.auth.router import router as auth_router

app.include_router(auth_router)
```

- [ ] **Step 8: Rodar testes**

Run: `.venv/bin/pytest tests/test_auth.py -v`
Expected: `7 passed`

- [ ] **Step 9: Commit**

```bash
git add apps/api
git commit -m "feat: adiciona autenticacao jwt com login, me e auditoria"
```

---

### Task 5: Seed com Maria e João

**Files:**
- Create: `apps/api/app/seed.py`

- [ ] **Step 1: Criar `apps/api/app/seed.py`**

Saldos coerentes com as transações: Maria `5000 + 1500 - 250 = 6250.00`; João `3000 + 250 = 3250.00`.

```python
import asyncio
import datetime as dt
from decimal import Decimal

from sqlalchemy import select

from app import models
from app.core.database import SessionLocal
from app.core.security import hash_password


async def seed() -> None:
    async with SessionLocal() as session:
        existing = await session.execute(select(models.User).limit(1))
        if existing.scalar_one_or_none() is not None:
            print("Seed ignorado: já existem dados.")
            return

        now = dt.datetime.now(dt.timezone.utc)

        maria = models.User(
            name="Maria Silva",
            email="maria@banklab.local",
            password_hash=hash_password("BankLab@123"),
        )
        joao = models.User(
            name="João Souza",
            email="joao@banklab.local",
            password_hash=hash_password("BankLab@123"),
        )
        session.add_all([maria, joao])
        await session.flush()

        conta_maria = models.Account(
            user_id=maria.id,
            branch="0001",
            number="0042-0",
            type="checking",
            balance=Decimal("6250.00"),
        )
        conta_joao = models.Account(
            user_id=joao.id,
            branch="0001",
            number="0188-3",
            type="checking",
            balance=Decimal("3250.00"),
        )
        session.add_all([conta_maria, conta_joao])
        await session.flush()

        session.add_all(
            [
                models.Transaction(
                    account_id=conta_maria.id,
                    type="deposit",
                    status="completed",
                    amount=Decimal("5000.00"),
                    description="Depósito inicial",
                    idempotency_key="seed-maria-deposito-1",
                    created_at=now - dt.timedelta(days=9),
                    completed_at=now - dt.timedelta(days=9),
                ),
                models.Transaction(
                    account_id=conta_maria.id,
                    type="deposit",
                    status="completed",
                    amount=Decimal("1500.00"),
                    description="Depósito salário",
                    idempotency_key="seed-maria-deposito-2",
                    created_at=now - dt.timedelta(days=5),
                    completed_at=now - dt.timedelta(days=5),
                ),
                models.Transaction(
                    account_id=conta_maria.id,
                    related_account_id=conta_joao.id,
                    type="transfer_out",
                    status="completed",
                    amount=Decimal("250.00"),
                    description="Transferência para João",
                    idempotency_key="seed-transferencia-1",
                    created_at=now - dt.timedelta(days=2),
                    completed_at=now - dt.timedelta(days=2),
                ),
                models.Transaction(
                    account_id=conta_joao.id,
                    type="deposit",
                    status="completed",
                    amount=Decimal("3000.00"),
                    description="Depósito inicial",
                    idempotency_key="seed-joao-deposito-1",
                    created_at=now - dt.timedelta(days=8),
                    completed_at=now - dt.timedelta(days=8),
                ),
                models.Transaction(
                    account_id=conta_joao.id,
                    related_account_id=conta_maria.id,
                    type="transfer_in",
                    status="completed",
                    amount=Decimal("250.00"),
                    description="Transferência de Maria",
                    idempotency_key="seed-transferencia-1",
                    created_at=now - dt.timedelta(days=2),
                    completed_at=now - dt.timedelta(days=2),
                ),
            ]
        )

        session.add_all(
            [
                models.Notification(
                    user_id=maria.id,
                    type="transaction",
                    title="Depósito recebido",
                    message="Você recebeu um depósito de R$ 1.500,00.",
                    dedup_key="seed-notif-maria-1",
                    read_at=now - dt.timedelta(days=4),
                    created_at=now - dt.timedelta(days=5),
                ),
                models.Notification(
                    user_id=maria.id,
                    type="transaction",
                    title="Transferência enviada",
                    message="Você enviou R$ 250,00 para a conta 0188-3.",
                    dedup_key="seed-notif-maria-2",
                    created_at=now - dt.timedelta(days=2),
                ),
                models.Notification(
                    user_id=joao.id,
                    type="transaction",
                    title="Transferência recebida",
                    message="Você recebeu R$ 250,00 da conta 0042-0.",
                    dedup_key="seed-notif-joao-1",
                    created_at=now - dt.timedelta(days=2),
                ),
            ]
        )

        await session.commit()
        print("Seed concluído: Maria e João criados com contas, transações e notificações.")


if __name__ == "__main__":
    asyncio.run(seed())
```

- [ ] **Step 2: Rodar o seed dentro do container**

```bash
docker compose up -d --build api
docker compose exec api python -m app.seed
```

Expected: `Seed concluído: ...`

Rodar de novo: `docker compose exec api python -m app.seed`
Expected: `Seed ignorado: já existem dados.`

- [ ] **Step 3: Verificar login real via curl**

```bash
curl -s -X POST http://localhost:8000/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email": "maria@banklab.local", "password": "BankLab@123"}'
```

Expected: JSON com `access_token` e `"name": "Maria Silva"`.

- [ ] **Step 4: Commit**

```bash
git add apps/api/app/seed.py
git commit -m "feat: adiciona seed com clientes maria e joao"
```

---

### Task 6: Contas

**Files:**
- Create: `apps/api/app/modules/accounts/__init__.py`
- Create: `apps/api/app/modules/accounts/schemas.py`
- Create: `apps/api/app/modules/accounts/router.py`
- Modify: `apps/api/app/main.py`
- Test: `apps/api/tests/test_accounts.py`

- [ ] **Step 1: Escrever testes (falham)**

`apps/api/tests/test_accounts.py`:

```python
from decimal import Decimal

from tests.conftest import auth_headers, create_account, create_user


async def test_lista_apenas_contas_do_usuario(client, session):
    maria = await create_user(session)
    joao = await create_user(session, name="João Souza", email="joao@banklab.local")
    conta_maria = await create_account(session, maria, balance=Decimal("6250.00"))
    await create_account(session, joao)

    response = await client.get("/accounts", headers=auth_headers(maria))
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == str(conta_maria.id)
    assert body[0]["balance"] == "6250.00"
    assert body[0]["branch"] == "0001"
    assert body[0]["status"] == "active"


async def test_detalhe_de_conta_propria(client, session):
    maria = await create_user(session)
    conta = await create_account(session, maria)
    response = await client.get(f"/accounts/{conta.id}", headers=auth_headers(maria))
    assert response.status_code == 200
    assert response.json()["id"] == str(conta.id)


async def test_detalhe_de_conta_de_outro_usuario_retorna_404(client, session):
    maria = await create_user(session)
    joao = await create_user(session, name="João Souza", email="joao@banklab.local")
    conta_joao = await create_account(session, joao)
    response = await client.get(
        f"/accounts/{conta_joao.id}", headers=auth_headers(maria)
    )
    assert response.status_code == 404
    assert response.json()["code"] == "ACCOUNT_NOT_FOUND"


async def test_lista_sem_token_retorna_401(client):
    response = await client.get("/accounts")
    assert response.status_code == 401
```

- [ ] **Step 2: Rodar e confirmar falha**

Run: `.venv/bin/pytest tests/test_accounts.py -v`
Expected: FAIL (404 nas rotas).

- [ ] **Step 3: Criar `apps/api/app/modules/accounts/schemas.py`**

```python
from pydantic import BaseModel


class AccountOut(BaseModel):
    id: str
    branch: str
    number: str
    type: str
    balance: str
    status: str
```

- [ ] **Step 4: Criar `apps/api/app/modules/accounts/router.py`** (e `__init__.py` vazio)

```python
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models
from app.core.database import get_session
from app.core.errors import APIError
from app.modules.accounts.schemas import AccountOut
from app.modules.auth.deps import get_current_user

router = APIRouter(tags=["accounts"])


def to_account_out(account: models.Account) -> AccountOut:
    return AccountOut(
        id=str(account.id),
        branch=account.branch,
        number=account.number,
        type=account.type,
        balance=f"{account.balance:.2f}",
        status=account.status,
    )


@router.get("/accounts", response_model=list[AccountOut])
async def list_accounts(
    user: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[AccountOut]:
    result = await session.execute(
        select(models.Account)
        .where(models.Account.user_id == user.id)
        .order_by(models.Account.created_at)
    )
    return [to_account_out(a) for a in result.scalars().all()]


@router.get("/accounts/{account_id}", response_model=AccountOut)
async def get_account(
    account_id: uuid.UUID,
    user: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> AccountOut:
    result = await session.execute(
        select(models.Account).where(
            models.Account.id == account_id, models.Account.user_id == user.id
        )
    )
    account = result.scalar_one_or_none()
    if account is None:
        raise APIError(404, "ACCOUNT_NOT_FOUND", "Conta não encontrada.")
    return to_account_out(account)
```

- [ ] **Step 5: Registrar no `main.py`**

```python
from app.modules.accounts.router import router as accounts_router

app.include_router(accounts_router)
```

- [ ] **Step 6: Rodar testes**

Run: `.venv/bin/pytest tests/test_accounts.py -v`
Expected: `4 passed`

- [ ] **Step 7: Commit**

```bash
git add apps/api
git commit -m "feat: adiciona listagem e detalhe de contas"
```

---

### Task 7: Depósitos — idempotência, evento e auditoria

**Files:**
- Create: `apps/api/app/modules/deposits/__init__.py`
- Create: `apps/api/app/modules/deposits/schemas.py`
- Create: `apps/api/app/modules/deposits/router.py`
- Modify: `apps/api/app/main.py`
- Test: `apps/api/tests/test_deposits.py`

- [ ] **Step 1: Escrever testes (falham)**

`apps/api/tests/test_deposits.py`:

```python
import uuid
from decimal import Decimal

from sqlalchemy import select

from app import models
from tests.conftest import auth_headers, create_account, create_user


def deposit_payload(account_id, amount="100.00"):
    return {
        "account_id": str(account_id),
        "amount": amount,
        "description": "Depósito simulado",
    }


def idem_headers(user, key=None):
    return {**auth_headers(user), "Idempotency-Key": key or str(uuid.uuid4())}


async def test_deposito_valido_cria_transacao_e_atualiza_saldo(
    client, session, monkeypatch
):
    events = []

    async def fake_publish(event):
        events.append(event)

    monkeypatch.setattr(
        "app.modules.deposits.router.publish_event", fake_publish
    )

    maria = await create_user(session)
    conta = await create_account(session, maria, balance=Decimal("1000.00"))

    response = await client.post(
        "/deposits",
        json=deposit_payload(conta.id, "150.50"),
        headers=idem_headers(maria),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "completed"
    assert body["new_balance"] == "1150.50"

    await session.refresh(conta)
    assert conta.balance == Decimal("1150.50")

    tx = (
        await session.execute(
            select(models.Transaction).where(models.Transaction.type == "deposit")
        )
    ).scalar_one()
    assert tx.amount == Decimal("150.50")
    assert tx.status == "completed"

    log = (
        await session.execute(
            select(models.AuditLog).where(
                models.AuditLog.action == "deposit.completed"
            )
        )
    ).scalar_one()
    assert log.actor_user_id == maria.id

    assert len(events) == 1
    assert events[0]["event_type"] == "transaction.deposit.completed"
    assert events[0]["amount"] == "150.50"


async def test_deposito_sem_idempotency_key_retorna_400(client, session):
    maria = await create_user(session)
    conta = await create_account(session, maria)
    response = await client.post(
        "/deposits", json=deposit_payload(conta.id), headers=auth_headers(maria)
    )
    assert response.status_code == 400
    assert response.json()["code"] == "IDEMPOTENCY_KEY_REQUIRED"


async def test_deposito_repetido_com_mesma_chave_nao_duplica(client, session):
    maria = await create_user(session)
    conta = await create_account(session, maria, balance=Decimal("1000.00"))
    headers = idem_headers(maria, key="repetida-1")

    first = await client.post(
        "/deposits", json=deposit_payload(conta.id, "100.00"), headers=headers
    )
    second = await client.post(
        "/deposits", json=deposit_payload(conta.id, "100.00"), headers=headers
    )

    assert first.json()["transaction_id"] == second.json()["transaction_id"]
    await session.refresh(conta)
    assert conta.balance == Decimal("1100.00")


async def test_deposito_com_valor_zero_retorna_422(client, session):
    maria = await create_user(session)
    conta = await create_account(session, maria)
    response = await client.post(
        "/deposits",
        json=deposit_payload(conta.id, "0.00"),
        headers=idem_headers(maria),
    )
    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


async def test_deposito_em_conta_de_outro_usuario_retorna_404(client, session):
    maria = await create_user(session)
    joao = await create_user(session, name="João Souza", email="joao@banklab.local")
    conta_joao = await create_account(session, joao)
    response = await client.post(
        "/deposits",
        json=deposit_payload(conta_joao.id),
        headers=idem_headers(maria),
    )
    assert response.status_code == 404
    assert response.json()["code"] == "ACCOUNT_NOT_FOUND"


async def test_precisao_decimal_em_depositos_sucessivos(client, session):
    maria = await create_user(session)
    conta = await create_account(session, maria, balance=Decimal("1000.00"))
    for _ in range(3):
        response = await client.post(
            "/deposits",
            json=deposit_payload(conta.id, "0.10"),
            headers=idem_headers(maria),
        )
        assert response.status_code == 201
    await session.refresh(conta)
    assert conta.balance == Decimal("1000.30")
```

- [ ] **Step 2: Rodar e confirmar falha**

Run: `.venv/bin/pytest tests/test_deposits.py -v`
Expected: FAIL (404 na rota).

- [ ] **Step 3: Criar `apps/api/app/modules/deposits/schemas.py`** (e `__init__.py` vazio)

```python
import uuid
from decimal import Decimal

from pydantic import BaseModel, Field


class DepositRequest(BaseModel):
    account_id: uuid.UUID
    amount: Decimal = Field(gt=Decimal("0"), max_digits=12, decimal_places=2)
    description: str | None = Field(default=None, max_length=255)


class DepositResponse(BaseModel):
    transaction_id: str
    status: str
    new_balance: str
```

- [ ] **Step 4: Criar `apps/api/app/modules/deposits/router.py`**

```python
import datetime as dt

from fastapi import APIRouter, Depends, Header
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app import models
from app.core.database import get_session
from app.core.errors import APIError
from app.core.events import publish_event
from app.modules.audit.service import record_audit
from app.modules.auth.deps import get_current_user
from app.modules.deposits.schemas import DepositRequest, DepositResponse

router = APIRouter(tags=["deposits"])


async def _find_existing(
    session: AsyncSession, user: models.User, key: str
) -> DepositResponse | None:
    result = await session.execute(
        select(models.Transaction, models.Account)
        .join(models.Account, models.Transaction.account_id == models.Account.id)
        .where(
            models.Transaction.idempotency_key == key,
            models.Transaction.type == "deposit",
            models.Account.user_id == user.id,
        )
    )
    row = result.first()
    if row is None:
        return None
    tx, account = row
    return DepositResponse(
        transaction_id=str(tx.id),
        status=tx.status,
        new_balance=f"{account.balance:.2f}",
    )


@router.post("/deposits", response_model=DepositResponse, status_code=201)
async def create_deposit(
    payload: DepositRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    user: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> DepositResponse:
    if not idempotency_key:
        raise APIError(
            400, "IDEMPOTENCY_KEY_REQUIRED", "O header Idempotency-Key é obrigatório."
        )

    existing = await _find_existing(session, user, idempotency_key)
    if existing is not None:
        return existing

    result = await session.execute(
        select(models.Account)
        .where(
            models.Account.id == payload.account_id,
            models.Account.user_id == user.id,
        )
        .with_for_update()
    )
    account = result.scalar_one_or_none()
    if account is None:
        raise APIError(404, "ACCOUNT_NOT_FOUND", "Conta não encontrada.")
    if account.status != "active":
        raise APIError(422, "ACCOUNT_NOT_ACTIVE", "A conta não está ativa.")

    now = dt.datetime.now(dt.timezone.utc)
    tx = models.Transaction(
        account_id=account.id,
        type="deposit",
        status="completed",
        amount=payload.amount,
        description=payload.description,
        idempotency_key=idempotency_key,
        completed_at=now,
    )
    session.add(tx)
    account.balance = account.balance + payload.amount
    await session.flush()
    await record_audit(
        session,
        actor_user_id=user.id,
        action="deposit.completed",
        entity_type="transaction",
        entity_id=tx.id,
        metadata={"amount": f"{payload.amount:.2f}", "account_id": str(account.id)},
    )

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        existing = await _find_existing(session, user, idempotency_key)
        if existing is not None:
            return existing
        raise

    await publish_event(
        {
            "event_type": "transaction.deposit.completed",
            "transaction_id": str(tx.id),
            "account_id": str(account.id),
            "user_id": str(user.id),
            "amount": f"{payload.amount:.2f}",
            "occurred_at": now.isoformat(),
        }
    )

    return DepositResponse(
        transaction_id=str(tx.id),
        status=tx.status,
        new_balance=f"{account.balance:.2f}",
    )
```

- [ ] **Step 5: Registrar no `main.py`**

```python
from app.modules.deposits.router import router as deposits_router

app.include_router(deposits_router)
```

- [ ] **Step 6: Rodar testes**

Run: `.venv/bin/pytest tests/test_deposits.py -v`
Expected: `6 passed`

- [ ] **Step 7: Commit**

```bash
git add apps/api
git commit -m "feat: adiciona deposito idempotente com evento e auditoria"
```

---

### Task 8: Transferências atômicas e idempotentes

**Files:**
- Create: `apps/api/app/modules/transfers/__init__.py`
- Create: `apps/api/app/modules/transfers/schemas.py`
- Create: `apps/api/app/modules/transfers/router.py`
- Modify: `apps/api/app/main.py`
- Test: `apps/api/tests/test_transfers.py`

- [ ] **Step 1: Escrever testes (falham)**

`apps/api/tests/test_transfers.py`:

```python
import uuid
from decimal import Decimal

from sqlalchemy import select

from app import models
from tests.conftest import auth_headers, create_account, create_user


def transfer_payload(source_id, destination_number, amount="250.00"):
    return {
        "source_account_id": str(source_id),
        "destination_account_number": destination_number,
        "amount": amount,
        "description": "Transferência teste",
    }


def idem_headers(user, key=None):
    return {**auth_headers(user), "Idempotency-Key": key or str(uuid.uuid4())}


async def fixture_contas(session):
    maria = await create_user(session)
    joao = await create_user(session, name="João Souza", email="joao@banklab.local")
    origem = await create_account(
        session, maria, number="0042-0", balance=Decimal("1000.00")
    )
    destino = await create_account(
        session, joao, number="0188-3", balance=Decimal("500.00")
    )
    return maria, joao, origem, destino


async def test_transferencia_valida_atualiza_saldos_atomicamente(
    client, session, monkeypatch
):
    events = []

    async def fake_publish(event):
        events.append(event)

    monkeypatch.setattr(
        "app.modules.transfers.router.publish_event", fake_publish
    )

    maria, joao, origem, destino = await fixture_contas(session)

    response = await client.post(
        "/transfers",
        json=transfer_payload(origem.id, "0188-3", "250.00"),
        headers=idem_headers(maria),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "completed"
    assert body["new_balance"] == "750.00"
    assert body["source_transaction_id"] != body["destination_transaction_id"]

    await session.refresh(origem)
    await session.refresh(destino)
    assert origem.balance == Decimal("750.00")
    assert destino.balance == Decimal("750.00")

    txs = (
        (await session.execute(select(models.Transaction))).scalars().all()
    )
    assert {t.type for t in txs} == {"transfer_out", "transfer_in"}

    log = (
        await session.execute(
            select(models.AuditLog).where(
                models.AuditLog.action == "transfer.completed"
            )
        )
    ).scalar_one()
    assert log.actor_user_id == maria.id

    assert len(events) == 1
    assert events[0]["event_type"] == "transaction.transfer.completed"
    assert events[0]["source_user_id"] == str(maria.id)
    assert events[0]["destination_user_id"] == str(joao.id)


async def test_saldo_insuficiente_bloqueia_sem_alterar_nada(client, session):
    maria, joao, origem, destino = await fixture_contas(session)

    response = await client.post(
        "/transfers",
        json=transfer_payload(origem.id, "0188-3", "2000.00"),
        headers=idem_headers(maria),
    )
    assert response.status_code == 422
    assert response.json()["code"] == "INSUFFICIENT_BALANCE"

    await session.refresh(origem)
    await session.refresh(destino)
    assert origem.balance == Decimal("1000.00")
    assert destino.balance == Decimal("500.00")
    txs = (await session.execute(select(models.Transaction))).scalars().all()
    assert txs == []


async def test_conta_destino_inexistente_retorna_404(client, session):
    maria, _, origem, _ = await fixture_contas(session)
    response = await client.post(
        "/transfers",
        json=transfer_payload(origem.id, "9999-9"),
        headers=idem_headers(maria),
    )
    assert response.status_code == 404
    assert response.json()["code"] == "DESTINATION_ACCOUNT_NOT_FOUND"


async def test_transferencia_para_mesma_conta_retorna_422(client, session):
    maria, _, origem, _ = await fixture_contas(session)
    response = await client.post(
        "/transfers",
        json=transfer_payload(origem.id, "0042-0"),
        headers=idem_headers(maria),
    )
    assert response.status_code == 422
    assert response.json()["code"] == "SAME_ACCOUNT"


async def test_conta_origem_de_outro_usuario_retorna_404(client, session):
    maria, joao, origem, destino = await fixture_contas(session)
    response = await client.post(
        "/transfers",
        json=transfer_payload(destino.id, "0042-0"),
        headers=idem_headers(maria),
    )
    assert response.status_code == 404
    assert response.json()["code"] == "ACCOUNT_NOT_FOUND"


async def test_transferencia_repetida_com_mesma_chave_nao_duplica(client, session):
    maria, joao, origem, destino = await fixture_contas(session)
    headers = idem_headers(maria, key="transfer-repetida-1")
    payload = transfer_payload(origem.id, "0188-3", "100.00")

    first = await client.post("/transfers", json=payload, headers=headers)
    second = await client.post("/transfers", json=payload, headers=headers)

    assert first.json()["transfer_id"] == second.json()["transfer_id"]
    assert (
        first.json()["destination_transaction_id"]
        == second.json()["destination_transaction_id"]
    )
    await session.refresh(origem)
    await session.refresh(destino)
    assert origem.balance == Decimal("900.00")
    assert destino.balance == Decimal("600.00")


async def test_valor_negativo_retorna_422(client, session):
    maria, _, origem, _ = await fixture_contas(session)
    response = await client.post(
        "/transfers",
        json=transfer_payload(origem.id, "0188-3", "-10.00"),
        headers=idem_headers(maria),
    )
    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


async def test_conta_origem_inativa_retorna_422(client, session):
    maria = await create_user(session)
    joao = await create_user(session, name="João Souza", email="joao@banklab.local")
    origem = await create_account(
        session, maria, number="0042-0", balance=Decimal("1000.00"), status="blocked"
    )
    await create_account(session, joao, number="0188-3")
    response = await client.post(
        "/transfers",
        json=transfer_payload(origem.id, "0188-3"),
        headers=idem_headers(maria),
    )
    assert response.status_code == 422
    assert response.json()["code"] == "ACCOUNT_NOT_ACTIVE"


async def test_corrida_de_idempotencia_cai_no_fallback_sem_duplicar(
    client, session, monkeypatch
):
    from app.modules.transfers import router as transfers_router

    maria, joao, origem, destino = await fixture_contas(session)
    headers = idem_headers(maria, key="transfer-corrida-1")
    payload = transfer_payload(origem.id, "0188-3", "100.00")

    first = await client.post("/transfers", json=payload, headers=headers)
    assert first.status_code == 201

    original_find = transfers_router._find_existing
    calls = {"n": 0}

    async def stale_find(session_, user_id, key):
        calls["n"] += 1
        if calls["n"] == 1:
            return None
        return await original_find(session_, user_id, key)

    monkeypatch.setattr(transfers_router, "_find_existing", stale_find)

    second = await client.post("/transfers", json=payload, headers=headers)
    assert second.status_code == 201
    assert second.json()["transfer_id"] == first.json()["transfer_id"]

    await session.refresh(origem)
    await session.refresh(destino)
    assert origem.balance == Decimal("900.00")
    assert destino.balance == Decimal("600.00")
```

- [ ] **Step 2: Rodar e confirmar falha**

Run: `.venv/bin/pytest tests/test_transfers.py -v`
Expected: FAIL (404 na rota).

- [ ] **Step 3: Criar `apps/api/app/modules/transfers/schemas.py`** (e `__init__.py` vazio)

```python
import uuid
from decimal import Decimal

from pydantic import BaseModel, Field


class TransferRequest(BaseModel):
    source_account_id: uuid.UUID
    destination_account_number: str
    amount: Decimal = Field(gt=Decimal("0"), max_digits=12, decimal_places=2)
    description: str | None = Field(default=None, max_length=255)


class TransferResponse(BaseModel):
    transfer_id: str
    status: str
    source_transaction_id: str
    destination_transaction_id: str
    new_balance: str
```

- [ ] **Step 4: Criar `apps/api/app/modules/transfers/router.py`**

As duas contas são travadas com `FOR UPDATE` em ordem determinística de `id` para evitar deadlock:

```python
import datetime as dt
import uuid

from fastapi import APIRouter, Depends, Header
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app import models
from app.core.database import get_session
from app.core.errors import APIError
from app.core.events import publish_event
from app.modules.audit.service import record_audit
from app.modules.auth.deps import get_current_user
from app.modules.transfers.schemas import TransferRequest, TransferResponse

router = APIRouter(tags=["transfers"])


async def _find_existing(
    session: AsyncSession, user_id: uuid.UUID, key: str
) -> TransferResponse | None:
    result = await session.execute(
        select(models.Transaction, models.Account)
        .join(models.Account, models.Transaction.account_id == models.Account.id)
        .where(
            models.Transaction.idempotency_key == key,
            models.Transaction.type == "transfer_out",
            models.Account.user_id == user_id,
        )
    )
    row = result.first()
    if row is None:
        return None
    tx_out, source_account = row
    tx_in = (
        await session.execute(
            select(models.Transaction).where(
                models.Transaction.idempotency_key == key,
                models.Transaction.type == "transfer_in",
            )
        )
    ).scalar_one()
    return TransferResponse(
        transfer_id=str(tx_out.id),
        status=tx_out.status,
        source_transaction_id=str(tx_out.id),
        destination_transaction_id=str(tx_in.id),
        new_balance=f"{source_account.balance:.2f}",
    )


@router.post("/transfers", response_model=TransferResponse, status_code=201)
async def create_transfer(
    payload: TransferRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    user: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> TransferResponse:
    if not idempotency_key:
        raise APIError(
            400, "IDEMPOTENCY_KEY_REQUIRED", "O header Idempotency-Key é obrigatório."
        )

    # Capturado antes de qualquer rollback: após rollback o objeto ORM expira
    # e acessar user.id dispararia lazy-load fora do greenlet (MissingGreenlet).
    user_id = user.id

    existing = await _find_existing(session, user_id, idempotency_key)
    if existing is not None:
        return existing

    source_check = (
        await session.execute(
            select(models.Account).where(
                models.Account.id == payload.source_account_id,
                models.Account.user_id == user_id,
            )
        )
    ).scalar_one_or_none()
    if source_check is None:
        raise APIError(404, "ACCOUNT_NOT_FOUND", "Conta não encontrada.")

    destination_check = (
        await session.execute(
            select(models.Account).where(
                models.Account.number == payload.destination_account_number
            )
        )
    ).scalar_one_or_none()
    if destination_check is None:
        raise APIError(
            404, "DESTINATION_ACCOUNT_NOT_FOUND", "Conta de destino não encontrada."
        )
    if destination_check.id == source_check.id:
        raise APIError(
            422, "SAME_ACCOUNT", "A conta de destino deve ser diferente da origem."
        )

    locked = (
        await session.execute(
            select(models.Account)
            .where(models.Account.id.in_([source_check.id, destination_check.id]))
            .order_by(models.Account.id)
            .with_for_update()
        )
    ).scalars().all()
    by_id = {account.id: account for account in locked}
    source = by_id[source_check.id]
    destination = by_id[destination_check.id]

    if source.status != "active":
        raise APIError(422, "ACCOUNT_NOT_ACTIVE", "A conta de origem não está ativa.")
    if destination.status != "active":
        raise APIError(
            422, "ACCOUNT_NOT_ACTIVE", "A conta de destino não está ativa."
        )
    if source.balance < payload.amount:
        raise APIError(
            422,
            "INSUFFICIENT_BALANCE",
            "Saldo insuficiente para concluir a transferência.",
        )

    now = dt.datetime.now(dt.timezone.utc)
    tx_out = models.Transaction(
        account_id=source.id,
        related_account_id=destination.id,
        type="transfer_out",
        status="completed",
        amount=payload.amount,
        description=payload.description,
        idempotency_key=idempotency_key,
        completed_at=now,
    )
    tx_in = models.Transaction(
        account_id=destination.id,
        related_account_id=source.id,
        type="transfer_in",
        status="completed",
        amount=payload.amount,
        description=payload.description,
        idempotency_key=idempotency_key,
        completed_at=now,
    )
    session.add_all([tx_out, tx_in])
    source.balance = source.balance - payload.amount
    destination.balance = destination.balance + payload.amount

    # flush + audit + commit dentro do try: o IntegrityError da constraint
    # única dispara já no flush, e o fallback precisa alcançá-lo.
    try:
        await session.flush()
        await record_audit(
            session,
            actor_user_id=user_id,
            action="transfer.completed",
            entity_type="transaction",
            entity_id=tx_out.id,
            metadata={
                "amount": f"{payload.amount:.2f}",
                "source_account_id": str(source.id),
                "destination_account_id": str(destination.id),
            },
        )
        await session.commit()
    except IntegrityError:
        await session.rollback()
        existing = await _find_existing(session, user_id, idempotency_key)
        if existing is not None:
            return existing
        raise

    await publish_event(
        {
            "event_type": "transaction.transfer.completed",
            "source_transaction_id": str(tx_out.id),
            "destination_transaction_id": str(tx_in.id),
            "source_account_id": str(source.id),
            "destination_account_id": str(destination.id),
            "source_user_id": str(user_id),
            "destination_user_id": str(destination.user_id),
            "amount": f"{payload.amount:.2f}",
            "occurred_at": now.isoformat(),
        }
    )

    return TransferResponse(
        transfer_id=str(tx_out.id),
        status=tx_out.status,
        source_transaction_id=str(tx_out.id),
        destination_transaction_id=str(tx_in.id),
        new_balance=f"{source.balance:.2f}",
    )
```

- [ ] **Step 5: Registrar no `main.py`**

```python
from app.modules.transfers.router import router as transfers_router

app.include_router(transfers_router)
```

- [ ] **Step 6: Rodar testes**

Run: `.venv/bin/pytest tests/test_transfers.py -v`
Expected: `9 passed`

- [ ] **Step 7: Commit**

```bash
git add apps/api
git commit -m "feat: adiciona transferencia atomica e idempotente entre contas"
```

---

### Task 9: Extrato — listagem com filtros e paginação

**Files:**
- Create: `apps/api/app/modules/transactions/__init__.py`
- Create: `apps/api/app/modules/transactions/schemas.py`
- Create: `apps/api/app/modules/transactions/router.py`
- Modify: `apps/api/app/main.py`
- Test: `apps/api/tests/test_transactions.py`

- [ ] **Step 1: Escrever testes (falham)**

`apps/api/tests/test_transactions.py`:

```python
import datetime as dt
from decimal import Decimal

from app import models
from tests.conftest import auth_headers, create_account, create_user


async def criar_transacoes(session, account):
    now = dt.datetime.now(dt.timezone.utc)
    txs = [
        models.Transaction(
            account_id=account.id,
            type="deposit",
            status="completed",
            amount=Decimal("100.00"),
            description="Depósito salário",
            created_at=now - dt.timedelta(days=10),
        ),
        models.Transaction(
            account_id=account.id,
            type="transfer_out",
            status="completed",
            amount=Decimal("50.00"),
            description="Pagamento aluguel",
            created_at=now - dt.timedelta(days=5),
        ),
        models.Transaction(
            account_id=account.id,
            type="deposit",
            status="pending",
            amount=Decimal("30.00"),
            description="Depósito extra",
            created_at=now - dt.timedelta(days=1),
        ),
    ]
    session.add_all(txs)
    await session.commit()
    return txs


async def test_lista_paginada_ordenada_por_data_desc(client, session):
    maria = await create_user(session)
    conta = await create_account(session, maria)
    await criar_transacoes(session, conta)

    response = await client.get(
        "/transactions?page=1&page_size=2", headers=auth_headers(maria)
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert body["page"] == 1
    assert body["page_size"] == 2
    assert len(body["items"]) == 2
    assert body["items"][0]["description"] == "Depósito extra"


async def test_filtro_por_tipo(client, session):
    maria = await create_user(session)
    conta = await create_account(session, maria)
    await criar_transacoes(session, conta)

    response = await client.get(
        "/transactions?type=transfer_out", headers=auth_headers(maria)
    )
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["type"] == "transfer_out"


async def test_filtro_por_status(client, session):
    maria = await create_user(session)
    conta = await create_account(session, maria)
    await criar_transacoes(session, conta)

    response = await client.get(
        "/transactions?status=pending", headers=auth_headers(maria)
    )
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["status"] == "pending"


async def test_filtro_por_periodo(client, session):
    maria = await create_user(session)
    conta = await create_account(session, maria)
    await criar_transacoes(session, conta)

    hoje = dt.date.today()
    de = (hoje - dt.timedelta(days=6)).isoformat()
    ate = (hoje - dt.timedelta(days=3)).isoformat()
    response = await client.get(
        f"/transactions?from={de}&to={ate}", headers=auth_headers(maria)
    )
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["description"] == "Pagamento aluguel"


async def test_busca_textual_por_descricao(client, session):
    maria = await create_user(session)
    conta = await create_account(session, maria)
    await criar_transacoes(session, conta)

    response = await client.get(
        "/transactions?search=aluguel", headers=auth_headers(maria)
    )
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["description"] == "Pagamento aluguel"


async def test_sem_resultados_retorna_lista_vazia(client, session):
    maria = await create_user(session)
    await create_account(session, maria)
    response = await client.get(
        "/transactions?search=inexistente", headers=auth_headers(maria)
    )
    body = response.json()
    assert body["total"] == 0
    assert body["items"] == []


async def test_nao_lista_transacoes_de_outro_usuario(client, session):
    maria = await create_user(session)
    joao = await create_user(session, name="João Souza", email="joao@banklab.local")
    conta_joao = await create_account(session, joao)
    await criar_transacoes(session, conta_joao)

    response = await client.get("/transactions", headers=auth_headers(maria))
    assert response.json()["total"] == 0
```

- [ ] **Step 2: Rodar e confirmar falha**

Run: `.venv/bin/pytest tests/test_transactions.py -v`
Expected: FAIL (404 na rota).

- [ ] **Step 3: Criar `apps/api/app/modules/transactions/schemas.py`** (e `__init__.py` vazio)

```python
from pydantic import BaseModel

from app import models


class TransactionOut(BaseModel):
    id: str
    account_id: str
    related_account_id: str | None
    type: str
    status: str
    amount: str
    description: str | None
    created_at: str
    completed_at: str | None


class TransactionListResponse(BaseModel):
    items: list[TransactionOut]
    page: int
    page_size: int
    total: int


def to_transaction_out(tx: models.Transaction) -> TransactionOut:
    return TransactionOut(
        id=str(tx.id),
        account_id=str(tx.account_id),
        related_account_id=(
            str(tx.related_account_id) if tx.related_account_id else None
        ),
        type=tx.type,
        status=tx.status,
        amount=f"{tx.amount:.2f}",
        description=tx.description,
        created_at=tx.created_at.isoformat(),
        completed_at=tx.completed_at.isoformat() if tx.completed_at else None,
    )
```

- [ ] **Step 4: Criar `apps/api/app/modules/transactions/router.py`**

```python
import datetime as dt
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models
from app.core.database import get_session
from app.modules.auth.deps import get_current_user
from app.modules.transactions.schemas import (
    TransactionListResponse,
    to_transaction_out,
)

router = APIRouter(tags=["transactions"])


@router.get("/transactions", response_model=TransactionListResponse)
async def list_transactions(
    account_id: uuid.UUID | None = Query(default=None),
    from_: dt.date | None = Query(default=None, alias="from"),
    to: dt.date | None = Query(default=None),
    type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> TransactionListResponse:
    filters = [models.Account.user_id == user.id]
    if account_id is not None:
        filters.append(models.Transaction.account_id == account_id)
    if from_ is not None:
        filters.append(
            models.Transaction.created_at
            >= dt.datetime.combine(from_, dt.time.min, tzinfo=dt.timezone.utc)
        )
    if to is not None:
        filters.append(
            models.Transaction.created_at
            < dt.datetime.combine(
                to + dt.timedelta(days=1), dt.time.min, tzinfo=dt.timezone.utc
            )
        )
    if type is not None:
        filters.append(models.Transaction.type == type)
    if status is not None:
        filters.append(models.Transaction.status == status)
    if search:
        filters.append(models.Transaction.description.ilike(f"%{search}%"))

    base = (
        select(models.Transaction)
        .join(models.Account, models.Transaction.account_id == models.Account.id)
        .where(*filters)
    )

    total = (
        await session.execute(
            select(func.count()).select_from(base.subquery())
        )
    ).scalar_one()

    items = (
        (
            await session.execute(
                base.order_by(models.Transaction.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        .scalars()
        .all()
    )

    return TransactionListResponse(
        items=[to_transaction_out(tx) for tx in items],
        page=page,
        page_size=page_size,
        total=total,
    )
```

- [ ] **Step 5: Registrar no `main.py`**

```python
from app.modules.transactions.router import router as transactions_router

app.include_router(transactions_router)
```

- [ ] **Step 6: Rodar testes**

Run: `.venv/bin/pytest tests/test_transactions.py -v`
Expected: `7 passed`

- [ ] **Step 7: Commit**

```bash
git add apps/api
git commit -m "feat: adiciona extrato com filtros e paginacao"
```

---

### Task 10: Resumo da página Início (`GET /summary`)

**Files:**
- Create: `apps/api/app/modules/summary/__init__.py`
- Create: `apps/api/app/modules/summary/router.py`
- Modify: `apps/api/app/main.py`
- Test: `apps/api/tests/test_summary.py`

- [ ] **Step 1: Escrever testes (falham)**

`apps/api/tests/test_summary.py`:

```python
import datetime as dt
from decimal import Decimal

from app import models
from tests.conftest import auth_headers, create_account, create_user


async def test_summary_agrega_dados_do_usuario(client, session):
    maria = await create_user(session)
    conta = await create_account(session, maria, balance=Decimal("6250.00"))
    now = dt.datetime.now(dt.timezone.utc)

    session.add_all(
        [
            models.Transaction(
                account_id=conta.id,
                type="deposit",
                status="completed",
                amount=Decimal("1500.00"),
                description="Depósito do mês",
                created_at=now,
            ),
            models.Transaction(
                account_id=conta.id,
                type="transfer_out",
                status="completed",
                amount=Decimal("250.00"),
                description="Saída do mês",
                created_at=now,
            ),
            models.Notification(
                user_id=maria.id,
                title="Depósito recebido",
                message="Você recebeu um depósito.",
            ),
        ]
    )
    await session.commit()

    response = await client.get("/summary", headers=auth_headers(maria))
    assert response.status_code == 200
    body = response.json()
    assert body["total_balance"] == "6250.00"
    assert body["monthly_inflow"] == "1500.00"
    assert body["monthly_outflow"] == "250.00"
    assert body["unread_notifications"] == 1
    assert len(body["latest_transactions"]) == 2


async def test_summary_sem_movimentacoes_retorna_zeros(client, session):
    maria = await create_user(session)
    await create_account(session, maria, balance=Decimal("0.00"))
    response = await client.get("/summary", headers=auth_headers(maria))
    body = response.json()
    assert body["monthly_inflow"] == "0.00"
    assert body["monthly_outflow"] == "0.00"
    assert body["unread_notifications"] == 0
    assert body["latest_transactions"] == []


async def test_summary_limita_ultimas_5_transacoes(client, session):
    maria = await create_user(session)
    conta = await create_account(session, maria)
    now = dt.datetime.now(dt.timezone.utc)
    session.add_all(
        [
            models.Transaction(
                account_id=conta.id,
                type="deposit",
                status="completed",
                amount=Decimal("10.00"),
                created_at=now - dt.timedelta(minutes=i),
            )
            for i in range(7)
        ]
    )
    await session.commit()

    response = await client.get("/summary", headers=auth_headers(maria))
    assert len(response.json()["latest_transactions"]) == 5
```

- [ ] **Step 2: Rodar e confirmar falha**

Run: `.venv/bin/pytest tests/test_summary.py -v`
Expected: FAIL (404 na rota).

- [ ] **Step 3: Criar `apps/api/app/modules/summary/router.py`** (e `__init__.py` vazio)

```python
import datetime as dt
from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models
from app.core.database import get_session
from app.modules.auth.deps import get_current_user
from app.modules.transactions.schemas import TransactionOut, to_transaction_out

router = APIRouter(tags=["summary"])


class SummaryResponse(BaseModel):
    total_balance: str
    monthly_inflow: str
    monthly_outflow: str
    unread_notifications: int
    latest_transactions: list[TransactionOut]


@router.get("/summary", response_model=SummaryResponse)
async def get_summary(
    user: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SummaryResponse:
    now = dt.datetime.now(dt.timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    total_balance = (
        await session.execute(
            select(func.coalesce(func.sum(models.Account.balance), 0)).where(
                models.Account.user_id == user.id
            )
        )
    ).scalar_one()

    async def month_sum(types: list[str]) -> Decimal:
        return (
            await session.execute(
                select(func.coalesce(func.sum(models.Transaction.amount), 0))
                .join(
                    models.Account,
                    models.Transaction.account_id == models.Account.id,
                )
                .where(
                    models.Account.user_id == user.id,
                    models.Transaction.type.in_(types),
                    models.Transaction.status == "completed",
                    models.Transaction.created_at >= month_start,
                )
            )
        ).scalar_one()

    inflow = await month_sum(["deposit", "transfer_in"])
    outflow = await month_sum(["transfer_out"])

    unread = (
        await session.execute(
            select(func.count())
            .select_from(models.Notification)
            .where(
                models.Notification.user_id == user.id,
                models.Notification.read_at.is_(None),
            )
        )
    ).scalar_one()

    latest = (
        (
            await session.execute(
                select(models.Transaction)
                .join(
                    models.Account,
                    models.Transaction.account_id == models.Account.id,
                )
                .where(models.Account.user_id == user.id)
                .order_by(models.Transaction.created_at.desc())
                .limit(5)
            )
        )
        .scalars()
        .all()
    )

    return SummaryResponse(
        total_balance=f"{Decimal(total_balance):.2f}",
        monthly_inflow=f"{Decimal(inflow):.2f}",
        monthly_outflow=f"{Decimal(outflow):.2f}",
        unread_notifications=unread,
        latest_transactions=[to_transaction_out(tx) for tx in latest],
    )
```

- [ ] **Step 4: Registrar no `main.py`**

```python
from app.modules.summary.router import router as summary_router

app.include_router(summary_router)
```

- [ ] **Step 5: Rodar testes**

Run: `.venv/bin/pytest tests/test_summary.py -v`
Expected: `3 passed`

- [ ] **Step 6: Commit**

```bash
git add apps/api
git commit -m "feat: adiciona resumo agregado para pagina inicio"
```

---

### Task 11: Notificações — listagem e marcação de leitura

**Files:**
- Create: `apps/api/app/modules/notifications/__init__.py`
- Create: `apps/api/app/modules/notifications/schemas.py`
- Create: `apps/api/app/modules/notifications/router.py`
- Modify: `apps/api/app/main.py`
- Test: `apps/api/tests/test_notifications.py`

- [ ] **Step 1: Escrever testes (falham)**

`apps/api/tests/test_notifications.py`:

```python
import datetime as dt

from app import models
from tests.conftest import auth_headers, create_user


async def criar_notificacao(session, user, *, read_at=None, title="Depósito recebido"):
    notif = models.Notification(
        user_id=user.id,
        title=title,
        message="Mensagem de teste.",
        read_at=read_at,
    )
    session.add(notif)
    await session.commit()
    await session.refresh(notif)
    return notif


async def test_lista_apenas_notificacoes_do_usuario(client, session):
    maria = await create_user(session)
    joao = await create_user(session, name="João Souza", email="joao@banklab.local")
    await criar_notificacao(session, maria)
    await criar_notificacao(session, joao, title="Outra")

    response = await client.get("/notifications", headers=auth_headers(maria))
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["title"] == "Depósito recebido"
    assert body[0]["read_at"] is None


async def test_marcar_notificacao_como_lida(client, session):
    maria = await create_user(session)
    notif = await criar_notificacao(session, maria)

    response = await client.patch(
        f"/notifications/{notif.id}/read", headers=auth_headers(maria)
    )
    assert response.status_code == 200
    assert response.json()["read_at"] is not None


async def test_marcar_ja_lida_mantem_data_original(client, session):
    maria = await create_user(session)
    original = dt.datetime(2026, 6, 1, 12, 0, tzinfo=dt.timezone.utc)
    notif = await criar_notificacao(session, maria, read_at=original)

    response = await client.patch(
        f"/notifications/{notif.id}/read", headers=auth_headers(maria)
    )
    assert response.status_code == 200
    assert response.json()["read_at"] == original.isoformat()


async def test_notificacao_de_outro_usuario_retorna_404(client, session):
    maria = await create_user(session)
    joao = await create_user(session, name="João Souza", email="joao@banklab.local")
    notif = await criar_notificacao(session, joao)

    response = await client.patch(
        f"/notifications/{notif.id}/read", headers=auth_headers(maria)
    )
    assert response.status_code == 404
    assert response.json()["code"] == "NOTIFICATION_NOT_FOUND"
```

- [ ] **Step 2: Rodar e confirmar falha**

Run: `.venv/bin/pytest tests/test_notifications.py -v`
Expected: FAIL (404 nas rotas).

- [ ] **Step 3: Criar `apps/api/app/modules/notifications/schemas.py`** (e `__init__.py` vazio)

```python
from pydantic import BaseModel

from app import models


class NotificationOut(BaseModel):
    id: str
    type: str
    title: str
    message: str
    read_at: str | None
    created_at: str


def to_notification_out(notif: models.Notification) -> NotificationOut:
    return NotificationOut(
        id=str(notif.id),
        type=notif.type,
        title=notif.title,
        message=notif.message,
        read_at=notif.read_at.isoformat() if notif.read_at else None,
        created_at=notif.created_at.isoformat(),
    )
```

- [ ] **Step 4: Criar `apps/api/app/modules/notifications/router.py`**

```python
import datetime as dt
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models
from app.core.database import get_session
from app.core.errors import APIError
from app.modules.auth.deps import get_current_user
from app.modules.notifications.schemas import NotificationOut, to_notification_out

router = APIRouter(tags=["notifications"])


@router.get("/notifications", response_model=list[NotificationOut])
async def list_notifications(
    user: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[NotificationOut]:
    result = await session.execute(
        select(models.Notification)
        .where(models.Notification.user_id == user.id)
        .order_by(models.Notification.created_at.desc())
    )
    return [to_notification_out(n) for n in result.scalars().all()]


@router.patch("/notifications/{notification_id}/read", response_model=NotificationOut)
async def mark_as_read(
    notification_id: uuid.UUID,
    user: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> NotificationOut:
    result = await session.execute(
        select(models.Notification).where(
            models.Notification.id == notification_id,
            models.Notification.user_id == user.id,
        )
    )
    notif = result.scalar_one_or_none()
    if notif is None:
        raise APIError(404, "NOTIFICATION_NOT_FOUND", "Notificação não encontrada.")
    if notif.read_at is None:
        notif.read_at = dt.datetime.now(dt.timezone.utc)
        await session.commit()
        await session.refresh(notif)
    return to_notification_out(notif)
```

- [ ] **Step 5: Registrar no `main.py`**

```python
from app.modules.notifications.router import router as notifications_router

app.include_router(notifications_router)
```

- [ ] **Step 6: Rodar testes**

Run: `.venv/bin/pytest tests/test_notifications.py -v`
Expected: `4 passed`

- [ ] **Step 7: Commit**

```bash
git add apps/api
git commit -m "feat: adiciona listagem e leitura de notificacoes"
```

---

### Task 12: Worker de notificações com consumer group e deduplicação

**Files:**
- Create: `apps/api/app/workers/__init__.py`
- Create: `apps/api/app/workers/notifications_worker.py`
- Modify: `docker-compose.yml` (adicionar serviço `worker`)
- Test: `apps/api/tests/test_notifications_worker.py`

- [ ] **Step 1: Escrever testes (falham)**

`apps/api/tests/test_notifications_worker.py`:

```python
import uuid

from sqlalchemy import select

from app import models
from app.workers.notifications_worker import build_notifications, handle_event
from tests.conftest import create_user


def deposit_event(user_id, tx_id=None):
    return {
        "event_type": "transaction.deposit.completed",
        "transaction_id": tx_id or str(uuid.uuid4()),
        "account_id": str(uuid.uuid4()),
        "user_id": str(user_id),
        "amount": "1500.00",
        "occurred_at": "2026-06-10T12:00:00+00:00",
    }


async def test_evento_de_deposito_cria_notificacao(client, session):
    maria = await create_user(session)
    await handle_event(session, deposit_event(maria.id))

    notif = (
        await session.execute(select(models.Notification))
    ).scalar_one()
    assert notif.user_id == maria.id
    assert notif.title == "Depósito recebido"
    assert "R$ 1.500,00" in notif.message
    assert notif.read_at is None


async def test_reprocessar_mesmo_evento_nao_duplica(client, session):
    maria = await create_user(session)
    event = deposit_event(maria.id)
    await handle_event(session, event)
    await handle_event(session, event)

    notifs = (
        (await session.execute(select(models.Notification))).scalars().all()
    )
    assert len(notifs) == 1


async def test_evento_de_transferencia_notifica_remetente_e_destinatario(
    client, session
):
    maria = await create_user(session)
    joao = await create_user(session, name="João Souza", email="joao@banklab.local")
    event = {
        "event_type": "transaction.transfer.completed",
        "source_transaction_id": str(uuid.uuid4()),
        "destination_transaction_id": str(uuid.uuid4()),
        "source_account_id": str(uuid.uuid4()),
        "destination_account_id": str(uuid.uuid4()),
        "source_user_id": str(maria.id),
        "destination_user_id": str(joao.id),
        "amount": "250.00",
        "occurred_at": "2026-06-10T12:00:00+00:00",
    }
    await handle_event(session, event)

    notifs = (
        (await session.execute(select(models.Notification))).scalars().all()
    )
    assert len(notifs) == 2
    titles = {n.title for n in notifs}
    assert titles == {"Transferência enviada", "Transferência recebida"}


def test_evento_desconhecido_nao_gera_notificacoes():
    assert build_notifications({"event_type": "outro.evento"}) == []
```

- [ ] **Step 2: Rodar e confirmar falha**

Run: `.venv/bin/pytest tests/test_notifications_worker.py -v`
Expected: FAIL com `ModuleNotFoundError`.

- [ ] **Step 3: Criar `apps/api/app/workers/notifications_worker.py`** (e `__init__.py` vazio)

```python
import asyncio
import json
import logging
import uuid
from decimal import Decimal

import redis.asyncio as aioredis
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app import models
from app.core.config import settings
from app.core.database import SessionLocal
from app.core.events import STREAM

logger = logging.getLogger(__name__)

GROUP = "notifications"
CONSUMER = "worker-1"


def format_brl(amount: str) -> str:
    value = f"{Decimal(amount):,.2f}"
    return "R$ " + value.replace(",", "X").replace(".", ",").replace("X", ".")


def build_notifications(event: dict) -> list[dict]:
    event_type = event.get("event_type")
    if event_type == "transaction.deposit.completed":
        return [
            {
                "user_id": event["user_id"],
                "type": "transaction",
                "title": "Depósito recebido",
                "message": (
                    f"Você recebeu um depósito de {format_brl(event['amount'])}."
                ),
                "dedup_key": (
                    f"{event_type}:{event['transaction_id']}:{event['user_id']}"
                ),
            }
        ]
    if event_type == "transaction.transfer.completed":
        return [
            {
                "user_id": event["source_user_id"],
                "type": "transaction",
                "title": "Transferência enviada",
                "message": f"Você enviou {format_brl(event['amount'])}.",
                "dedup_key": (
                    f"{event_type}:{event['source_transaction_id']}"
                    f":{event['source_user_id']}"
                ),
            },
            {
                "user_id": event["destination_user_id"],
                "type": "transaction",
                "title": "Transferência recebida",
                "message": f"Você recebeu {format_brl(event['amount'])}.",
                "dedup_key": (
                    f"{event_type}:{event['destination_transaction_id']}"
                    f":{event['destination_user_id']}"
                ),
            },
        ]
    logger.warning("Evento desconhecido ignorado: %s", event_type)
    return []


async def handle_event(session: AsyncSession, event: dict) -> None:
    for item in build_notifications(event):
        stmt = (
            insert(models.Notification)
            .values(
                user_id=uuid.UUID(item["user_id"]),
                type=item["type"],
                title=item["title"],
                message=item["message"],
                dedup_key=item["dedup_key"],
            )
            .on_conflict_do_nothing(index_elements=["dedup_key"])
        )
        await session.execute(stmt)
    await session.commit()


async def ensure_group(client: aioredis.Redis) -> None:
    try:
        await client.xgroup_create(STREAM, GROUP, id="0", mkstream=True)
    except aioredis.ResponseError as exc:
        if "BUSYGROUP" not in str(exc):
            raise


async def process_entries(client: aioredis.Redis, batches: list) -> None:
    for _stream, entries in batches or []:
        for entry_id, fields in entries:
            try:
                event = json.loads(fields["data"])
                async with SessionLocal() as session:
                    await handle_event(session, event)
                await client.xack(STREAM, GROUP, entry_id)
            except Exception:
                logger.exception("Falha ao processar evento %s", entry_id)


async def run() -> None:
    logging.basicConfig(level=logging.INFO)
    client = aioredis.from_url(settings.redis_url, decode_responses=True)
    await ensure_group(client)
    logger.info("Worker de notificações iniciado.")

    # Reprocessa mensagens pendentes (entregues e não confirmadas) ao subir.
    pending = await client.xreadgroup(GROUP, CONSUMER, {STREAM: "0"}, count=100)
    await process_entries(client, pending)

    while True:
        messages = await client.xreadgroup(
            GROUP, CONSUMER, {STREAM: ">"}, count=10, block=5000
        )
        await process_entries(client, messages)


if __name__ == "__main__":
    asyncio.run(run())
```

- [ ] **Step 4: Rodar testes**

Run: `.venv/bin/pytest tests/test_notifications_worker.py -v`
Expected: `4 passed`

- [ ] **Step 5: Adicionar serviço `worker` ao `docker-compose.yml`**

Dentro de `services:`:

```yaml
  worker:
    build: ./apps/api
    command: python -m app.workers.notifications_worker
    environment:
      DATABASE_URL: postgresql+asyncpg://banklab:banklab@postgres:5432/banklab
      REDIS_URL: redis://redis:6379/0
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
```

- [ ] **Step 6: Validação ponta a ponta do fluxo de eventos**

```bash
docker compose up -d --build
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email": "maria@banklab.local", "password": "BankLab@123"}' | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')
CONTA=$(curl -s http://localhost:8000/accounts -H "Authorization: Bearer $TOKEN" | python3 -c 'import json,sys; print(json.load(sys.stdin)[0]["id"])')
curl -s -X POST http://localhost:8000/deposits \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -H "Idempotency-Key: validacao-e2e-1" \
  -d "{\"account_id\": \"$CONTA\", \"amount\": \"100.00\", \"description\": \"Validação e2e\"}"
sleep 2
curl -s http://localhost:8000/notifications -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

Expected: o depósito responde 201 e a lista de notificações contém uma nova "Depósito recebido" de R$ 100,00 (criada pelo worker via Redis Streams).

- [ ] **Step 7: Rodar a suíte completa**

Run: `.venv/bin/pytest -v`
Expected: todos os testes passam (≈ 40).

- [ ] **Step 8: Commit**

```bash
git add apps/api docker-compose.yml
git commit -m "feat: adiciona worker de notificacoes com redis streams e deduplicacao"
```

---

## Critérios de conclusão da Fase 2

Cobertura mínima da spec (seção 16, backend) atendida:

- login válido / inválido / inativo / token expirado / rota sem token ✓ (Task 4)
- listagem de contas ✓ (Task 6)
- depósito válido / inválido / idempotente / precisão decimal ✓ (Task 7)
- transferência válida / saldo insuficiente / conta inexistente / idempotente ✓ (Task 8)
- filtros de extrato ✓ (Task 9)
- notificação a partir de evento / reprocessamento sem duplicar ✓ (Task 12)
- marcação de notificação como lida ✓ (Task 11)

Validações finais:

- `.venv/bin/pytest -v` → tudo verde.
- `docker compose up -d --build` → api, worker, web, postgres, redis no ar.
- Migrations rodam no boot do container da api.
- `docker compose exec api python -m app.seed` é idempotente.
- Fluxo manual depósito → evento → notificação funciona (Step 6 da Task 12).
