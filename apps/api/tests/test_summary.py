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
    assert body["total_balance"] == "0.00"
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


async def test_summary_exclui_transacoes_pendentes_das_somas(client, session):
    maria = await create_user(session)
    conta = await create_account(session, maria, balance=Decimal("100.00"))
    now = dt.datetime.now(dt.timezone.utc)
    session.add_all(
        [
            models.Transaction(
                account_id=conta.id,
                type="deposit",
                status="pending",
                amount=Decimal("999.00"),
                created_at=now,
            ),
            models.Transaction(
                account_id=conta.id,
                type="transfer_out",
                status="pending",
                amount=Decimal("888.00"),
                created_at=now,
            ),
        ]
    )
    await session.commit()

    response = await client.get("/summary", headers=auth_headers(maria))
    body = response.json()
    assert body["monthly_inflow"] == "0.00"
    assert body["monthly_outflow"] == "0.00"


async def test_summary_nao_mistura_dados_de_outro_usuario(client, session):
    maria = await create_user(session)
    joao = await create_user(session, name="João Souza", email="joao@banklab.local")
    await create_account(session, maria, balance=Decimal("10.00"))
    conta_joao = await create_account(session, joao, balance=Decimal("5000.00"))
    now = dt.datetime.now(dt.timezone.utc)
    session.add_all(
        [
            models.Transaction(
                account_id=conta_joao.id,
                type="deposit",
                status="completed",
                amount=Decimal("5000.00"),
                created_at=now,
            ),
            models.Notification(
                user_id=joao.id,
                title="Depósito recebido",
                message="Você recebeu um depósito.",
            ),
        ]
    )
    await session.commit()

    response = await client.get("/summary", headers=auth_headers(maria))
    body = response.json()
    assert body["total_balance"] == "10.00"
    assert body["monthly_inflow"] == "0.00"
    assert body["unread_notifications"] == 0
    assert body["latest_transactions"] == []
