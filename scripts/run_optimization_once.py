"""Run the CP-SAT pipeline once for the seeded demo section, outside Kafka.

app/planner.py's run_optimization() is normally triggered by a Kafka event
(app/consumer.py); this script calls it directly so the demo stack doesn't
need Kafka/Redpanda running. Requires DATABASE_URL set to the operational DB
and the section already seeded (scripts/seed_from_pipeline.py).

Usage:
    python -m scripts.run_optimization_once
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OPT_SERVICE_DIR = REPO_ROOT / "services" / "optimization-service"
if str(OPT_SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(OPT_SERVICE_DIR))

from sqlalchemy import select  # noqa: E402

from app.planner import run_optimization  # noqa: E402
from db.models import Section  # noqa: E402
from db.session import SessionLocal  # noqa: E402
from scripts.seed_from_pipeline import SECTION_NAME  # noqa: E402


def main() -> None:
    with SessionLocal() as db:
        section = db.execute(select(Section).where(Section.name == SECTION_NAME)).scalar_one()
        section_id = section.id

    outcome = run_optimization(section_id=section_id)
    if outcome.plan_id is None:
        print(
            "No plan produced -- either no eligible SUBMITTED requests, or the "
            "solved schedule failed check.validate() (see the OptimizationRun "
            "row's error_message)."
        )
        return
    print(f"Plan {outcome.plan_id}")
    print(outcome.metrics)


if __name__ == "__main__":
    main()
