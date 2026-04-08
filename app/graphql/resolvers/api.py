import strawberry
from typing import List

from app.clients.factory import FournisseurFactory
from app.graphql.types.standardized_api import StandardApi



async def resolve_search_api(fournisseur_id: str) -> List[StandardApi]:
        # 1. On récupère le bon adaptateur (ex: FranceTransportProvider)
        fournisseur = FournisseurFactory.get_fournisseur(fournisseur_id)

        # 2. L'adaptateur fait l'appel HTTP à transport.data.gouv.fr et renvoie des objets StandardDataset
        results = await fournisseur.search()

        return results
