from app.core.otel_setup import setup_otel, instrument_fastapi

setup_otel()

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from strawberry.fastapi import GraphQLRouter

from app.core.broker import broker
from app.core.config import properties
from app.core.topology import GTFS_FILE_AVAILABLE
from app.graphql.schema import schema


@asynccontextmanager
async def lifespan(app: FastAPI):
    await broker.connect()
    # C'est ce process qui publie gtfs.file.available, et un publish ne declare
    # que son exchange : sans cette declaration, une demande d'ingestion emise
    # avant le premier demarrage du worker aom-agregator serait perdue.
    await broker.declare_queue(GTFS_FILE_AVAILABLE)
    yield
    await broker.disconnect()


app = FastAPI(lifespan=lifespan)

graphql_app = GraphQLRouter(schema)
app.include_router(graphql_app, prefix=properties.GRAPHQL_PREFIX)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


instrument_fastapi(app)
