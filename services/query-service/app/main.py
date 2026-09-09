"""Query Service entrypoint.

Serves reads via Redis cache-aside, falling back to the Read Store on a cache
miss (see docs/application_architecture_flow.md, Sections 5–6). The read path
never touches Kafka — it goes frontend -> gateway -> query-service -> (Redis |
Read Store) (Section 6).
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import config  # noqa: F401  (ensures READ_STORE_URL is set before db imports)
from app.cache import Cache
from app.config import settings
from app.routers import basegraph, blocks, plans, tracks, trains, train_positions

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Best-effort: if Redis is down the Cache degrades to no-cache (see cache.py).
    app.state.cache = Cache(url=settings.redis_url, default_ttl=settings.cache_ttl_seconds)
    logger.info(
        "Query Service started (cache=%s).", "on" if app.state.cache.available else "off"
    )
    yield
    logger.info("Query Service stopped.")


app = FastAPI(title="Query Service", lifespan=lifespan)
app.include_router(plans.router)
app.include_router(blocks.router)
app.include_router(tracks.router)
app.include_router(trains.router)
app.include_router(basegraph.router)
app.include_router(train_positions.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
