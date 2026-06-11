import uuid

import jwt as pyjwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app import models
from app.core.database import get_session
from app.core.errors import APIError
from app.core.security import decode_access_token

bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    session: AsyncSession = Depends(get_session),
) -> models.User:
    if credentials is None:
        raise APIError(401, "NOT_AUTHENTICATED", "Autenticação necessária.")
    try:
        payload = decode_access_token(credentials.credentials)
    except pyjwt.ExpiredSignatureError:
        raise APIError(401, "TOKEN_EXPIRED", "Sessão expirada. Faça login novamente.")
    except pyjwt.InvalidTokenError:
        raise APIError(401, "INVALID_TOKEN", "Token inválido.")

    user = await session.get(models.User, uuid.UUID(payload["sub"]))
    if user is None or user.status != "active":
        raise APIError(401, "INVALID_TOKEN", "Token inválido.")
    return user
