"""Provisions the fixed demo scenarios and solves all three approaches on
each, in-process (no HTTP round trip through the API's BackgroundTasks) so
every scenario is already computed before judges see it -- a 60s CP-SAT
solve live on stage is a dead demo.

Idempotent: a scenario is looked up by name rather than recreated, and a
(scenario, approach) pair already `complete` is left alone unless --force.
Run inside the api container so DATABASE_URL/src/api are all already
correct: `docker compose exec api python -m scripts.seed_demo`.
"""

import argparse

import pandas as pd

from src.config import BACKLOG_SIZE, DEFAULT_SEED, JOBS_PER_DAY

from api.models.tables import Approach, RunStatus
from api.services.persistence import (
    create_run,
    create_scenario,
    get_latest_run,
    get_result,
    get_scenario_by_name,
)
from api.services.solve_runner import run_scenario

# backlog_size choices: BACKLOG_SIZE (240) is the already-calibrated default
# that the 30-seed batch and every prior verification ran against, producing
# ~300 total jobs and a real gang-capacity bottleneck (n_possessions win
# universal, weighted_wait win ~70% of seeds) -- that's "Standard section".
# 2x pushes the same bottleneck harder for "Heavy backlog". 0.25x is small
# enough that gang capacity stops binding as hard, so most jobs fit either
# way and baseline's greedy has less waste for the solver to reclaim --
# "Light load", the honest small-gain case.
DEMO_SCENARIOS = [
    {"name": "Standard section", "seed": DEFAULT_SEED, "backlog_size": BACKLOG_SIZE, "jobs_per_day": JOBS_PER_DAY},
    {"name": "Heavy backlog", "seed": DEFAULT_SEED, "backlog_size": BACKLOG_SIZE * 2, "jobs_per_day": JOBS_PER_DAY},
    {"name": "Light load", "seed": DEFAULT_SEED, "backlog_size": BACKLOG_SIZE // 4, "jobs_per_day": JOBS_PER_DAY},
]


def _row(scenario_name: str, approach: Approach, run, skipped: bool) -> dict:
    metrics = get_result(run.id).metrics_json if run.status == RunStatus.complete else {}
    return {
        "scenario": scenario_name,
        "approach": approach.value,
        "status": run.status.value + (" (skipped)" if skipped else ""),
        "solve_time_s": run.solve_time_actual,
        "jobs_unscheduled": metrics.get("jobs_unscheduled"),
        "n_possessions": metrics.get("n_possessions"),
        "weighted_wait": metrics.get("weighted_wait"),
    }


def seed_scenario(spec: dict, force: bool) -> list[dict]:
    scenario = get_scenario_by_name(spec["name"])
    if scenario is None:
        scenario = create_scenario(
            seed=spec["seed"], backlog_size=spec["backlog_size"], jobs_per_day=spec["jobs_per_day"], name=spec["name"]
        )

    rows = []
    for approach in Approach:
        existing = get_latest_run(scenario.id, approach)
        if existing is not None and existing.status == RunStatus.complete and not force:
            rows.append(_row(spec["name"], approach, existing, skipped=True))
            continue

        run = create_run(scenario_id=scenario.id, approach=approach)
        run_scenario(run.id, scenario.id, approach, None)
        rows.append(_row(spec["name"], approach, get_latest_run(scenario.id, approach), skipped=False))
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="re-solve every approach even if already complete")
    args = parser.parse_args()

    rows = [row for spec in DEMO_SCENARIOS for row in seed_scenario(spec, args.force)]
    print(pd.DataFrame(rows).to_string(index=False))


if __name__ == "__main__":
    main()
