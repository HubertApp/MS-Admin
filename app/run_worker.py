# run_worker.py

from app.core.otel_setup import setup_otel
setup_otel()

import asyncio
import logging
from faststream import FastStream
from app.core.broker import broker
from app.core.config import properties
from app.workers.callbacks.ingestion_callback import router
from app.workers.publishers.notification_publisher import NOTIFICATIONS_QUEUE

logging.basicConfig(level=properties.LOG_LEVEL.upper())

broker.include_router(router)

app = FastStream(broker)


@app.after_startup
async def declarer_topologie() -> None:
    """Déclare la queue de MS-notifications, qui ne nous appartient pas.

    `broker.publish` ne déclare rien : un message envoyé vers une queue absente
    est non routable, et `on_return_raises` le transforme en erreur. Sans cette
    déclaration, tout résultat d'ingestion traité avant le premier démarrage de
    MS-notifications perdrait sa notification. Les paramètres doivent rester
    identiques à ceux de son `src/main.ts`.
    """
    await broker.declare_queue(NOTIFICATIONS_QUEUE)

if __name__ == "__main__":
    asyncio.run(app.run())
