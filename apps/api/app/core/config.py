from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://banklab:banklab@localhost:5432/banklab"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "change-me-local-secret"
    jwt_expires_in_minutes: int = 60
    testing: bool = False


settings = Settings()
