"""Background execution of one scheduling run. Dispatched via FastAPI
BackgroundTasks with a plain (non-async) function -- Starlette runs sync
background callables in a worker thread, off the event loop, which is what
keeps the API responsive during a multi-second CP-SAT solve."""

import time

from src.baseline import schedule_baseline
from src.check import validate
from src.config import PRIORITY_WEIGHTS, SOLVE_TIME_LIMIT
from src.data_gen import MINUTES_PER_DAY, generate_dataset
from src.model import predicted_weights
from src.solver import ground_truth_weights, schedule_solver

from api.models.tables import Approach, RunStatus
from api.services.persistence import get_scenario, save_result, update_run_status

PRIORITY_ORDER = ["Critical", "High", "Medium", "Low"]


def _weighted_wait(mean_wait_days: dict) -> float:
    """Single fairness score: PRIORITY_WEIGHTS applied to each priority
    class's mean wait, comparable across approaches regardless of which
    weight scheme produced the schedule."""
    return sum(PRIORITY_WEIGHTS[cls] * mean_wait_days[cls] for cls in PRIORITY_ORDER)


def run_scenario(run_id: int, scenario_id: int, approach: Approach, solve_time_limit: float | None) -> None:
    """Generate the scenario from its stored parameters, run `approach`,
    validate, and persist. Always leaves the run `complete` or `failed` --
    never stuck `running`, even on an unexpected exception."""
    try:
        update_run_status(run_id, RunStatus.running)
        scenario = get_scenario(scenario_id)

        segments, trains, jobs, windows = generate_dataset(
            seed=scenario.seed, jobs_per_day=scenario.jobs_per_day, backlog_size=scenario.backlog_size
        )

        if approach == Approach.baseline:
            t0 = time.perf_counter()
            schedule, possessions, metrics = schedule_baseline(jobs, trains, windows)
            solve_time_actual = round(time.perf_counter() - t0, 2)
            solver_status = "N/A"
        else:
            weights = ground_truth_weights(jobs) if approach == Approach.solver_gt else predicted_weights(jobs)
            time_limit = solve_time_limit if solve_time_limit is not None else SOLVE_TIME_LIMIT
            schedule, possessions, metrics, solve_info = schedule_solver(jobs, trains, windows, weights, time_limit=time_limit)
            solve_time_actual = solve_info["wall_clock_seconds"]
            solver_status = solve_info["status"]

        violations = validate(schedule, possessions, segments, trains, windows, jobs)

        metrics_payload = {
            "jobs_unscheduled": metrics["jobs_unscheduled"],
            "n_possessions": metrics["n_possessions"],
            "line_blocked_min": metrics["line_blocked_min"],
            "total_job_duration_min": metrics["total_job_duration_min"],
            "weighted_wait": _weighted_wait(metrics["mean_wait_days"]),
            "wait_days": metrics["mean_wait_days"],
            "mean_delay_days": metrics["mean_delay_days"],
        }

        # report_day only lives on jobs_df, not on schedule_df -- merge it in
        # here and compute wait_days per job, since it's not otherwise
        # reachable once this run is only readable through Result's JSONB.
        placed = schedule.merge(jobs[["id", "day"]], left_on="job_id", right_on="id")
        start_day = placed["start_min"] // MINUTES_PER_DAY
        placed["wait_days"] = (start_day - placed["day"].clip(lower=0)).astype(int)
        schedule_with_wait = placed.drop(columns=["id", "day"])

        unscheduled = jobs.loc[~jobs["id"].isin(schedule["job_id"]), ["id", "segment", "department", "priority_class"]]

        save_result(
            run_id=run_id,
            schedule_json=schedule_with_wait.to_dict("records"),
            possessions_json=possessions.to_dict("records"),
            metrics_json=metrics_payload,
            validation_violations_json=[
                {"rule": v.rule, "detail": v.detail, "job_id": v.job_id, "possession_id": v.possession_id}
                for v in violations
            ],
            unscheduled_json=unscheduled.to_dict("records"),
        )
        update_run_status(run_id, RunStatus.complete, solve_time_actual=solve_time_actual, solver_status=solver_status)
    except Exception as exc:
        update_run_status(run_id, RunStatus.failed, error_message=str(exc))
