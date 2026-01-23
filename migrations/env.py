import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# 1. IMPORTS DE VOTRE PROJET
# On importe la config pour avoir l'URL de la BDD
from app.core.config import settings
# On importe la Base SQLAlchemy pour les métadonnées
from app.models.base import Base
# TRES IMPORTANT : Importez TOUS vos modèles ici
# Si vous ne le faites pas, Alembic ne verra pas vos tables !
from app.models.api import ApiModel  
# from app.models.user import UserModel (Exemple futur)

# Config Alembic
config = context.config

# Setup logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 2. LIEZ LES METADONNÉES
target_metadata = Base.metadata

# 3. CONFIGURATION DE L'URL (Surcharge celle de alembic.ini)
# On force l'URL à celle définie dans votre classe Settings (celle du .env)
config.set_main_option("sqlalchemy.url", settings.ASYNC_DATABASE_URL)


def run_migrations_offline() -> None:
    """Mode Offline (sans connexion active)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Mode Online (Le plus utilisé)."""
    # On crée un moteur asynchrone à partir de la config
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())