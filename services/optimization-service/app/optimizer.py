"""Optimizer: merges compatible block requests into blocks.

MVP strategy (architecture Sections 18, 20): for each track, merge overlapping
(and touching) requested windows into union blocks. One merged block replaces N
overlapping requests, minimizing repeated blocking. This deterministic
interval-union is explainable and correct for the MVP; hard safety constraints
and full constraint programming are backlog.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime

from app.shadow_finder import RequestWindow


@dataclass
class MergedBlock:
    track_id: uuid.UUID
    start: datetime
    end: datetime
    request_ids: list[uuid.UUID] = field(default_factory=list)

    @property
    def is_merged(self) -> bool:
        return len(self.request_ids) > 1

    @property
    def duration_minutes(self) -> int:
        return int((self.end - self.start).total_seconds() // 60)


def merge_windows(windows: list[RequestWindow]) -> list[MergedBlock]:
    """Merge overlapping/touching windows on a single track into union blocks.

    Classic interval-union: sort by start, sweep, and extend the current block
    while the next window starts before it ends.
    """
    ordered = sorted(windows, key=lambda w: (w.start, w.end))
    blocks: list[MergedBlock] = []
    for w in ordered:
        if blocks and w.start <= blocks[-1].end:
            last = blocks[-1]
            if w.end > last.end:
                last.end = w.end
            if w.request_id not in last.request_ids:
                last.request_ids.append(w.request_id)
        else:
            blocks.append(
                MergedBlock(track_id=w.track_id, start=w.start, end=w.end, request_ids=[w.request_id])
            )
    return blocks
