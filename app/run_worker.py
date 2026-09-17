# run_worker.py

from app.core.otel_setup import setup_otel

setup_otel()

import asyncio
import logging
from faststream import FastStream
from app.core.broker import broker
from app.core.config import properties
from app.workers.callbacks.email import email_router

logging.basicConfig(level=properties.LOG_LEVEL)
broker.include_router(email_router)

app = FastStream(broker)

if __name__ == "__main__":
    asyncio.run(app.run())