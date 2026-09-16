from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.core.broker import broker
from app.core.topology import GTFS_FILE_AVAILABLE
from app.main import app


@pytest.fixture
def broker_neutralise(monkeypatch):
    monkeypatch.setattr(broker, "connect", AsyncMock())
    monkeypatch.setattr(broker, "declare_queue", AsyncMock())
    return broker


def test_la_route_graphql_repond(broker_neutralise, monkeypatch):
    # `disconnect` n'existe pas sur RabbitBroker (bug n°2) : on l'ajoute pour
    # que l'arrêt du TestClient ne masque pas ce smoke test.
    monkeypatch.setattr(broker_neutralise, "disconnect", AsyncMock(), raising=False)

    with TestClient(app) as client:
        reponse = client.post("/graphql", json={"query": "{ __typename }"})

    assert reponse.status_code == 200
    assert reponse.json() == {"data": {"__typename": "Query"}}
    broker_neutralise.declare_queue.assert_awaited_once_with(GTFS_FILE_AVAILABLE)


@pytest.mark.xfail(
    strict=True,
    raises=AttributeError,
    reason="Bug n°2 : le lifespan appelle broker.disconnect(), absent de FastStream 0.6.5 (close()/stop())",
)
def test_l_arret_de_l_application_ferme_le_broker(broker_neutralise, monkeypatch):
    monkeypatch.setattr(broker_neutralise, "close", AsyncMock())

    with TestClient(app):
        pass

    broker_neutralise.close.assert_awaited_once()
