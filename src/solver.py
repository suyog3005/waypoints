"""CP-SAT optimiser for block-planner.

Jointly schedules jobs across departments -- the coordinated counterpart to
src/baseline.py's uncoordinated greedy. A possession candidate exists per
(day, window_name, line, safe_range) where safe_range is one maximal
train-free contiguous segment stretch for that window/line -- this is what
keeps a possession's range from ever crossing a train-conflicted segment.
Within a candidate's fixed safe_range, the possession's *actual* segment
range [poss_lo, poss_hi] is derived, not free: it's forced (AddMinEquality /
AddMaxEquality) to be exactly the min-to-max segment of whichever jobs end
up using it. The objective then penalises two distinct things: total range
width (line_blocked_min, weighted small) and specifically the "dead"
segments strictly inside that derived range that no job actually occupies
(weighted separately) -- e.g. jobs on segments 3 and 7 force a possession
over 3-7, and segments 4-6 are dead unless something else also lands there.

A job's uses[job, window] boolean both pins its own start time inside that
window and feeds the matching possession's min/max derivation. Same-segment
jobs get AddNoOverlap; gang capacity is AddCumulative per department.

The search is warm-started from schedule_baseline's own solution via
AddHint: it's fast to compute (milliseconds) and always feasible, so it
costs nothing to offer as a starting point, and it gives CP-SAT a complete
assignment to improve on rather than searching from scratch.
"""

import time

import pandas as pd
from ortools.sat.python import cp_model

from src.baseline import _line_blocked_min, _window_train_conflicts, _with_abs_times, schedule_baseline
from src.config import (
    DEAD_SEGMENT_MINUTES_WEIGHT,
    GANG_COUNTS,
    LINE_BLOCKED_MIN_WEIGHT,
    N_SEGMENTS,
    PRIORITY_WEIGHTS,
    SOLVE_TIME_LIMIT,
    UNSCHEDULED_PENALTY,
)
from src.data_gen import DEPARTMENTS, MINUTES_PER_DAY

MAX_DELAY_DAYS = 400  # generous upper bound: worst-case backlog lookback (180d) + horizon (30d) + slack
LINES = ("Up", "Down")


def ground_truth_weights(jobs_df: pd.DataFrame) -> dict[str, int]:
    """Default job weights: PRIORITY_WEIGHTS looked up on jobs_df's ground-truth priority_class."""
    return {row.id: PRIORITY_WEIGHTS[row.priority_class] for row in jobs_df.itertuples()}


def _safe_segment_ranges(conflicted_segments: set[int]) -> list[tuple[int, int]]:
    """Maximal contiguous segment ranges [0, N_SEGMENTS) containing no conflicted segment."""
    ranges = []
    lo = None
    for s in range(N_SEGMENTS):
        if s in conflicted_segments:
            if lo is not None:
                ranges.append((lo, s - 1))
                lo = None
        elif lo is None:
            lo = s
    if lo is not None:
        ranges.append((lo, N_SEGMENTS - 1))
    return ranges


def _containing_range(segment: int, ranges: list[tuple[int, int]]) -> tuple[int, int]:
    """Which safe range a (train-free-for-this-job) segment falls in. Always
    finds one: _eligible_windows already excluded windows where the job's
    own segment is conflicted, so it's guaranteed to be in some safe range."""
    for lo, hi in ranges:
        if lo <= segment <= hi:
            return lo, hi
    raise AssertionError(f"segment {segment} not in any safe range {ranges} -- eligibility filter is broken")


def _eligible_windows(job, windows: list) -> list:
    """Window instances a job could possibly use: on/after its report day,
    long enough for its duration, and its own segment train-free there."""
    return [
        w
        for w in windows
        if w.day >= job.day
        and job.estimated_duration_min <= w.abs_end - w.abs_start
        and (job.segment, job.line) not in w.conflicted
    ]


def schedule_solver(
    jobs_df: pd.DataFrame,
    trains_df: pd.DataFrame,
    windows_df: pd.DataFrame,
    weights: dict[str, int],
    time_limit: float = SOLVE_TIME_LIMIT,
) -> tuple[pd.DataFrame, pd.DataFrame, dict, dict]:
    """Jointly schedule jobs across departments with CP-SAT.

    Returns (schedule_df, possessions_df, metrics, solve_info). `metrics`
    has the same shape as schedule_baseline's; `solve_info` carries
    solver-only diagnostics: status, wall_clock_seconds, objective_value,
    best_objective_bound.
    """
    trains_abs = _with_abs_times(trains_df)
    windows_abs = _with_abs_times(windows_df).sort_values("abs_start").reset_index(drop=True)
    conflicts = _window_train_conflicts(trains_abs, windows_abs)

    class Window:
        __slots__ = ("day", "window_name", "abs_start", "abs_end", "conflicted")

    windows = []
    for w in windows_abs.itertuples():
        window = Window()
        window.day, window.window_name = w.day, w.window_name
        window.abs_start, window.abs_end = int(w.abs_start), int(w.abs_end)
        window.conflicted = conflicts.get((w.day, w.window_name), set())
        windows.append(window)
    horizon_end = max(w.abs_end for w in windows)

    safe_ranges_by_key: dict[tuple, list[tuple[int, int]]] = {}
    for w in windows:
        for line in LINES:
            conflicted_here = {s for s, ln in w.conflicted if ln == line}
            safe_ranges_by_key[(w.day, w.window_name, line)] = _safe_segment_ranges(conflicted_here)

    model = cp_model.CpModel()
    jobs = list(jobs_df.itertuples())

    present: dict[str, cp_model.IntVar] = {}
    start: dict[str, cp_model.IntVar] = {}
    interval: dict[str, cp_model.IntervalVar] = {}
    effective_delay: dict[str, cp_model.IntVar] = {}
    job_window_use: dict[tuple[str, int, str], cp_model.IntVar] = {}  # (job_id, day, window_name) -> use var, for warm-start hints

    # Possession candidates, keyed (day, window_name, line, safe_lo, safe_hi),
    # built lazily as jobs discover them -- only candidates some job could
    # actually use get created.
    poss_use_vars: dict[tuple, list] = {}
    poss_eff_min: dict[tuple, list] = {}
    poss_eff_max: dict[tuple, list] = {}
    poss_segment_uses: dict[tuple, dict[int, list]] = {}
    poss_window_duration: dict[tuple, int] = {}
    poss_window_bounds: dict[tuple, tuple[int, int]] = {}

    for job in jobs:
        present[job.id] = model.NewBoolVar(f"present_{job.id}")
        elig = _eligible_windows(job, windows)

        if not elig:
            model.Add(present[job.id] == 0)
            start[job.id] = model.NewIntVar(0, horizon_end, f"start_{job.id}")
            interval[job.id] = model.NewOptionalIntervalVar(
                start[job.id],
                job.estimated_duration_min,
                start[job.id] + job.estimated_duration_min,
                present[job.id],
                f"interval_{job.id}",
            )
            effective_delay[job.id] = model.NewIntVar(0, 0, f"delay_{job.id}")
            continue

        domain = cp_model.Domain.FromIntervals(
            [(w.abs_start, w.abs_end - job.estimated_duration_min) for w in elig]
        )
        start[job.id] = model.NewIntVarFromDomain(domain, f"start_{job.id}")
        interval[job.id] = model.NewOptionalIntervalVar(
            start[job.id],
            job.estimated_duration_min,
            start[job.id] + job.estimated_duration_min,
            present[job.id],
            f"interval_{job.id}",
        )

        use_vars = []
        for w in elig:
            u = model.NewBoolVar(f"uses_{job.id}_{w.day}_{w.window_name}")
            use_vars.append(u)
            job_window_use[(job.id, w.day, w.window_name)] = u
            model.Add(start[job.id] >= w.abs_start).OnlyEnforceIf(u)
            model.Add(start[job.id] <= w.abs_end - job.estimated_duration_min).OnlyEnforceIf(u)

            lo, hi = _containing_range(job.segment, safe_ranges_by_key[(w.day, w.window_name, job.line)])
            key = (w.day, w.window_name, job.line, lo, hi)
            if key not in poss_use_vars:
                poss_use_vars[key] = []
                poss_eff_min[key] = []
                poss_eff_max[key] = []
                poss_segment_uses[key] = {}
                poss_window_duration[key] = w.abs_end - w.abs_start
                poss_window_bounds[key] = (w.abs_start, w.abs_end)

            poss_use_vars[key].append(u)
            poss_segment_uses[key].setdefault(job.segment, []).append(u)

            eff_min_v = model.NewIntVar(lo, hi + 1, f"effmin_{job.id}_{key}")
            model.Add(eff_min_v == job.segment).OnlyEnforceIf(u)
            model.Add(eff_min_v == hi + 1).OnlyEnforceIf(u.Not())
            poss_eff_min[key].append(eff_min_v)

            eff_max_v = model.NewIntVar(lo - 1, hi, f"effmax_{job.id}_{key}")
            model.Add(eff_max_v == job.segment).OnlyEnforceIf(u)
            model.Add(eff_max_v == lo - 1).OnlyEnforceIf(u.Not())
            poss_eff_max[key].append(eff_max_v)

        model.Add(sum(use_vars) == present[job.id])

        day_of_start = model.NewIntVar(-1, horizon_end // MINUTES_PER_DAY + 1, f"day_{job.id}")
        model.AddDivisionEquality(day_of_start, start[job.id], MINUTES_PER_DAY)
        raw_delay = model.NewIntVar(0, MAX_DELAY_DAYS, f"rawdelay_{job.id}")
        model.Add(raw_delay == day_of_start - job.day)
        effective_delay[job.id] = model.NewIntVar(0, MAX_DELAY_DAYS, f"delay_{job.id}")
        model.Add(effective_delay[job.id] == raw_delay).OnlyEnforceIf(present[job.id])
        model.Add(effective_delay[job.id] == 0).OnlyEnforceIf(present[job.id].Not())

    for _, group in jobs_df.groupby(["segment", "line"]):
        segment_intervals = [interval[job_id] for job_id in group["id"]]
        if len(segment_intervals) > 1:
            model.AddNoOverlap(segment_intervals)

    for department in DEPARTMENTS:
        dept_intervals = [interval[j.id] for j in jobs if j.department == department]
        model.AddCumulative(dept_intervals, [1] * len(dept_intervals), GANG_COUNTS[department])

    poss_present: dict[tuple, cp_model.IntVar] = {}
    poss_lo: dict[tuple, cp_model.IntVar] = {}
    poss_hi: dict[tuple, cp_model.IntVar] = {}
    width: dict[tuple, cp_model.IntVar] = {}
    dead_segments: dict[tuple, cp_model.IntVar] = {}

    for key, use_list in poss_use_vars.items():
        lo, hi = key[3], key[4]
        span = hi - lo + 1

        poss_present[key] = model.NewBoolVar(f"poss_present_{key}")
        model.AddMaxEquality(poss_present[key], use_list)

        poss_lo[key] = model.NewIntVar(lo, hi + 1, f"poss_lo_{key}")
        poss_hi[key] = model.NewIntVar(lo - 1, hi, f"poss_hi_{key}")
        model.AddMinEquality(poss_lo[key], poss_eff_min[key])
        model.AddMaxEquality(poss_hi[key], poss_eff_max[key])

        width[key] = model.NewIntVar(0, span, f"width_{key}")
        model.Add(width[key] == poss_hi[key] - poss_lo[key] + 1).OnlyEnforceIf(poss_present[key])
        model.Add(width[key] == 0).OnlyEnforceIf(poss_present[key].Not())

        covered_vars = []
        for segment_uses in poss_segment_uses[key].values():
            if len(segment_uses) == 1:
                covered_vars.append(segment_uses[0])
            else:
                c = model.NewBoolVar(f"covered_{key}_{len(covered_vars)}")
                model.AddMaxEquality(c, segment_uses)
                covered_vars.append(c)
        covered_count = model.NewIntVar(0, span, f"coveredcount_{key}")
        model.Add(covered_count == sum(covered_vars))

        dead_segments[key] = model.NewIntVar(0, span, f"dead_{key}")
        model.Add(dead_segments[key] == width[key] - covered_count).OnlyEnforceIf(poss_present[key])
        model.Add(dead_segments[key] == 0).OnlyEnforceIf(poss_present[key].Not())

    objective = []
    for job in jobs:
        objective.append(weights.get(job.id, 0) * effective_delay[job.id])
        objective.append(UNSCHEDULED_PENALTY * (1 - present[job.id]))
    for key in poss_present:
        objective.append(LINE_BLOCKED_MIN_WEIGHT * poss_window_duration[key] * width[key])
        objective.append(DEAD_SEGMENT_MINUTES_WEIGHT * poss_window_duration[key] * dead_segments[key])
    model.Minimize(sum(objective))

    baseline_schedule, _, _ = schedule_baseline(jobs_df, trains_df, windows_df)
    baseline_start = dict(zip(baseline_schedule["job_id"], baseline_schedule["start_min"]))
    for job in jobs:
        if job.id not in baseline_start:
            model.AddHint(present[job.id], 0)
            continue
        model.AddHint(present[job.id], 1)
        s = int(baseline_start[job.id])
        model.AddHint(start[job.id], s)
        w = next((w for w in windows if w.abs_start <= s <= w.abs_end - job.estimated_duration_min), None)
        if w is not None:
            u = job_window_use.get((job.id, w.day, w.window_name))
            if u is not None:
                model.AddHint(u, 1)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_search_workers = 8
    t0 = time.perf_counter()
    status = solver.Solve(model)
    wall_clock = time.perf_counter() - t0

    solve_info = {
        "status": solver.StatusName(status),
        "wall_clock_seconds": round(wall_clock, 2),
        "objective_value": solver.ObjectiveValue() if status in (cp_model.OPTIMAL, cp_model.FEASIBLE) else None,
        "best_objective_bound": solver.BestObjectiveBound() if status in (cp_model.OPTIMAL, cp_model.FEASIBLE) else None,
    }

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        empty_schedule = pd.DataFrame(
            columns=["job_id", "segment", "line", "start_min", "end_min", "department", "priority_class"]
        )
        empty_possessions = pd.DataFrame(
            columns=["possession_id", "line", "segment_start", "segment_end", "start_min", "end_min"]
        )
        metrics = {
            "line_blocked_min": 0.0,
            "total_job_duration_min": 0.0,
            "jobs_unscheduled": len(jobs),
            "n_possessions": 0,
            # None, not NaN -- Postgres jsonb rejects NaN outright (not valid JSON).
            "mean_delay_days": {k: None for k in ("Critical", "High", "Medium", "Low")},
            "mean_wait_days": {k: None for k in ("Critical", "High", "Medium", "Low")},
        }
        return empty_schedule, empty_possessions, metrics, solve_info

    schedule_rows = []
    for job in jobs:
        if solver.Value(present[job.id]):
            s = solver.Value(start[job.id])
            schedule_rows.append(
                {
                    "job_id": job.id,
                    "segment": job.segment,
                    "line": job.line,
                    "start_min": s,
                    "end_min": s + job.estimated_duration_min,
                    "department": job.department,
                    "priority_class": job.priority_class,
                }
            )
    schedule_df = pd.DataFrame(
        schedule_rows, columns=["job_id", "segment", "line", "start_min", "end_min", "department", "priority_class"]
    )

    possession_rows = []
    for key, pv in poss_present.items():
        if solver.Value(pv):
            day, window_name, line, _, _ = key
            abs_start, abs_end = poss_window_bounds[key]
            possession_rows.append(
                {
                    "possession_id": f"POSS-{day:03d}-{window_name}-{line}-{solver.Value(poss_lo[key])}",
                    "line": line,
                    "segment_start": solver.Value(poss_lo[key]),
                    "segment_end": solver.Value(poss_hi[key]),
                    "start_min": abs_start,
                    "end_min": abs_end,
                }
            )
    possessions_df = pd.DataFrame(
        possession_rows,
        columns=["possession_id", "line", "segment_start", "segment_end", "start_min", "end_min"],
    )

    unscheduled_ids = [job.id for job in jobs if not solver.Value(present[job.id])]
    total_job_duration_min = float((schedule_df["end_min"] - schedule_df["start_min"]).sum())
    placed = schedule_df.merge(jobs_df[["id", "day"]], left_on="job_id", right_on="id")
    start_day = placed["start_min"] // MINUTES_PER_DAY
    delay_days = start_day - placed["day"]
    wait_days = start_day - placed["day"].clip(lower=0)
    order = ["Critical", "High", "Medium", "Low"]
    mean_delay_days = (delay_days.groupby(placed["priority_class"]).mean().reindex(order).round(2)).to_dict()
    mean_wait_days = (wait_days.groupby(placed["priority_class"]).mean().reindex(order).round(2)).to_dict()
    # reindex(order) introduces NaN for any class with zero placed jobs --
    # Postgres jsonb rejects NaN outright (it's not valid JSON), so swap to
    # None ("no data for this class") before it ever reaches persistence.
    mean_delay_days = {k: (None if pd.isna(v) else v) for k, v in mean_delay_days.items()}
    mean_wait_days = {k: (None if pd.isna(v) else v) for k, v in mean_wait_days.items()}

    metrics = {
        "line_blocked_min": _line_blocked_min(possessions_df),
        "total_job_duration_min": total_job_duration_min,
        "jobs_unscheduled": len(unscheduled_ids),
        "n_possessions": len(possessions_df),
        "mean_delay_days": mean_delay_days,
        "mean_wait_days": mean_wait_days,
    }
    return schedule_df, possessions_df, metrics, solve_info
