"""Batch entry point: data_gen -> baseline/solver -> check, across many seeds.

For each of N_RUN_SEEDS scenarios, runs three approaches on the identical
scenario -- schedule_baseline, schedule_solver with ML-predicted weights,
and schedule_solver with ground-truth weights -- validates every result,
and reports baseline-vs-solver comparisons.
"""

import os
import time

import numpy as np
import pandas as pd

from src.baseline import schedule_baseline
from src.check import validate
from src.config import DEFAULT_SEED, N_RUN_SEEDS, PRIORITY_WEIGHTS, SOLVE_TIME_LIMIT
from src.data_gen import generate_dataset
from src.model import predicted_weights
from src.solver import ground_truth_weights, schedule_solver

PRIORITY_ORDER = ["Critical", "High", "Medium", "Low"]
APPROACHES = ["baseline", "solver_ml", "solver_gt"]
NUMERIC_METRICS = ["jobs_unscheduled", "n_possessions", "line_blocked_min", "weighted_wait"] + [
    f"wait_{cls}" for cls in PRIORITY_ORDER
]
OUTPUT_CSV = "outputs/run_comparison.csv"


def _weighted_wait(mean_wait_days: dict) -> float | None:
    """Single fairness score: true PRIORITY_WEIGHTS applied to each
    priority class's mean wait -- lower is better, comparable across
    approaches regardless of which weight scheme produced the schedule.
    None (not a partial sum) if any class has no placed jobs to average."""
    if any(mean_wait_days[cls] is None for cls in PRIORITY_ORDER):
        return None
    return sum(PRIORITY_WEIGHTS[cls] * mean_wait_days[cls] for cls in PRIORITY_ORDER)


def _run_one(approach: str, jobs_df: pd.DataFrame, trains_df: pd.DataFrame, windows_df: pd.DataFrame, segments_df: pd.DataFrame) -> dict:
    """Run one (approach, scenario) combination and validate it. Returns a
    flat result row; job_id-level outputs aren't kept, only the metrics."""
    if approach == "baseline":
        t0 = time.perf_counter()
        schedule, possessions, metrics = schedule_baseline(jobs_df, trains_df, windows_df)
        solve_time = time.perf_counter() - t0
        status = "N/A"
    else:
        weights = ground_truth_weights(jobs_df) if approach == "solver_gt" else predicted_weights(jobs_df)
        schedule, possessions, metrics, solve_info = schedule_solver(
            jobs_df, trains_df, windows_df, weights, time_limit=SOLVE_TIME_LIMIT
        )
        solve_time = solve_info["wall_clock_seconds"]
        status = solve_info["status"]

    violations = validate(schedule, possessions, segments_df, trains_df, windows_df, jobs_df)

    row = {
        "jobs_unscheduled": metrics["jobs_unscheduled"],
        "n_possessions": metrics["n_possessions"],
        "line_blocked_min": metrics["line_blocked_min"],
        "weighted_wait": _weighted_wait(metrics["mean_wait_days"]),
        "solve_time": solve_time,
        "status": status,
        "violations": len(violations),
    }
    for cls in PRIORITY_ORDER:
        row[f"wait_{cls}"] = metrics["mean_wait_days"][cls]
    return row


def run_comparison(n_seeds: int = N_RUN_SEEDS, seed: int = DEFAULT_SEED) -> pd.DataFrame:
    """Run baseline + solver(ML) + solver(ground truth) across n_seeds
    scenarios (drawn from `seed`'s RNG stream), validating every result.
    Returns the full per-seed, per-approach results table."""
    rng = np.random.default_rng(seed)
    seeds = rng.choice(1_000_000, size=n_seeds, replace=False)

    rows = []
    for s in seeds:
        segments, trains, jobs, windows = generate_dataset(seed=int(s))
        for approach in APPROACHES:
            row = _run_one(approach, jobs, trains, windows, segments)
            row["seed"] = int(s)
            row["approach"] = approach
            rows.append(row)
            print(row, flush=True)

    return pd.DataFrame(rows)


def report_comparison(result: pd.DataFrame, out_path: str = OUTPUT_CSV) -> None:
    """Print mean+-std per approach, mean % improvement of each solver
    approach over baseline, head-to-head win counts, and validation
    failures; export the full per-seed table to CSV."""
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    result.to_csv(out_path, index=False)
    print(f"\nFull per-seed results written to {out_path}")

    print("\n=== Mean +- std per approach ===")
    summary = result.groupby("approach")[NUMERIC_METRICS + ["solve_time"]].agg(["mean", "std"])
    print(summary.round(2).T)

    baseline = result[result["approach"] == "baseline"].set_index("seed")
    for solver_approach in ("solver_ml", "solver_gt"):
        solver = result[result["approach"] == solver_approach].set_index("seed")

        print(f"\n=== {solver_approach} vs baseline: mean % improvement (lower-is-better metrics) ===")
        pct_improvement = ((baseline[NUMERIC_METRICS] - solver[NUMERIC_METRICS]) / baseline[NUMERIC_METRICS] * 100).mean()
        print(pct_improvement.round(2))

        beats_possessions = solver["n_possessions"] < baseline["n_possessions"]
        beats_wait = solver["weighted_wait"] < baseline["weighted_wait"]
        print(f"\n{solver_approach}: beats baseline on n_possessions in {beats_possessions.sum()}/{len(beats_possessions)} seeds")
        if not beats_possessions.all():
            print(f"  loses (or ties) in seeds: {beats_possessions[~beats_possessions].index.tolist()}")
        print(f"{solver_approach}: beats baseline on weighted_wait in {beats_wait.sum()}/{len(beats_wait)} seeds")
        if not beats_wait.all():
            print(f"  loses (or ties) in seeds: {beats_wait[~beats_wait].index.tolist()}")

    print("\n=== check.validate() ===")
    bad = result[result["violations"] > 0]
    if bad.empty:
        print(f"Clean on every run: 0 violations across {len(result)} (seed, approach) runs.")
    else:
        print("VALIDATION FAILURES:")
        print(bad[["seed", "approach", "violations"]].to_string(index=False))


if __name__ == "__main__":
    result = run_comparison()
    report_comparison(result)
