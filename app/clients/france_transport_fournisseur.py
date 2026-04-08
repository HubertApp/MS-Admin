# app/clients/france_transport_provider.py
from datetime import datetime
from typing import List

import httpx
from app.clients.i_fournisseur import IFournisseur
from app.core.config import settings
from app.graphql.types.standardized_api import StandardApi, StandardResource


class FranceTransportFournisseur(IFournisseur):
    @property
    def fournisseur_id(self) -> str:
        return "FR_TRANSPORT_GOUV"

    async def search(self) -> List[StandardApi]:
        # 1. On récupère TOUS les datasets (sans paramètre)
        url = f"{settings.TRANSPORT_DATA_GOUV_API_URL}/datasets"
        headers = {}
        headers["Authorize"] = settings.TRANSPORT_DATA_GOUV_API_TOKEN
        async with httpx.AsyncClient(headers=headers) as client:
            response = await client.get(url)
            response.raise_for_status()
            all_datasets = response.json()

        results = []

        # 2. Filtrage "à la main" en Python pur
        for item in all_datasets:
            type = item.get("type", "").lower()

            # Si la recherche matche le titre ou l'URL
            if "public-transit" in type:
                results.append(self._map_to_standard(item))

        return results

    async def get_by_id(self, external_id: str) -> StandardApi | None:
        url = f"{settings.TRANSPORT_DATA_GOUV_API_URL}/datasets/{external_id}"

        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            if response.status_code == 404:
                return None
            response.raise_for_status()

            return self._map_to_standard(response.json())

    def _map_to_standard(self, raw_data: dict) -> StandardApi:
        """Le traducteur : passe du JSON FR aux types GraphQL (Strawberry)"""

        standard_resources = []
        for res in raw_data.get("resources", []):

            # Gestion robuste de la date (le format de l'API gouv est en ISO avec un 'Z')
            updated_str = res.get("updated")
            if updated_str:
                updated_dt = datetime.fromisoformat(updated_str.replace('Z', '+00:00'))
            else:
                updated_dt = datetime.now()

            standard_resources.append(StandardResource(
                title=res.get("title", "Sans titre"),
                format=res.get("format", "Inconnu"),
                # On privilégie l'URL directe du fichier si dispo, sinon l'URL de la page
                download_url=res.get("url") or res.get("original_url", ""),
                updated_at=updated_dt,
                filesize_bytes=res.get("filesize")
            ))

        return StandardApi(
            fournisseur_id=self.fournisseur_id,
            external_id=raw_data.get("id", ""),
            name=raw_data.get("title", ""),
            country_code="FR",
            # On tente de récupérer le nom de la ville ou de l'agglo via le publisher ou la zone couverte
            city_or_region=self._extract_region(raw_data),
            resources=standard_resources
        )

    def _extract_region(self, raw_data: dict) -> str:
        """Logique métier spécifique pour extraire la zone géographique du dataset français"""
        covered_areas = raw_data.get("covered_area", [])
        if covered_areas and len(covered_areas) > 0:
            return covered_areas[0].get("nom", "France")

        publisher = raw_data.get("publisher", {})
        return publisher.get("name", "France")