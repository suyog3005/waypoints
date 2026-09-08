"""Shadow Finder: identifies overlapping/dependent block requests.

Pure functions (no DB/Kafka) so they can be unit-tested in isolation.
Implements architecture Section 17: group requests by affected resource (track)
and find clusters of transitively-overlapping time windows — the merge
candidates the optimizer consumes.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class RequestWindow:
    request_id: uuid.UUID
    track_id: uuid.UUID
    start: datetime
    end: datetime


def group_by_track(windows: list[RequestWindow]) -> dict[uuid.UUID, list[RequestWindow]]:
    """Group windows by their track (affected resource)."""
    grouped: dict[uuid.UUID, list[RequestWindow]] = {}
    for w in windows:
        grouped.setdefault(w.track_id, []).append(w)
    return grouped


def find_overlapping_clusters(
    windows: list[RequestWindow],
) -> dict[uuid.UUID, list[list[RequestWindow]]]:
    """For each track, return clusters of transitively-overlapping windows.

    A cluster with a single window means that request does not overlap any other
    on that track. Clusters with more than one window are merge candidates
    (Section 17).
    """
    result: dict[uuid.UUID, list[list[RequestWindow]]] = {}
    for track_id, track_windows in group_by_track(windows).items():
        result[track_id] = _cluster(track_windows)
    return result


def _cluster(windows: list[RequestWindow]) -> list[list[RequestWindow]]:
    """Sweep sorted windows, grouping those that overlap the running cluster."""
    ordered = sorted(windows, key=lambda w: (w.start, w.end))
    clusters: list[list[RequestWindow]] = []
    current: list[RequestWindow] = []
    current_end: datetime | None = None
    for w in ordered:
        if not current:
            current = [w]
            current_end = w.end
        elif w.start <= current_end:  # overlaps the running cluster
            current.append(w)
            if w.end > current_end:
                current_end = w.end
        else:
            clusters.append(current)
            current = [w]
            current_end = w.end
    if current:
        clusters.append(current)
    return clusters
