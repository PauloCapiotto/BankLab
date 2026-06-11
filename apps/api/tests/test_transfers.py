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
