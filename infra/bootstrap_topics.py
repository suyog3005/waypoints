"""Bootstrap Kafka topics for local development.

Creates the topics defined in `contracts.events.topics` (architecture Section 14)
if they do not already exist. Run after starting the broker:

    docker compose -f infra/docker-compose.yml up -d
    python infra/bootstrap_topics.py

Requires `aiokafka` (already a dependency of the command/optimization services).
"""

import asyncio
import os
import sys
from pathlib import Path

# Make the repo root importable so `contracts` resolves when run as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aiokafka.admin import AIOKafkaAdminClient  # noqa: E402
from contracts.events.topics import Topics  # noqa: E402

BROKERS = os.environ.get("KAFKA_BROKERS", "localhost:9092")

# Topics to create, with partition/replication counts.
TOPIC_CONFIGS = {
    Topics.PLAN_COMMANDS: {"partitions": 3, "replication_factor": 1},
    Topics.TRAIN_EVENTS: {"partitions": 3, "replication_factor": 1},
    Topics.TRACK_EVENTS: {"partitions": 3, "replication_factor": 1},
    Topics.OPTIMIZATION_REQUESTS: {"partitions": 3, "replication_factor": 1},
    Topics.OPTIMIZATION_RESULTS: {"partitions": 3, "replication_factor": 1},
    Topics.ASSET_EVENTS: {"partitions": 1, "replication_factor": 1},
    Topics.RESTRICTION_EVENTS: {"partitions": 1, "replication_factor": 1},
    Topics.MAINTENANCE_EVENTS: {"partitions": 1, "replication_factor": 1},
    Topics.ALERTS: {"partitions": 1, "replication_factor": 1},
}


async def main() -> None:
    admin = AIOKafkaAdminClient(bootstrap_servers=BROKERS)
    await admin.start()
    try:
        existing = set(await admin.list_topics())
        to_create = {name: cfg for name, cfg in TOPIC_CONFIGS.items() if name not in existing}
        if not to_create:
            print(f"All {len(TOPIC_CONFIGS)} topics already exist on {BROKERS}.")
            return
        await admin.create_topics(
            [
                {
                    "topic": name,
                    "num_partitions": cfg["partitions"],
                    "replication_factor": cfg["replication_factor"],
                }
                for name, cfg in to_create.items()
            ]
        )
        print(f"Created {len(to_create)} topic(s): {', '.join(sorted(to_create))}")
    finally:
        await admin.stop()


if __name__ == "__main__":
    asyncio.run(main())
