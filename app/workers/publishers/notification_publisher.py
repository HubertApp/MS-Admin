"""Publication des événements métier à destination de MS-notifications.

MS-notifications est un service NestJS. Son transport RabbitMQ lit tout ce qui
arrive sur `notifications_queue` et attend une enveloppe `{"pattern", "data"}` :
c'est ce que produit un `ClientProxy.emit()` côté Nest, et le contrat que ce
module reproduit à la main.

Les paramètres de la queue reprennent ceux déclarés dans le `src/main.ts` de
MS-notifications (durable, rien d'autre). Toute divergence provoquerait un
PRECONDITION_FAILED au premier publish.

Cette queue n'a volontairement pas sa place dans `app/core/topology.py` : ce
fichier-là est le miroir strict de MS-aom-agregator et doit rester identique à
sa copie dans l'autre dépôt.
"""

from datetime import datetime, timezone
from typing import Optional

from faststream.rabbit import RabbitQueue

from app.core.broker import broker

NOTIFICATIONS_QUEUE = RabbitQueue("notifications_queue", durable=True)

TRANSIT_NETWORK_AGGREGATED_PATTERN = "transit_network_aggregated"


async def publish_aggregation_result(
    network_id: str,
    network_name: Optional[str],
    status: str,
    error: Optional[str] = None,
) -> None:
    """Signale le résultat d'une agrégation à MS-notifications.

    `status` reprend tel quel le vocabulaire de `gtfs.ingestion.result` (`ok` ou
    `error`) : la traduction en libellé et en objet de mail appartient au
    service de notification, pas ici.
    """
    await broker.publish(
        {
            "pattern": TRANSIT_NETWORK_AGGREGATED_PATTERN,
            "data": {
                "network_id": network_id,
                "network_name": network_name,
                "status": status,
                "error": error,
                "occurred_at": datetime.now(timezone.utc).isoformat(),
            },
        },
        queue=NOTIFICATIONS_QUEUE,
        persist=True,
    )
