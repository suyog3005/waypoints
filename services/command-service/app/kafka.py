"""Best-effort Kafka producer for the Command Service.

If the broker is unreachable (e.g. local dev without Kafka running), publishing
degrades to logging so the write path still succeeds. The event is always
persisted to the `events` table by the caller, so no event is lost — Kafka is
the distribution channel, not the source of truth (architecture Section 14).
"""

import json
import logging
from typing import Any

from aiokafka import AIOKafkaProducer

logger = logging.getLogger(__name__)


class KafkaPublisher:
    def __init__(self, brokers: str, enabled: bool = True) -> None:
        self._brokers = brokers
        self._enabled = enabled
        self._producer: AIOKafkaProducer | None = None

    async def start(self) -> None:
        if not self._enabled:
            logger.info("Kafka publishing disabled; events will be logged only.")
            return
        self._producer = AIOKafkaProducer(
            bootstrap_servers=self._brokers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            key_serializer=lambda k: k.encode("utf-8") if k else None,
            acks="all",
        )
        try:
            await self._producer.start()
            logger.info("Kafka producer started (brokers=%s)", self._brokers)
        except Exception:
            logger.exception("Failed to start Kafka producer; falling back to log-only mode.")
            self._producer = None

    async def stop(self) -> None:
        if self._producer is not None:
            await self._producer.stop()
            self._producer = None

    async def publish(self, topic: str, key: str, value: dict[str, Any]) -> bool:
        """Publish an event. Returns True on success, False if unavailable/failed."""
        if self._producer is None:
            logger.warning("Kafka unavailable; event %s for topic %s not published.", key, topic)
            return False
        try:
            await self._producer.send_and_wait(topic, value=value, key=key)
            return True
        except Exception:
            logger.exception("Failed to publish event %s to topic %s", key, topic)
            return False
