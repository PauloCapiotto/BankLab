from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models
from app.core.config import settings
from app.core.database import get_session
from app.core.errors import APIError
from app.core.security import create_access_token, verify_password
from app.modules.audit.service import record_audit
from app.modules.auth.deps import get_current_user
from app.modules.auth.schemas import LoginRequest, LoginResponse, UserOut

router = APIRouter(tags=["auth"])


@router.post("/auth/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest, session: AsyncSession = Depends(get_session)
) -> LoginResponse:
    result = await session.execute(
        select(models.User).where(models.User.email == payload.email)
    )
    user = result.scalar_one_or_none()
    if (
        user is None
        or not verify_password(payload.password, user.password_hash)
        or user.status != "active"
    ):
        raise APIError(401, "INVALID_CREDENTIALS", "E-mail ou senha inválidos.")

    await record_audit(
        session,
        actor_user_id=user.id,
        action="auth.login",
        entity_type="user",
        entity_id=user.id,
    )
    await session.commit()

    return LoginResponse(
        access_token=create_access_token(str(user.id)),
        token_type="bearer",
        expires_in=settings.jwt_expires_in_minutes * 60,
        user=UserOut(id=str(user.id), name=user.name, email=user.email),
    )


@router.get("/auth/me", response_model=UserOut)
async def me(user: models.User = Depends(get_current_user)) -> UserOut:
    return UserOut(id=str(user.id), name=user.name, email=user.email)
