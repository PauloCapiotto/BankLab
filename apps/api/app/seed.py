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
