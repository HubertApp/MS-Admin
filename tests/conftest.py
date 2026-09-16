"""Fixtures partagées : toute la suite tourne hors ligne.

Les variables d'environnement sont posées AVANT tout import de `app` :
`app.core.database` instancie `AsyncIOMotorClient(secrets.DATABASE_URL)` à
l'import, et la valeur par défaut `<DATABASE_URL>` n'est pas une URI valide.
Motor est paresseux : aucune connexion n'est ouverte.
"""
import os

os.environ["DATABASE_URL"] = "mongodb://localhost:27017"
os.environ["RABBITMQ_URL"] = "amqp://guest:guest@localhost:5672/"
os.environ["TRANSPORT_DATA_GOUV_API_URL"] = "https://transport.test/api"
os.environ["TRANSPORT_DATA_GOUV_API_TOKEN"] = "test-token"

from unittest.mock import AsyncMock  # noqa: E402

import httpx  # noqa: E402
import pytest  # noqa: E402
from mongomock_motor import AsyncMongoMockClient  # noqa: E402

import app.clients.france_transport_fournisseur as france_transport_module  # noqa: E402
import app.core.database as database_module  # noqa: E402
import app.graphql.types.registred_transit_network as types_module  # noqa: E402
import app.services.transit_network_service as service_module  # noqa: E402
from app.core.broker import broker  # noqa: E402
from app.graphql.inputs.registred_transit_networks import TransitNetworkInput  # noqa: E402

VALEURS_RESEAU_PAR_DEFAUT = {
    "fournisseur_id": "FR_TRANSPORT_GOUV",
    "external_id": "net-1",
    "name": "Réseau test",
    "country_code": "FR",
    "city_or_region": "Paris",
}


@pytest.fixture
def mongo_collection(monkeypatch):
    """Collection MongoDB en mémoire, neuve pour chaque test.

    Les modules importent la collection par son nom : il faut la remplacer
    dans chacun d'eux, patcher `app.core.database` seul serait sans effet.
    """
    collection = AsyncMongoMockClient()["admin_db"]["registered_transit_network"]
    for module in (database_module, service_module, types_module):
        monkeypatch.setattr(module, "registred_transit_network", collection)
    return collection


@pytest.fixture
def published(monkeypatch):
    """Remplace la publication RabbitMQ pour inspecter les messages émis."""
    publish = AsyncMock()
    monkeypatch.setattr(broker, "publish", publish)
    return publish


@pytest.fixture
def http_mock(monkeypatch):
    """Installe un handler HTTP à la place de l'API transport.data.gouv.

    Renvoie la liste des requêtes reçues, remplie au fil des appels.
    """
    vrai_client = httpx.AsyncClient

    def installer(handler):
        requetes = []

        def enregistrer(request):
            requetes.append(request)
            return handler(request)

        monkeypatch.setattr(
            france_transport_module.httpx,
            "AsyncClient",
            lambda **kwargs: vrai_client(transport=httpx.MockTransport(enregistrer), **kwargs),
        )
        return requetes

    return installer


@pytest.fixture
def network_input():
    def construire(**overrides):
        return TransitNetworkInput(**{**VALEURS_RESEAU_PAR_DEFAUT, **overrides})

    return construire


@pytest.fixture
def network_doc():
    def construire(**overrides):
        return {**VALEURS_RESEAU_PAR_DEFAUT, **overrides}

    return construire
