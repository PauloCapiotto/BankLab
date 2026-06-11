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
