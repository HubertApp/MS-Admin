import pytest

from app.core.topology import GTFS_FILE_AVAILABLE
from app.graphql.inputs.registred_transit_networks import ResourceInput
from app.graphql.types.registred_transit_network import Resource, TransitNetworkStatus
from app.services.transit_network_service import TransitNetworkService

URL_GTFS = "https://data.test/gtfs.zip"
RESSOURCE_GTFS = {"title": "GTFS", "format": "GTFS", "endpoint_url": URL_GTFS}


class TestCreateTransitNetwork:
    async def test_insere_le_reseau_et_renvoie_le_type_graphql(
        self, mongo_collection, published, network_input
    ):
        data = network_input(resources=[ResourceInput(**RESSOURCE_GTFS)])

        reseau = await TransitNetworkService.create_transit_network(data)

        assert reseau.external_id == "net-1"
        assert reseau.resources == [Resource(**RESSOURCE_GTFS)]
        stocke = await mongo_collection.find_one({"external_id": "net-1"})
        assert stocke["name"] == "Réseau test"
        assert stocke["resources"] == [RESSOURCE_GTFS]

    async def test_statut_en_attente_par_defaut(self, mongo_collection, published, network_input):
        reseau = await TransitNetworkService.create_transit_network(network_input())

        assert reseau.status is TransitNetworkStatus.PENDING_AGGREGATION
        stocke = await mongo_collection.find_one({"external_id": "net-1"})
        assert stocke["status"] == "PENDING_AGGREGATION"

    async def test_respecte_le_statut_fourni(self, mongo_collection, published, network_input):
        data = network_input(status=TransitNetworkStatus.DATA_AVAILABLE)

        reseau = await TransitNetworkService.create_transit_network(data)

        assert reseau.status is TransitNetworkStatus.DATA_AVAILABLE
        stocke = await mongo_collection.find_one({"external_id": "net-1"})
        assert stocke["status"] == "DATA_AVAILABLE"

    async def test_refuse_un_external_id_deja_enregistre(
        self, mongo_collection, published, network_input, network_doc
    ):
        await mongo_collection.insert_one(network_doc())

        with pytest.raises(ValueError, match="net-1 existe déjà"):
            await TransitNetworkService.create_transit_network(network_input(endpoint_url=URL_GTFS))

        assert await mongo_collection.count_documents({}) == 1
        published.assert_not_awaited()

    async def test_publie_la_ressource_gtfs(self, mongo_collection, published, network_input):
        data = network_input(
            endpoint_url="https://api.test/fallback",
            resources=[
                ResourceInput(title="Doc", format="PDF", endpoint_url="https://data.test/doc.pdf"),
                ResourceInput(title="GTFS", format=" gtfs ", endpoint_url=URL_GTFS),
            ],
        )

        await TransitNetworkService.create_transit_network(data)

        published.assert_awaited_once_with(
            {"network_id": "net-1", "url": URL_GTFS, "format": "GTFS"},
            queue=GTFS_FILE_AVAILABLE,
            persist=True,
        )

    async def test_publie_l_endpoint_url_sans_ressource_gtfs(
        self, mongo_collection, published, network_input
    ):
        data = network_input(
            endpoint_url="https://api.test/flux",
            resources=[ResourceInput(title="Doc", format="PDF", endpoint_url="https://data.test/doc.pdf")],
        )

        await TransitNetworkService.create_transit_network(data)

        published.assert_awaited_once_with(
            {"network_id": "net-1", "url": "https://api.test/flux", "format": "GTFS"},
            queue=GTFS_FILE_AVAILABLE,
            persist=True,
        )

    async def test_ne_publie_rien_sans_source_gtfs(self, mongo_collection, published, network_input):
        await TransitNetworkService.create_transit_network(network_input())

        published.assert_not_awaited()


class TestSetStatus:
    async def test_met_a_jour_le_statut(self, mongo_collection, network_doc):
        await mongo_collection.insert_one(network_doc(status="PENDING_AGGREGATION"))

        trouve = await TransitNetworkService.set_status("net-1", TransitNetworkStatus.DATA_AVAILABLE)

        assert trouve is True
        stocke = await mongo_collection.find_one({"external_id": "net-1"})
        assert stocke["status"] == "DATA_AVAILABLE"

    async def test_renvoie_false_si_le_reseau_est_introuvable(self, mongo_collection):
        trouve = await TransitNetworkService.set_status("absent", TransitNetworkStatus.DATA_AVAILABLE)

        assert trouve is False


class TestRetriggerAggregation:
    async def test_refuse_un_reseau_introuvable(self, mongo_collection, published):
        with pytest.raises(ValueError, match="Réseau introuvable : absent"):
            await TransitNetworkService.retrigger_aggregation("absent")

        published.assert_not_awaited()

    async def test_refuse_un_reseau_sans_source_gtfs(self, mongo_collection, published, network_doc):
        await mongo_collection.insert_one(network_doc(status="AGGREGATION_ERROR"))

        with pytest.raises(ValueError, match="Aucune source GTFS exploitable pour net-1"):
            await TransitNetworkService.retrigger_aggregation("net-1")

        published.assert_not_awaited()
        stocke = await mongo_collection.find_one({"external_id": "net-1"})
        assert stocke["status"] == "AGGREGATION_ERROR"

    async def test_republie_et_repasse_en_attente(self, mongo_collection, published, network_doc):
        await mongo_collection.insert_one(
            network_doc(status="AGGREGATION_ERROR", resources=[RESSOURCE_GTFS])
        )

        reseau = await TransitNetworkService.retrigger_aggregation("net-1")

        published.assert_awaited_once_with(
            {"network_id": "net-1", "url": URL_GTFS, "format": "GTFS"},
            queue=GTFS_FILE_AVAILABLE,
            persist=True,
        )
        assert reseau.status is TransitNetworkStatus.PENDING_AGGREGATION
        stocke = await mongo_collection.find_one({"external_id": "net-1"})
        assert stocke["status"] == "PENDING_AGGREGATION"


class TestUpdateTransitNetwork:
    async def test_met_a_jour_et_conserve_le_statut_si_absent(
        self, mongo_collection, network_input, network_doc
    ):
        await mongo_collection.insert_one(network_doc(status="DATA_AVAILABLE"))

        reseau = await TransitNetworkService.update_transit_network(
            "net-1", network_input(name="Nouveau nom")
        )

        assert reseau.name == "Nouveau nom"
        assert reseau.status is TransitNetworkStatus.DATA_AVAILABLE
        stocke = await mongo_collection.find_one({"external_id": "net-1"})
        assert stocke["name"] == "Nouveau nom"
        assert stocke["status"] == "DATA_AVAILABLE"

    async def test_applique_le_statut_fourni(self, mongo_collection, network_input, network_doc):
        await mongo_collection.insert_one(network_doc(status="DATA_AVAILABLE"))

        reseau = await TransitNetworkService.update_transit_network(
            "net-1", network_input(status=TransitNetworkStatus.OUT_OF_SERVICE)
        )

        assert reseau.status is TransitNetworkStatus.OUT_OF_SERVICE
        stocke = await mongo_collection.find_one({"external_id": "net-1"})
        assert stocke["status"] == "OUT_OF_SERVICE"

    async def test_refuse_un_reseau_introuvable(self, mongo_collection, network_input):
        with pytest.raises(ValueError, match="API introuvable."):
            await TransitNetworkService.update_transit_network("absent", network_input())


class TestDeleteTransitNetwork:
    async def test_supprime_le_reseau(self, mongo_collection, network_doc):
        await mongo_collection.insert_one(network_doc())

        assert await TransitNetworkService.delete_transit_network("net-1") is True
        assert await mongo_collection.count_documents({}) == 0

    async def test_renvoie_false_si_le_reseau_est_introuvable(self, mongo_collection):
        assert await TransitNetworkService.delete_transit_network("absent") is False


class TestSearchRegistredTransitNetwork:
    @pytest.fixture
    async def sept_reseaux(self, mongo_collection, network_doc):
        documents = [network_doc(external_id=f"net-{i}", fournisseur_id="A") for i in range(5)]
        documents += [network_doc(external_id=f"autre-{i}", fournisseur_id="B") for i in range(2)]
        await mongo_collection.insert_many(documents)

    async def test_pagine_les_resultats(self, sept_reseaux):
        resultat = await TransitNetworkService.search_registred_transit_network(limit=2, offset=2)

        assert resultat["total_count"] == 7
        assert resultat["total_pages"] == 4
        assert resultat["limit"] == 2
        assert resultat["offset"] == 2
        assert [r.external_id for r in resultat["items"]] == ["net-2", "net-3"]

    async def test_filtre_par_fournisseur(self, sept_reseaux):
        resultat = await TransitNetworkService.search_registred_transit_network(fournisseur_id="B")

        assert resultat["total_count"] == 2
        assert resultat["total_pages"] == 1
        assert [r.external_id for r in resultat["items"]] == ["autre-0", "autre-1"]

    async def test_zero_page_quand_la_limite_est_nulle(self, sept_reseaux):
        resultat = await TransitNetworkService.search_registred_transit_network(limit=0)

        assert resultat["total_pages"] == 0

    async def test_ressources_absentes_converties_en_liste_vide(self, mongo_collection, network_doc):
        await mongo_collection.insert_one(network_doc(resources=None))

        resultat = await TransitNetworkService.search_registred_transit_network()

        assert resultat["items"][0].resources == []
