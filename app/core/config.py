from typing import Optional
from pydantic import PostgresDsn, RedisDsn, AmqpDsn, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # --- 1. Config Générale ---
    APP_NAME: str = "Microservice Admin"
    DEBUG: bool = True # Mettre à False en prod
    API_PREFIX: str = "/v1/admin"
    TRANSPORT_DATA_GOUV_API_TOKEN: str = "<TOKEN>"
    TRANSPORT_DATA_GOUV_API_URL: str = "<URL>"
    # --- 3. Message Broker (RabbitMQ / FastStream) ---
    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672/"
    # --- 4. Config Technique ---
    DATABASE_URL: str = "<DATABASE_URL>"
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )
settings = Settings()