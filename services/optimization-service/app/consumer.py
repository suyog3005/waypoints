"""Kafka consumer for the optimization service.

Subscribes to the optimization request topics and, on each event, runs the
planner and publishes an ``optimization.result`` event back to the results
topic. This is the "intelligence" half of the real-time loop (architecture
Section 10).
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone

from aiokafka import AIOKafkaConsumer

from app.config import settings
from app.planner import run_optimization
from contracts.events import (
    EVENT_REGISTRY,
    OptimizationRequested,
    OptimizationResult,
    make_event,
)
from contracts.events.topics import Topics

logger = logging.getLogger(__name__)


def _parse_event(raw: bytes):
    """Deserialize a Kafka message into a typed event, or None if unknown."""
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        logger.warning("Skipping non-JSON message: %r", raw[:120])
        return None
    event_type = data.get("event_type")
    cls = EVENT_REGISTRY.get(event_type)
    if cls is None:
        logger.warning("Unknown event_type: %s", event_type)
        return None
    try:
        return cls.model_validate(data)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to validate %s: %s", event_type, exc)
        return None


async def _handle_optimization_requested(event: OptimizationRequested) -> None:
    """Run the planner for a request and publish the result event."""
    payload = event.payload
    track_id = payload.get("track_id")
    section_id = payload.get("section_id")
    track_uuid = uuid.UUID(track_id) if track_id else None
    section_uuid = uuid.UUID(section_id) if section_id else None

    outcome = run_optimization(
        track_id=track_uuid,
        section_id=section_uuid,
        triggered_by_event_id=event.event_id,
        correlation_id=event.correlation_id,
    )

    if outcome.plan_id is None:
        logger.info(
            "Optimization for track=%s section=%s -> no eligible requests",
            track_id,
            section_id,
        )
        return

    m = outcome.metrics
    result_event = make_event(
        OptimizationResult,
        payload={
            "plan_id": str(outcome.plan_id),
            "total_block_duration_minutes": m.total_block_duration_minutes if m else None,
            "affected_tracks_count": m.affected_tracks_count if m else None,
            "merged_requests_count": m.merged_requests_count if m else None,
            "metrics": {
                "block_count": m.block_count,
                "request_count": m.request_count,
            }
            if m
            else {},
        },
        occurred_at=datetime.now(timezone.utc),
        entity_type="plan",
        entity_id=outcome.plan_id,
        correlation_id=event.correlation_id,
    )
    await _publish(result_event)
    logger.info(
        "Optimization for track=%s section=%s -> plan=%s",
        track_id,
        section_id,
        outcome.plan_id,
    )


async def _publish(event) -> None:
    """Publish an event to its mapped topic (best-effort)."""
    from contracts.events.topics import EVENT_TOPIC_MAP

    topic = EVENT_TOPIC_MAP.get(event.event_type)
    if topic is None:
        logger.warning("No topic mapped for %s", event.event_type)
        return
    try:
        producer = await _producer.get()
        await producer.send_and_wait(topic, event.model_dump_json().encode())
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to publish %s: %s", event.event_type, exc)


class _Producer:
    """Lazily-started shared Kafka producer."""

    def __init__(self) -> None:
        self._instance = None

    async def get(self):
        if self._instance is None:
            from aiokafka import AIOKafkaProducer

            self._instance = AIOKafkaProducer(
                bootstrap_servers=settings.kafka_brokers,
                value_serializer=lambda v: v,
            )
            await self._instance.start()
        return self._instance

    async def stop(self) -> None:
        if self._instance is not None:
            await self._instance.stop()
            self._instance = None


_producer = _Producer()


async def consume() -> None:
    """Main consumer loop. Runs until cancelled."""
    consumer = AIOKafkaConsumer(
        Topics.OPTIMIZATION_REQUESTS,
        Topics.PLAN_COMMANDS,
        bootstrap_servers=settings.kafka_brokers,
        group_id=settings.kafka_consumer_group,
        auto_offset_reset="earliest",
        enable_auto_commit=True,
    )
    await consumer.start()
    logger.info("Optimization consumer started (group=%s)", settings.kafka_consumer_group)
    try:
        async for msg in consumer:
            event = _parse_event(msg.value)
            if event is None:
                continue
            if isinstance(event, OptimizationRequested):
                await _handle_optimization_requested(event)
            else:
                logger.debug("Ignoring event type %s", event.event_type)
    finally:
        await consumer.stop()
        await _producer.stop()
        logger.info("Optimization consumer stopped")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    try:
        asyncio.run(consume())
    except KeyboardInterrupt:
        logger.info("Interrupted")


if __name__ == "__main__":
    main()
