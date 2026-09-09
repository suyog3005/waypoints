"""Shared 3D tiling helpers (X, Y, Time).

Used by both the ETL (``db.readstore.etl``) and the Query Service
(``app.routers.train_positions``) so the tile-ID computation is identical on
the write and read paths. Keep this module dependency-light (no DB imports) so
it can be imported from anywhere.

The constants and ID format MUST match the frontend's ``lib/tile-management.ts``
(``DEFAULT_TILE_SIZE``, ``TIME_BUCKET_MINUTES``, and the
``"{x}_{y}_{yyyy-MM-ddTHH:mm}"`` tile-ID shape).
"""

from __future__ import annotations

from datetime import datetime, timezone

# Schematic tile size (meters) and time bucket (minutes).
TILE_SIZE_M = 10_000
TIME_BUCKET_MINUTES = 15


def time_bucket(dt: datetime) -> str:
    """Quantize a datetime to a 15-minute bucket, formatted ``yyyy-MM-ddTHH:mm``.

    Bucketing and formatting are done in **UTC** so the tile ID is identical to
    the frontend's ``roundToInterval`` (which buckets on the UTC epoch and
    formats with ``timeZone: 'UTC'``). This keeps the write (ETL) and read
    (Query Service) paths — and the browser — in agreement regardless of the
    server or client local timezone.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    epoch_seconds = int(dt.timestamp())
    minutes = epoch_seconds // (TIME_BUCKET_MINUTES * 60)
    bucketed = datetime.fromtimestamp(minutes * TIME_BUCKET_MINUTES * 60, tz=timezone.utc)
    return bucketed.strftime("%Y-%m-%dT%H:%M")


def tile_id(x: float, y: float, bucket: str) -> str:
    """Build a tile ID: ``{tileX}_{tileY}_{timeBucket}``."""
    tile_x = int(x // TILE_SIZE_M)
    tile_y = int(y // TILE_SIZE_M)
    return f"{tile_x}_{tile_y}_{bucket}"


def position_tile(x: float, y: float, from_time: datetime) -> str:
    """Convenience: tile ID for a position given its (x, y) and from_time."""
    return tile_id(x, y, time_bucket(from_time))
