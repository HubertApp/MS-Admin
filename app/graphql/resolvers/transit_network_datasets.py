from typing import List

from app.clients.factory import FournisseurFactory
from app.graphql.types.standardized_datasets import StandardDatasets



async def resolve_search_datasets(fournisseur_id: str) -> List[StandardDatasets]:
        fournisseur = FournisseurFactory.get_fournisseur(fournisseur_id)
        results = await fournisseur.search()
        return results
