import pytest
from faststream.rabbit import RabbitBroker, TestRabbitBroker
from pydantic import ValidationError

from app.core.topology import GTFS_INGESTION_RESULT
from app.workers.callbacks.ingestion_callback import router

# Broker dédié aux tests, défini une seule fois : inclure le router dans un
# nouveau broker à chaque test dupliquerait les subscribers.
broker_de_test = RabbitBroker()
broker_de_test.include_router(router)


async def publier(payload):
    async with TestRabbitBroker(broker_de_test) as broker:
        await broker.publish(payload, queue=GTFS_INGESTION_RESULT)


@pytest.mark.parametrize(
    "payload, statut_attendu",
    [
        ({"network_id": "net-1", "status": "ok"}, "DATA_AVAILABLE"),
        ({"network_id": "net-1", "status": "error", "error": "flux corrompu"}, "AGGREGATION_ERROR"),
    ],
)
async def test_met_a_jour_le_statut_du_reseau(mongo_collection, network_doc, payload, statut_attendu):
    await mongo_collection.insert_one(network_doc(status="PENDING_AGGREGATION"))

    await publier(payload)

    stocke = await mongo_collection.find_one({"external_id": "net-1"})
    assert stocke["status"] == statut_attendu


async def test_ignore_un_reseau_introuvable(mongo_collection, capsys):
    await publier({"network_id": "absent", "status": "ok"})

    assert "Reseau introuvable, statut ignore : absent" in capsys.readouterr().out


async def test_rejette_un_resultat_invalide(mongo_collection, network_doc):
    await mongo_collection.insert_one(network_doc(status="PENDING_AGGREGATION"))

    with pytest.raises(ValidationError):
        await publier({"network_id": "net-1", "status": "partiel"})

    stocke = await mongo_collection.find_one({"external_id": "net-1"})
    assert stocke["status"] == "PENDING_AGGREGATION"
