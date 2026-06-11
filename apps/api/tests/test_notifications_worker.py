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


class FakeRedisClient:
    def __init__(self):
        self.acked = []

    async def xack(self, stream, group, entry_id):
        self.acked.append(entry_id)


async def test_entrada_com_falha_nao_recebe_ack(client, session):
    from app.workers import notifications_worker as worker

    fake = FakeRedisClient()
    batches = [("banklab.transactions", [("1-0", {"data": "{json-invalido"})])]
    await worker.process_entries(fake, batches)
    assert fake.acked == []


async def test_entrada_processada_recebe_ack(client, session):
    import json

    from app.workers import notifications_worker as worker

    fake = FakeRedisClient()
    batches = [
        (
            "banklab.transactions",
            [("1-0", {"data": json.dumps({"event_type": "outro.evento"})})],
        )
    ]
    await worker.process_entries(fake, batches)
    assert fake.acked == ["1-0"]
