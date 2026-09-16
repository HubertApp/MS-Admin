from unittest.mock import AsyncMock

import pytest

from app.clients.factory import FournisseurFactory
from app.graphql.resolvers.registred_transit_networks import resolve_get_registred_transit_network
from app.graphql.resolvers.transit_network_datasets import resolve_search_datasets
from app.graphql.types.registred_transit_network import PaginatedTransitNetworks
from app.services.transit_network_service import TransitNetworkService


@pytest.fixture
def recherche(monkeypatch):
    mock = AsyncMock(
        return_value={"total_count": 0, "total_pages": 0, "limit": 5, "offset": 0, "items": []}
    )
    monkeypatch.setattr(TransitNetworkService, "search_registred_transit_network", mock)
    return mock


class TestResolveGetRegistredTransitNetwork:
    async def test_calcule_l_offset_depuis_la_page(self, recherche):
        resultat = await resolve_get_registred_transit_network(actual_page=3, limit=5)

        recherche.assert_awaited_once_with(5, 10)
        assert isinstance(resultat, PaginatedTransitNetworks)

    async def test_offset_explicite_prioritaire(self, recherche):
        await resolve_get_registred_transit_network(actual_page=3, limit=5, offset=7)

        recherche.assert_awaited_once_with(5, 7)


async def test_resolve_search_datasets_delegue_au_fournisseur(monkeypatch):
    datasets = [object()]
    demandes = []

    class FournisseurFactice:
        async def search(self):
            return datasets

    def get_fournisseur(fournisseur_id):
        demandes.append(fournisseur_id)
        return FournisseurFactice()

    monkeypatch.setattr(FournisseurFactory, "get_fournisseur", get_fournisseur)

    resultat = await resolve_search_datasets("FR_TRANSPORT_GOUV")

    assert resultat is datasets
    assert demandes == ["FR_TRANSPORT_GOUV"]
