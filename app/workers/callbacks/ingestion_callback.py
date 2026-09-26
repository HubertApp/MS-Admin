from typing import Literal, Optional

from faststream.rabbit import RabbitRouter
from pydantic import BaseModel

from app.core.topology import GTFS_INGESTION_RESULT
from app.graphql.types.registred_transit_network import TransitNetworkStatus
from app.services.transit_network_service import TransitNetworkService
from app.workers.publishers.notification_publisher import publish_aggregation_result

# Conservé pour les scripts de test qui l'importent ; la topologie fait foi.
INGESTION_RESULT_QUEUE = GTFS_INGESTION_RESULT.name

STATUS_BY_RESULT = {
    "ok": TransitNetworkStatus.DATA_AVAILABLE,
    "error": TransitNetworkStatus.AGGREGATION_ERROR,
}

router = RabbitRouter()


class IngestionResultEvent(BaseModel):
    network_id: str
    status: Literal["ok", "error"]
    error: Optional[str] = None


@router.subscriber(GTFS_INGESTION_RESULT)
async def handle_ingestion_result(message: IngestionResultEvent):
    nouveau_statut = STATUS_BY_RESULT[message.status]

    if message.error:
        print(f"Ingestion en erreur pour {message.network_id} : {message.error}", flush=True)

    trouve = await TransitNetworkService.set_status(message.network_id, nouveau_statut)
    if not trouve:
        print(f"Reseau introuvable, statut ignore : {message.network_id}", flush=True)
        return

    print(f"Statut de {message.network_id} passe a {nouveau_statut.value}", flush=True)

    await _notifier_admin(message)


async def _notifier_admin(message: IngestionResultEvent) -> None:
    """Previent MS-notifications, sans jamais faire echouer le traitement.

    Le statut est deja ecrit en base a ce stade. Une exception qui remonterait
    d'ici ferait rejeter le message d'ingestion sans remise en file : il serait
    perdu alors que le travail utile est fait.
    """
    try:
        reseau = await TransitNetworkService.find_by_external_id(message.network_id)
        await publish_aggregation_result(
            network_id=message.network_id,
            network_name=(reseau or {}).get("name"),
            status=message.status,
            error=message.error,
        )
        print(
            f"Notification admin publiee pour {message.network_id} "
            f"(status={message.status})",
            flush=True,
        )
    except Exception as erreur:
        print(
            f"Notification admin non publiee pour {message.network_id} : {erreur}",
            flush=True,
        )
