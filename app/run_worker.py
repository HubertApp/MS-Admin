# run_worker.py
import asyncio
import logging
from faststream import FastStream
from app.core.broker import broker
from app.workers.callbacks.email import email_router

logging.basicConfig(level=logging.INFO)
broker.include_router(email_router)

app = FastStream(broker)

if __name__ == "__main__":
    asyncio.run(app.run())