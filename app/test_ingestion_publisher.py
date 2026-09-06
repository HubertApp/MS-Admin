import asyncio
import sys

from faststream.rabbit import RabbitBroker

from app.core.config import secrets
from app.workers.callbacks.ingestion_callback import INGESTION_RESULT_QUEUE


async def run_test(network_id: str, status: str, error: str | None):
    async with RabbitBroker(secrets.RABBITMQ_URL) as broker:
        payload = {"network_id": network_id, "status": status}
        if error:
            payload["error"] = error

        print(f"Envoi du faux resultat d'ingestion : {payload}")
        await broker.publish(payload, queue=INGESTION_RESULT_QUEUE)
        print("Message envoye avec succes")


if __name__ == "__main__":
    network_id = sys.argv[1] if len(sys.argv) > 1 else "test-network"
    status = sys.argv[2] if len(sys.argv) > 2 else "ok"
    error = sys.argv[3] if len(sys.argv) > 3 else None
    asyncio.run(run_test(network_id, status, error))
