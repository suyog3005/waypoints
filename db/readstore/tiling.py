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


def _bucket_index(dt: datetime) -> int:
    """Integer 15-minute bucket index for a datetime (UTC epoch-based)."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return int(dt.timestamp()) // (TIME_BUCKET_MINUTES * 60)


def _bucket_label(index: int) -> str:
    """Format a bucket index as ``yyyy-MM-ddTHH:mm`` (UTC)."""
    bucketed = datetime.fromtimestamp(index * TIME_BUCKET_MINUTES * 60, tz=timezone.utc)
    return bucketed.strftime("%Y-%m-%dT%H:%M")


def time_bucket(dt: datetime) -> str:
    """Quantize a datetime to a 15-minute bucket, formatted ``yyyy-MM-ddTHH:mm``.

    Bucketing and formatting are done in **UTC** so the tile ID is identical to
    the frontend's ``roundToInterval`` (which buckets on the UTC epoch and
    formats with ``timeZone: 'UTC'``). This keeps the write (ETL) and read
    (Query Service) paths — and the browser — in agreement regardless of the
    server or client local timezone.
    """
    return _bucket_label(_bucket_index(dt))


def tile_id(x: float, y: float, bucket: str) -> str:
    """Build a tile ID: ``{tileX}_{tileY}_{timeBucket}``."""
    tile_x = int(x // TILE_SIZE_M)
    tile_y = int(y // TILE_SIZE_M)
    return f"{tile_x}_{tile_y}_{bucket}"


def position_tile(x: float, y: float, from_time: datetime) -> str:
    """Convenience: tile ID for a position given its (x, y) and from_time."""
    return tile_id(x, y, time_bucket(from_time))


def position_tiles(x: float, y: float, from_time: datetime, to_time: datetime) -> list[str]:
    """All tile IDs a position occupies across its time window.

    A train is "on" its track between ``from_time`` and ``to_time``. Because the
    map is tiled in 3D (X, Y, Time) and the frontend requests the tile for the
    *current display-time bucket*, a position must be retrievable in **every**
    15-minute bucket it spans — not just its start bucket. This returns the
    tile ID for each bucket in ``[from_time, to_time]`` (inclusive).

    The frontend then filters by ``fromTime <= t <= toTime`` (``filterByTime``),
    so returning the position in each spanned bucket is correct and idempotent.
    """
    start = _bucket_index(from_time)
    end = _bucket_index(to_time)
    if end < start:
        end = start
    return [tile_id(x, y, _bucket_label(i)) for i in range(start, end + 1)]
