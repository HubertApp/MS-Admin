from typing import Optional
from pydantic import PostgresDsn, RedisDsn, AmqpDsn, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Secrets(BaseSettings):
    TRANSPORT_DATA_GOUV_API_TOKEN: str = "<TOKEN>"
    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672/"
    DATABASE_URL: str = "<DATABASE_URL>"
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )
secrets = Secrets()

class Properties(BaseSettings):
    APP_NAME: str = "Microservice Admin"
    DEBUG: bool = True
    API_PREFIX: str = "/v1/admin"
    GRAPHQL_PREFIX: str = "/graphql"
    LOG_LEVEL: str = "INFO"
    TRANSPORT_DATA_GOUV_API_URL: str = "<URL>"
    model_config = SettingsConfigDict(
        env_file="application.properties",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )
properties = Properties()