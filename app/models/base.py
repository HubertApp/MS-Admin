from datetime import datetime
from typing import Any

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func

# Configuration optionnelle pour nommer les contraintes automatiquement
# (Très utile pour Alembic afin d'éviter les noms aléatoires)
naming_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

class Base(AsyncAttrs, DeclarativeBase):
    """
    Classe de base pour tous les modèles SQLAlchemy.
    """
    metadata = MetaData(naming_convention=naming_convention)

    # Optionnel : Représentation string automatique pour le debug
    def __repr__(self) -> str:
        cols = []
        for col in self.__table__.columns.keys():
            val = getattr(self, col)
            cols.append(f"{col}={val}")
        return f"<{self.__class__.__name__}({', '.join(cols)})>"

# --- BONUS : Un Mixin pour les dates ---
# Au lieu de réécrire created_at/updated_at dans chaque table
class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), 
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), 
        onupdate=func.now(), 
        nullable=False
    )