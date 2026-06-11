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
