"""Command Service entrypoint.

Handles state-changing operations (block requests), validates them, persists
them to the Operational DB, and publishes events to Kafka (see
docs/application_architecture_flow.md, Section 13).
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.kafka import KafkaPublisher
from app.routers import block_requests, event_injection, master_data

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.kafka = KafkaPublisher(
        brokers=settings.kafka_brokers, enabled=settings.kafka_enabled
    )
    await app.state.kafka.start()
    logger.info("Command Service started.")
    yield
    await app.state.kafka.stop()
    logger.info("Command Service stopped.")


app = FastAPI(title="Command Service", lifespan=lifespan)
app.include_router(block_requests.router)
app.include_router(event_injection.router)
app.include_router(master_data.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
