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
