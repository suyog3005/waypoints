"""Optimization service entrypoint.

This service is a Kafka consumer worker (not an HTTP API). It subscribes to
optimization request topics, runs the planner (the vendored CP-SAT pipeline:
LightGBM priority classifier -> solver -> feasibility validator), and
publishes results (see docs/application_architecture_flow.md, Sections
16-20).

Run with:
    python -m app.main
"""

from __future__ import annotations

from app import config  # noqa: F401  (must import before db.session)
from app.consumer import main as run_consumer


def main() -> None:
    run_consumer()


if __name__ == "__main__":
    main()
