import asyncio
import logging
from faststream import FastStream
from app.core.broker import broker
from app.core.config import properties
from app.workers.callbacks.ingestion_callback import router

logging.basicConfig(level=properties.LOG_LEVEL.upper())

broker.include_router(router)

app = FastStream(broker)

if __name__ == "__main__":
    asyncio.run(app.run())
