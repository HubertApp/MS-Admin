from typing import Optional
from pydantic import PostgresDsn, RedisDsn, AmqpDsn, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # --- 1. Config Générale ---
    APP_NAME: str = "Microservice Admin"
    DEBUG: bool = True # Mettre à False en prod
    API_PREFIX: str = "/v1/admin"
    # --- 2. Base de Données ---
    DATABASE_URL: str = "postgresql+asyncpg://user:password@db:5432/ms_admin_db"
    
    @computed_field
    @property
    def ASYNC_DATABASE_URL(self) -> str:
        if self.DATABASE_URL and self.DATABASE_URL.startswith("postgresql://"):
            return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
        return self.DATABASE_URL
    # --- 3. Message Broker (RabbitMQ / FastStream) ---
    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672/"
    # --- 4. Config Technique ---
    model_config = SettingsConfigDict(
        env_file="../.env", 
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )
settings = Settings()