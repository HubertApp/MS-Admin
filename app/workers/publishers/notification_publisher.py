"""Publication de demandes de notification à destination de MS-notifications.

MS-notifications est un service NestJS. Son transport RabbitMQ lit tout ce qui
arrive sur `notifications_queue` et attend une enveloppe `{"pattern", "data"}` :
c'est ce que produit un `ClientProxy.emit()` côté Nest, et le contrat que ce
module reproduit à la main.

`notification_requested` est un contrat générique : MS-notifications ne rédige
ni ne décide rien, il persiste puis livre tel quel. Destinataire, objet et
contenu sont donc entièrement fournis ici par l'appelant.

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

NOTIFICATION_REQUESTED_PATTERN = "notification_requested"

TRIGGERED_BY = "ms-admin"


async def publish_notification(
    user_id: str,
    recipient_email: Optional[str],
    subject: Optional[str],
    content: str,
    type: str,
    channels: list[str],
) -> None:
    """Demande à MS-notifications de livrer un message déjà entièrement rédigé."""
    await broker.publish(
        {
            "pattern": NOTIFICATION_REQUESTED_PATTERN,
            "data": {
                "user_id": user_id,
                "recipient_email": recipient_email,
                "subject": subject,
                "content": content,
                "type": type,
                "channels": channels,
                "triggered_by": TRIGGERED_BY,
                "occurred_at": datetime.now(timezone.utc).isoformat(),
            },
        },
        queue=NOTIFICATIONS_QUEUE,
        persist=True,
    )
