"""Kafka topic names (architecture Section 14).

Centralized so producers and consumers agree on topic strings. Exact topic
names are finalized here for the MVP; the full list from Section 14 is
represented, with the ones actually used by the MVP marked.
"""

from __future__ import annotations


class Topics:
    # --- Used by the MVP -------------------------------------------------
    PLAN_COMMANDS = "plan.commands"  # Command Service -> (optimization, others)
    TRAIN_EVENTS = "train.events"  # external/operational train events
    TRACK_EVENTS = "track.events"  # external/operational track events
    OPTIMIZATION_REQUESTS = "optimization.requests"  # trigger the optimizer
    OPTIMIZATION_RESULTS = "optimization.results"  # optimizer -> (query, frontend)

    # --- Declared for completeness (Section 14); wired up as needed ------
    ASSET_EVENTS = "asset.events"
    RESTRICTION_EVENTS = "restriction.events"
    MAINTENANCE_EVENTS = "maintenance.events"
    ALERTS = "alerts"


# Mapping of event_type -> topic, for the events defined in contracts.events.
EVENT_TOPIC_MAP: dict[str, str] = {
    "block_request.submitted": Topics.PLAN_COMMANDS,
    "block_request.updated": Topics.PLAN_COMMANDS,
    "optimization.requested": Topics.OPTIMIZATION_REQUESTS,
    "optimization.result": Topics.OPTIMIZATION_RESULTS,
    "track.status_changed": Topics.TRACK_EVENTS,
    "train.delay": Topics.TRAIN_EVENTS,
}
