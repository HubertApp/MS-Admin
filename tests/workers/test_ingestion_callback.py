import pytest
from faststream.rabbit import RabbitBroker, TestRabbitBroker
from pydantic import ValidationError

from app.core.topology import GTFS_INGESTION_RESULT
from app.workers.callbacks.ingestion_callback import router
from app.workers.publishers.notification_publisher import NOTIFICATIONS_QUEUE

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


async def test_notifie_l_admin_quand_l_agregation_reussit(mongo_collection, network_doc, published):
    await mongo_collection.insert_one(network_doc(status="PENDING_AGGREGATION"))

    await publier({"network_id": "net-1", "status": "ok"})

    published.assert_awaited_once()
    enveloppe = published.await_args.args[0]
    assert enveloppe["pattern"] == "transit_network_aggregated"
    assert enveloppe["data"]["network_id"] == "net-1"
    assert enveloppe["data"]["network_name"] == "Réseau test"
    assert enveloppe["data"]["status"] == "ok"
    assert enveloppe["data"]["error"] is None
    assert published.await_args.kwargs["queue"] is NOTIFICATIONS_QUEUE


async def test_notifie_l_admin_avec_la_raison_quand_l_agregation_echoue(
    mongo_collection, network_doc, published
):
    await mongo_collection.insert_one(network_doc(status="PENDING_AGGREGATION"))

    await publier({"network_id": "net-1", "status": "error", "error": "flux corrompu"})

    donnees = published.await_args.args[0]["data"]
    assert donnees["status"] == "error"
    assert donnees["error"] == "flux corrompu"


async def test_ne_notifie_pas_pour_un_reseau_introuvable(mongo_collection, published):
    await publier({"network_id": "absent", "status": "ok"})

    published.assert_not_awaited()


async def test_un_echec_de_notification_ne_fait_pas_perdre_le_message(
    mongo_collection, network_doc, published, capsys
):
    """Le statut est deja en base : laisser remonter l'exception rejetterait le
    message d'ingestion sans remise en file, pour rien."""
    await mongo_collection.insert_one(network_doc(status="PENDING_AGGREGATION"))
    published.side_effect = RuntimeError("broker indisponible")

    await publier({"network_id": "net-1", "status": "ok"})

    stocke = await mongo_collection.find_one({"external_id": "net-1"})
    assert stocke["status"] == "DATA_AVAILABLE"
    assert "Notification admin non publiee pour net-1" in capsys.readouterr().out


async def test_trace_la_notification_publiee(mongo_collection, network_doc, published, capsys):
    await mongo_collection.insert_one(network_doc(status="PENDING_AGGREGATION"))

    await publier({"network_id": "net-1", "status": "ok"})

    assert "Notification admin publiee pour net-1 (status=ok)" in capsys.readouterr().out
