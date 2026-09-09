"""GET /basegraph — schematic track network (nodes + edges) for the map.

Serves the Read Store projections ``base_graph_node`` and ``base_graph_edge``
(populated by ``db.readstore.etl``). The base graph changes rarely, so the
frontend caches it for an hour; we still cache here (TTL 1 h) to absorb load.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.cache import Cache, cache_get_or_load, cache_key
from app.db import get_read_store
from app.schemas import BaseGraphOut
from db.readstore.models import BaseGraphEdge, BaseGraphNode

router = APIRouter(tags=["basegraph"])

_BASEGRAPH_TTL = 3600  # 1 hour


@router.get("/basegraph", response_model=BaseGraphOut)
def get_basegraph(
    request: Request,
    db: Session = Depends(get_read_store),
) -> dict:
    cache: Cache = request.app.state.cache
    key = cache_key("basegraph")

    def loader() -> dict:
        nodes = db.scalars(select(BaseGraphNode).order_by(BaseGraphNode.node_key)).all()
        edges = db.scalars(select(BaseGraphEdge).order_by(BaseGraphEdge.edge_key)).all()
        return {
            "nodes": [
                {
                    "id": n.node_key,
                    "x": n.x,
                    "y": n.y,
                    "type": n.node_type,
                    "name": n.name,
                }
                for n in nodes
            ],
            "edges": [
                {
                    "id": e.edge_key,
                    "from_": e.from_node,
                    "to": e.to_node,
                    "track_id": e.track_id,
                }
                for e in edges
            ],
        }

    return cache_get_or_load(cache, key, loader, ttl=_BASEGRAPH_TTL)
