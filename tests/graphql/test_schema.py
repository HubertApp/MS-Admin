import httpx
import pytest

from app.graphql.schema import schema
from app.graphql.types.registred_transit_network import STATUS_LABELS, TransitNetworkStatus

URL_GTFS = "https://data.test/gtfs.zip"

CHAMPS_RESEAU = "externalId name status statusLabel resources { title format endpointUrl }"

CREATE = f"""
mutation Create($data: TransitNetworkInput!) {{
  createTransitNetwork(data: $data) {{ {CHAMPS_RESEAU} }}
}}
"""

UPDATE = f"""
mutation Update($externalId: String!, $data: TransitNetworkInput!) {{
  updateTransitNetwork(externalId: $externalId, data: $data) {{ {CHAMPS_RESEAU} }}
}}
"""

RETRIGGER = f"""
mutation Retrigger($externalId: String!) {{
  retriggerAggregation(externalId: $externalId) {{ {CHAMPS_RESEAU} }}
}}
"""

DELETE = """
mutation Delete($externalId: String!) {
  deleteTransitNetwork(externalId: $externalId)
}
"""

LISTE = """
query Liste($actualPage: Int!, $limit: Int!) {
  getRegistredTransitNetworks(actualPage: $actualPage, limit: $limit) {
    totalCount totalPages limit offset
    items { externalId status statusLabel }
  }
}
"""

DATASETS = """
query Datasets($fournisseurId: String!) {
  searchTransitNetworksDatasets(fournisseurId: $fournisseurId) {
    externalId name cityOrRegion
  }
}
"""


def input_reseau(**overrides):
    donnees = {
        "fournisseurId": "FR_TRANSPORT_GOUV",
        "externalId": "net-1",
        "name": "Réseau test",
        "countryCode": "FR",
        "cityOrRegion": "Paris",
        "resources": [{"title": "GTFS", "format": "GTFS", "endpointUrl": URL_GTFS}],
    }
    donnees.update(overrides)
    return donnees


class TestCreateTransitNetwork:
    async def test_cree_le_reseau(self, mongo_collection, published):
        resultat = await schema.execute(CREATE, variable_values={"data": input_reseau()})

        assert resultat.errors is None
        assert resultat.data["createTransitNetwork"] == {
            "externalId": "net-1",
            "name": "Réseau test",
            "status": "PENDING_AGGREGATION",
            "statusLabel": "En attente d'agrégation",
            "resources": [{"title": "GTFS", "format": "GTFS", "endpointUrl": URL_GTFS}],
        }
        published.assert_awaited_once()

    async def test_expose_l_erreur_de_doublon(self, mongo_collection, published, network_doc):
        await mongo_collection.insert_one(network_doc())

        resultat = await schema.execute(CREATE, variable_values={"data": input_reseau()})

        assert resultat.data is None
        assert "existe déjà" in resultat.errors[0].message


class TestUpdateTransitNetwork:
    async def test_met_a_jour_le_reseau(self, mongo_collection, network_doc):
        await mongo_collection.insert_one(network_doc(status="DATA_AVAILABLE"))

        resultat = await schema.execute(
            UPDATE,
            variable_values={
                "externalId": "net-1",
                "data": input_reseau(name="Nouveau nom", status="OUT_OF_SERVICE"),
            },
        )

        assert resultat.errors is None
        reseau = resultat.data["updateTransitNetwork"]
        assert reseau["name"] == "Nouveau nom"
        assert reseau["status"] == "OUT_OF_SERVICE"
        assert reseau["statusLabel"] == "Hors service"

    async def test_expose_l_erreur_reseau_introuvable(self, mongo_collection):
        resultat = await schema.execute(
            UPDATE, variable_values={"externalId": "absent", "data": input_reseau()}
        )

        assert resultat.errors[0].message == "API introuvable."


class TestRetriggerAggregation:
    async def test_relance_l_agregation(self, mongo_collection, published, network_doc):
        await mongo_collection.insert_one(
            network_doc(
                status="AGGREGATION_ERROR",
                resources=[{"title": "GTFS", "format": "GTFS", "endpoint_url": URL_GTFS}],
            )
        )

        resultat = await schema.execute(RETRIGGER, variable_values={"externalId": "net-1"})

        assert resultat.errors is None
        assert resultat.data["retriggerAggregation"]["status"] == "PENDING_AGGREGATION"
        published.assert_awaited_once()

    async def test_expose_l_erreur_reseau_introuvable(self, mongo_collection, published):
        resultat = await schema.execute(RETRIGGER, variable_values={"externalId": "absent"})

        assert resultat.errors[0].message == "Réseau introuvable : absent"


@pytest.mark.parametrize("existe, attendu", [(True, True), (False, False)])
async def test_delete_transit_network(mongo_collection, network_doc, existe, attendu):
    if existe:
        await mongo_collection.insert_one(network_doc())

    resultat = await schema.execute(DELETE, variable_values={"externalId": "net-1"})

    assert resultat.errors is None
    assert resultat.data == {"deleteTransitNetwork": attendu}


class TestGetRegistredTransitNetworks:
    async def test_pagine_depuis_le_numero_de_page(self, mongo_collection, network_doc):
        await mongo_collection.insert_many([network_doc(external_id=f"net-{i}") for i in range(3)])

        resultat = await schema.execute(LISTE, variable_values={"actualPage": 2, "limit": 2})

        assert resultat.errors is None
        page = resultat.data["getRegistredTransitNetworks"]
        assert page["totalCount"] == 3
        assert page["totalPages"] == 2
        assert page["limit"] == 2
        assert page["offset"] == 2
        assert [item["externalId"] for item in page["items"]] == ["net-2"]

    @pytest.mark.parametrize("statut", list(TransitNetworkStatus))
    async def test_expose_le_libelle_du_statut(self, mongo_collection, network_doc, statut):
        await mongo_collection.insert_one(network_doc(status=statut.value))

        resultat = await schema.execute(LISTE, variable_values={"actualPage": 1, "limit": 10})

        item = resultat.data["getRegistredTransitNetworks"]["items"][0]
        assert item == {
            "externalId": "net-1",
            "status": statut.value,
            "statusLabel": STATUS_LABELS[statut],
        }


class TestSearchTransitNetworksDatasets:
    async def test_renvoie_les_datasets_du_fournisseur(self, http_mock):
        http_mock(
            lambda request: httpx.Response(
                200,
                json=[
                    {
                        "id": "ds-1",
                        "title": "Réseau de Lyon",
                        "type": "public-transit",
                        "covered_area": [{"nom": "Lyon"}],
                        "resources": [],
                    }
                ],
            )
        )

        resultat = await schema.execute(DATASETS, variable_values={"fournisseurId": "FR_TRANSPORT_GOUV"})

        assert resultat.errors is None
        assert resultat.data["searchTransitNetworksDatasets"] == [
            {"externalId": "ds-1", "name": "Réseau de Lyon", "cityOrRegion": "Lyon"}
        ]

    async def test_expose_l_erreur_fournisseur_inconnu(self):
        resultat = await schema.execute(DATASETS, variable_values={"fournisseurId": "INCONNU"})

        assert "non supporté" in resultat.errors[0].message
