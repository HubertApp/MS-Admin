import pytest

from app.graphql.inputs.transit_network_datasets import DatasetsInput
from app.graphql.types.registred_transit_network import (
    STATUS_LABELS,
    Resource,
    TransitNetwork,
    TransitNetworkStatus,
    build_transit_network,
)


class TestBuildTransitNetwork:
    def test_retire_l_id_mongo_et_convertit_les_ressources(self, network_doc):
        ressource = {"title": "GTFS", "format": "GTFS", "endpoint_url": "https://data.test/gtfs.zip"}

        reseau = build_transit_network(
            network_doc(_id="identifiant-mongo", resources=[ressource], status="DATA_AVAILABLE")
        )

        assert isinstance(reseau, TransitNetwork)
        assert reseau.resources == [Resource(**ressource)]
        assert reseau.status is TransitNetworkStatus.DATA_AVAILABLE

    @pytest.mark.parametrize("overrides", [{}, {"status": None}, {"status": ""}])
    def test_statut_en_attente_par_defaut(self, network_doc, overrides):
        reseau = build_transit_network(network_doc(**overrides))

        assert reseau.status is TransitNetworkStatus.PENDING_AGGREGATION
        assert reseau.resources == []


def test_chaque_statut_a_un_libelle():
    assert set(STATUS_LABELS) == set(TransitNetworkStatus)


class TestResolveReference:
    @pytest.mark.parametrize("cle", ["externalId", "external_id"])
    async def test_retrouve_le_reseau(self, mongo_collection, network_doc, cle):
        await mongo_collection.insert_one(network_doc())

        reseau = await TransitNetwork.resolve_reference(**{cle: "net-1"})

        assert reseau.external_id == "net-1"
        assert reseau.name == "Réseau test"

    async def test_renvoie_none_si_le_reseau_est_introuvable(self, mongo_collection):
        assert await TransitNetwork.resolve_reference(externalId="absent") is None


def test_datasets_input_ressources_vides_et_non_partagees():
    valeurs = dict(
        fournisseur_id="FR_TRANSPORT_GOUV",
        external_id="ds-1",
        name="Réseau",
        country_code="FR",
        city_or_region="Lyon",
    )

    premier = DatasetsInput(**valeurs)
    second = DatasetsInput(**valeurs)

    assert premier.resources == []
    assert premier.resources is not second.resources
