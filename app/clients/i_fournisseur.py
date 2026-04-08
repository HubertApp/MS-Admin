# app/clients/base_provider.py
from abc import ABC, abstractmethod
from typing import List

from app.graphql.types.standardized_api import StandardApi


class IFournisseur(ABC):
    @property
    @abstractmethod
    def fournisseur_id(self) -> str:
        pass

    @abstractmethod
    async def search(self, title: str = None, url: str = None) -> List[StandardApi] | None:
        """Doit retourner un dictionnaire standardisé ou None."""
        pass