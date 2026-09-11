"""Baseline scheduler for block-planner.

Simulates current uncoordinated practice at the possession level. A
possession is a grant of one line over a contiguous segment range for the
full span of one permitted window instance -- trains cannot enter any
segment in that range for that whole span, regardless of how much of it a
job actually uses. Engineering, then S&T, then Traction schedule their own
jobs in turn, most-overdue-first, with no joint planning of which jobs to
prioritize and no deliberate window-sharing: each job gets its own whole
possession, covering just its own segment. That wastes whatever part of the
window the job doesn't need -- exactly the coordination gap src/solver.py
is meant to close by letting multiple jobs share one possession.

Possession *exclusivity* (no two possessions on the same line with
overlapping segment ranges) is still a single physical resource regardless
of coordination -- a section controller only grants one at a time -- so
later departments do see earlier departments' granted possessions. Gang
capacity stays a genuinely per-department resource.
"""

import numpy as np
import pandas as pd

from src.config import GANG_COUNTS
from src.data_gen import DEPARTMENTS, MINUTES_PER_DAY

Interval = tuple[int, int]


def _max_concurrent(intervals: list[Interval], s: int, e: int) -> int:
    """Max number of `intervals` simultaneously active at any instant within [s, e)."""
    events = []
    for a, b in intervals:
        lo, hi = max(a, s), min(b, e)
        if lo < hi:
            events.append((lo, 1))
            events.append((hi, -1))
    events.sort(key=lambda x: (x[0], x[1]))  # ends before starts at an equal timestamp
    concurrent = peak = 0
    for _, delta in events:
        concurrent += delta
        peak = max(peak, concurrent)
    return peak


def _earliest_gang_feasible_start(
    window_start: int, window_end: int, duration: int, gang_intervals: list[Interval], n_gangs: int
) -> int | None:
    """Earliest start within [window_start, window_end) with a department
    gang free for the whole `duration`. Only window_start and existing gang
    intervals' end times are checked -- concurrency is a step function that
    can only drop at an end time, so those are the only candidates."""
    candidates = sorted({window_start} | {b for _, b in gang_intervals if window_start < b <= window_end - duration})
    for t in candidates:
        if t + duration > window_end:
            continue
        if _max_concurrent(gang_intervals, t, t + duration) < n_gangs:
            return t
    return None


def _with_abs_times(df: pd.DataFrame) -> pd.DataFrame:
    """Add horizon-absolute [abs_start, abs_end) bounds from day + within-day
    start_min/end_min, widened outward to whole minutes so avoiding them
    never clips a train or window at sub-minute precision."""
    abs_start = np.floor(df["day"] * MINUTES_PER_DAY + df["start_min"]).astype(int)
    abs_end = np.ceil(df["day"] * MINUTES_PER_DAY + df["end_min"]).astype(int)
    return df.assign(abs_start=abs_start, abs_end=abs_end)


def _window_train_conflicts(trains_abs: pd.DataFrame, windows_abs: pd.DataFrame) -> dict[tuple[int, str], set]:
    """For each (day, window_name) instance, the (segment, line) pairs a
    train uses at some point during it -- a possession can't be granted for
    those, since the whole window would need to be train-free to grant one."""
    conflicts = {}
    for w in windows_abs.itertuples():
        overlapping = trains_abs[(trains_abs["abs_start"] < w.abs_end) & (trains_abs["abs_end"] > w.abs_start)]
        conflicts[(w.day, w.window_name)] = set(zip(overlapping["segment"], overlapping["line"]))
    return conflicts


def _schedule_department(
    dept_jobs: pd.DataFrame,
    claimed: set[tuple[int, str, int, str]],
    conflicts: dict[tuple[int, str], set],
    windows_abs: pd.DataFrame,
    n_gangs: int,
) -> tuple[list[dict], list[dict], list[str]]:
    """Greedy earliest-fit placement for one department's jobs, most overdue
    first. Each job claims its own whole-window possession on just its own
    segment. `claimed` is shared across all departments' calls and mutated
    in place, since possession of a segment/line/window instance is one
    physical resource. Returns (schedule rows, possession rows, unscheduled job ids)."""
    gang_intervals: list[Interval] = []
    schedule_rows: list[dict] = []
    possession_rows: list[dict] = []
    unscheduled: list[str] = []

    for job in dept_jobs.sort_values("days_overdue", ascending=False).itertuples():
        key = (job.segment, job.line)
        placement = None
        for w in windows_abs.loc[windows_abs["day"] >= job.day].itertuples():
            if key in conflicts.get((w.day, w.window_name), ()):
                continue
            if (*key, w.day, w.window_name) in claimed:
                continue
            start = _earliest_gang_feasible_start(w.abs_start, w.abs_end, job.estimated_duration_min, gang_intervals, n_gangs)
            if start is not None:
                placement = (start, w)
                break
        if placement is None:
            unscheduled.append(job.id)
            continue

        start, w = placement
        end = start + job.estimated_duration_min
        claimed.add((*key, w.day, w.window_name))
        gang_intervals.append((start, end))
        schedule_rows.append(
            {
                "job_id": job.id,
                "segment": job.segment,
                "line": job.line,
                "start_min": start,
                "end_min": end,
                "department": job.department,
                "priority_class": job.priority_class,
            }
        )
        possession_rows.append(
            {
                "possession_id": f"POSS-{job.id}",
                "line": job.line,
                "segment_start": job.segment,
                "segment_end": job.segment,
                "start_min": int(w.abs_start),
                "end_min": int(w.abs_end),
            }
        )

    return schedule_rows, possession_rows, unscheduled


def _line_blocked_min(possessions_df: pd.DataFrame) -> float:
    """Sum over possessions of duration x number of segments covered. A job
    holding a whole window alone wastes (window duration - job duration);
    a solver sharing one possession across several jobs pays that waste once."""
    if possessions_df.empty:
        return 0.0
    duration = possessions_df["end_min"] - possessions_df["start_min"]
    n_segments = possessions_df["segment_end"] - possessions_df["segment_start"] + 1
    return float((duration * n_segments).sum())


def _compute_metrics(
    schedule_df: pd.DataFrame,
    possessions_df: pd.DataFrame,
    jobs_df: pd.DataFrame,
    unscheduled_ids: list[str],
) -> dict:
    """Same metrics dict shape every scheduler (baseline, solver) must return."""
    total_job_duration_min = float((schedule_df["end_min"] - schedule_df["start_min"]).sum())

    placed = schedule_df.merge(jobs_df[["id", "day"]], left_on="job_id", right_on="id")
    start_day = placed["start_min"] // MINUTES_PER_DAY
    # delay_days: relative to the job's own report day (negative for backlog)
    # -- confounds pre-existing overdue-ness with scheduler behaviour, since
    # days_overdue itself feeds priority_class. wait_days: relative to
    # max(horizon start, report day) -- what the scheduler actually made a
    # job wait for, once it was actionable. Use wait_days for comparisons.
    delay_days = start_day - placed["day"]
    wait_days = start_day - placed["day"].clip(lower=0)
    order = ["Critical", "High", "Medium", "Low"]
    mean_delay_days = (delay_days.groupby(placed["priority_class"]).mean().reindex(order).round(2)).to_dict()
    mean_wait_days = (wait_days.groupby(placed["priority_class"]).mean().reindex(order).round(2)).to_dict()

    return {
        "line_blocked_min": _line_blocked_min(possessions_df),
        "total_job_duration_min": total_job_duration_min,
        "jobs_unscheduled": len(unscheduled_ids),
        "n_possessions": len(possessions_df),
        "mean_delay_days": mean_delay_days,
        "mean_wait_days": mean_wait_days,
    }


def schedule_baseline(
    jobs_df: pd.DataFrame, trains_df: pd.DataFrame, windows_df: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Run the uncoordinated, department-by-department greedy scheduler.
    Returns (schedule_df, possessions_df, metrics)."""
    trains_abs = _with_abs_times(trains_df)
    windows_abs = _with_abs_times(windows_df).sort_values("abs_start").reset_index(drop=True)
    conflicts = _window_train_conflicts(trains_abs, windows_abs)

    # Possession claims are shared across departments: segment/line
    # possession of a window instance is one physical resource.
    claimed: set[tuple[int, str, int, str]] = set()

    all_schedule_rows: list[dict] = []
    all_possession_rows: list[dict] = []
    all_unscheduled: list[str] = []
    for department in DEPARTMENTS:
        dept_jobs = jobs_df[jobs_df["department"] == department]
        schedule_rows, possession_rows, unscheduled = _schedule_department(
            dept_jobs, claimed, conflicts, windows_abs, GANG_COUNTS[department]
        )
        all_schedule_rows.extend(schedule_rows)
        all_possession_rows.extend(possession_rows)
        all_unscheduled.extend(unscheduled)

    schedule_df = pd.DataFrame(
        all_schedule_rows,
        columns=["job_id", "segment", "line", "start_min", "end_min", "department", "priority_class"],
    )
    possessions_df = pd.DataFrame(
        all_possession_rows,
        columns=["possession_id", "line", "segment_start", "segment_end", "start_min", "end_min"],
    )
    metrics = _compute_metrics(schedule_df, possessions_df, jobs_df, all_unscheduled)
    return schedule_df, possessions_df, metrics
