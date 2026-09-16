from datetime import datetime, timezone

import httpx
import pytest

from app.clients.france_transport_fournisseur import FranceTransportFournisseur

API_URL = "https://transport.test/api"


def dataset(**overrides):
    donnees = {
        "id": "ds-1",
        "title": "Réseau de Lyon",
        "type": "public-transit",
        "covered_area": [{"nom": "Lyon"}],
        "resources": [
            {
                "title": "GTFS Lyon",
                "format": "GTFS",
                "url": "https://data.test/lyon.zip",
                "updated": "2024-05-01T10:00:00Z",
                "filesize": 1234,
            }
        ],
    }
    donnees.update(overrides)
    return donnees


@pytest.fixture
def fournisseur():
    return FranceTransportFournisseur()


class TestSearch:
    async def test_appelle_l_api_avec_le_token(self, fournisseur, http_mock):
        requetes = http_mock(lambda request: httpx.Response(200, json=[]))

        await fournisseur.search()

        assert str(requetes[0].url) == f"{API_URL}/datasets"
        assert requetes[0].headers["Authorize"] == "test-token"

    async def test_ne_garde_que_les_reseaux_de_transport_public(self, fournisseur, http_mock):
        http_mock(
            lambda request: httpx.Response(
                200,
                json=[
                    dataset(id="transport", type="Public-Transit"),
                    dataset(id="velo", type="bike-sharing"),
                    {"id": "sans-type"},
                ],
            )
        )

        resultats = await fournisseur.search()

        assert [d.external_id for d in resultats] == ["transport"]

    async def test_propage_les_erreurs_http(self, fournisseur, http_mock):
        http_mock(lambda request: httpx.Response(500))

        with pytest.raises(httpx.HTTPStatusError):
            await fournisseur.search()


class TestGetById:
    async def test_renvoie_le_dataset_converti(self, fournisseur, http_mock):
        requetes = http_mock(lambda request: httpx.Response(200, json=dataset()))

        resultat = await fournisseur.get_by_id("ds-1")

        assert str(requetes[0].url) == f"{API_URL}/datasets/ds-1"
        assert resultat.external_id == "ds-1"
        assert resultat.name == "Réseau de Lyon"

    async def test_renvoie_none_si_le_dataset_n_existe_pas(self, fournisseur, http_mock):
        http_mock(lambda request: httpx.Response(404))

        assert await fournisseur.get_by_id("absent") is None

    async def test_propage_les_autres_erreurs_http(self, fournisseur, http_mock):
        http_mock(lambda request: httpx.Response(500))

        with pytest.raises(httpx.HTTPStatusError):
            await fournisseur.get_by_id("ds-1")

    @pytest.mark.xfail(
        strict=True,
        reason="Bug n°1 : get_by_id n'envoie pas le header Authorize, contrairement à search",
    )
    async def test_envoie_le_token(self, fournisseur, http_mock):
        requetes = http_mock(lambda request: httpx.Response(200, json=dataset()))

        await fournisseur.get_by_id("ds-1")

        assert requetes[0].headers.get("Authorize") == "test-token"


class TestMapToStandard:
    def test_convertit_un_dataset_complet(self, fournisseur):
        resultat = fournisseur._map_to_standard(dataset())

        assert resultat.fournisseur_id == "FR_TRANSPORT_GOUV"
        assert resultat.external_id == "ds-1"
        assert resultat.name == "Réseau de Lyon"
        assert resultat.country_code == "FR"
        assert resultat.city_or_region == "Lyon"
        ressource = resultat.resources[0]
        assert ressource.title == "GTFS Lyon"
        assert ressource.format == "GTFS"
        assert ressource.endpoint_url == "https://data.test/lyon.zip"
        assert ressource.filesize_bytes == 1234
        assert ressource.updated_at == datetime(2024, 5, 1, 10, 0, tzinfo=timezone.utc)

    def test_applique_les_valeurs_par_defaut(self, fournisseur):
        resultat = fournisseur._map_to_standard(
            {"resources": [{"original_url": "https://data.test/original.zip"}]}
        )

        assert resultat.external_id == ""
        assert resultat.name == ""
        ressource = resultat.resources[0]
        assert ressource.title == "Sans titre"
        assert ressource.format == "Inconnu"
        assert ressource.endpoint_url == "https://data.test/original.zip"
        assert ressource.filesize_bytes is None
        assert isinstance(ressource.updated_at, datetime)

    def test_url_vide_sans_url_ni_original_url(self, fournisseur):
        resultat = fournisseur._map_to_standard({"resources": [{}]})

        assert resultat.resources[0].endpoint_url == ""

    def test_sans_ressources(self, fournisseur):
        assert fournisseur._map_to_standard({}).resources == []


@pytest.mark.parametrize(
    "donnees, region_attendue",
    [
        ({"covered_area": [{"nom": "Lyon"}], "publisher": {"name": "SYTRAL"}}, "Lyon"),
        ({"covered_area": [], "publisher": {"name": "SYTRAL"}}, "SYTRAL"),
        ({"covered_area": [{}]}, "France"),
        ({"publisher": {}}, "France"),
        ({}, "France"),
    ],
)
def test_extract_region(fournisseur, donnees, region_attendue):
    assert fournisseur._extract_region(donnees) == region_attendue
