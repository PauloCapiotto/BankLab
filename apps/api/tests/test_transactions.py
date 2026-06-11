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
