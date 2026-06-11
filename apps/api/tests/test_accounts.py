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
