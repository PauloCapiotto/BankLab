from sqlalchemy import select

from app import models
from app.core.config import settings
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
    assert body["expires_in"] == settings.jwt_expires_in_minutes * 60
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
    assert response.json()["code"] == "INVALID_CREDENTIALS"


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


async def test_token_com_sub_invalido_retorna_401(client, session):
    await create_user(session)
    token = create_access_token("nao-e-um-uuid")
    response = await client.get(
        "/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401
    assert response.json()["code"] == "INVALID_TOKEN"
