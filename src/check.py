"""Independent feasibility validator for block-planner.

Deliberately shares no code with baseline.py or solver.py: every overlap,
window and capacity check here is re-derived from scratch, so a bug in a
scheduler's own placement logic can't also hide from the check that's
supposed to catch it. The only things imported are raw constants
(GANG_COUNTS, HORIZON_DAYS from config; MINUTES_PER_DAY from data_gen,
which defines the schema, not scheduling behaviour).

Validates at both levels of the possession model: a possession (one line,
a contiguous segment range, one window instance's time span) must be
exclusive and train-free; a job must lie inside a possession covering its
segment, run its full duration, not overlap another job on its own
segment, respect its department's gang count, and not start before its
report day.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.config import GANG_COUNTS, HORIZON_DAYS
from src.data_gen import MINUTES_PER_DAY


@dataclass(frozen=True)
class Violation:
    rule: str
    detail: str
    job_id: str | None = None
    possession_id: str | None = None


def _check_no_duplicate_jobs(schedule_df: pd.DataFrame) -> list[Violation]:
    counts = schedule_df["job_id"].value_counts()
    return [
        Violation(rule="no_duplicate_jobs", detail=f"job appears {count} times in the schedule", job_id=job_id)
        for job_id, count in counts[counts > 1].items()
    ]


def _check_valid_segment(
    schedule_df: pd.DataFrame, possessions_df: pd.DataFrame, segments_df: pd.DataFrame
) -> list[Violation]:
    """A job's segment, and every segment in a possession's range, must reference a real segment."""
    valid = set(segments_df["segment_id"])
    violations = [
        Violation(rule="valid_segment", detail=f"segment {block.segment} not in segments_df", job_id=block.job_id)
        for block in schedule_df.itertuples()
        if block.segment not in valid
    ]
    for p in possessions_df.itertuples():
        bad = [s for s in range(p.segment_start, p.segment_end + 1) if s not in valid]
        if bad:
            violations.append(
                Violation(
                    rule="valid_segment",
                    detail=f"possession covers segments {bad} not in segments_df",
                    possession_id=p.possession_id,
                )
            )
    return violations


def _check_no_segment_overlap(schedule_df: pd.DataFrame) -> list[Violation]:
    """No two jobs may overlap on the same segment + line. Brute-force
    pairwise check within each (segment, line) group -- groups are small,
    and this is the most obviously-correct way to write it."""
    violations = []
    for (segment, line), group in schedule_df.groupby(["segment", "line"]):
        rows = list(group.itertuples())
        for i in range(len(rows)):
            for j in range(i + 1, len(rows)):
                a, b = rows[i], rows[j]
                if a.start_min < b.end_min and b.start_min < a.end_min:
                    violations.append(
                        Violation(
                            rule="no_segment_overlap",
                            detail=(
                                f"overlaps {b.job_id} on segment {segment}/{line}: "
                                f"{a.start_min}-{a.end_min} vs {b.start_min}-{b.end_min}"
                            ),
                            job_id=a.job_id,
                        )
                    )
    return violations


def _check_full_duration(schedule_df: pd.DataFrame, jobs_df: pd.DataFrame) -> list[Violation]:
    """A scheduled block must run for exactly the job's estimated_duration_min."""
    expected = jobs_df.set_index("id")["estimated_duration_min"]
    violations = []
    for block in schedule_df.itertuples():
        if block.job_id not in expected.index:
            violations.append(Violation(rule="full_duration", detail="job_id not found in jobs_df", job_id=block.job_id))
            continue
        actual = block.end_min - block.start_min
        want = expected.loc[block.job_id]
        if actual != want:
            violations.append(
                Violation(
                    rule="full_duration",
                    detail=f"block duration {actual} != estimated_duration_min {want}",
                    job_id=block.job_id,
                )
            )
    return violations


def _check_job_within_possession(schedule_df: pd.DataFrame, possessions_df: pd.DataFrame) -> list[Violation]:
    """Every scheduled job must lie inside some possession covering its segment on its line."""
    violations = []
    for block in schedule_df.itertuples():
        candidates = possessions_df[
            (possessions_df["line"] == block.line)
            & (possessions_df["segment_start"] <= block.segment)
            & (block.segment <= possessions_df["segment_end"])
        ]
        fits = ((candidates["start_min"] <= block.start_min) & (block.end_min <= candidates["end_min"])).any()
        if not fits:
            violations.append(
                Violation(
                    rule="job_within_possession",
                    detail=f"block {block.start_min}-{block.end_min} on segment {block.segment}/{block.line} not covered by any possession",
                    job_id=block.job_id,
                )
            )
    return violations


def _check_possession_within_window(possessions_df: pd.DataFrame, windows_df: pd.DataFrame) -> list[Violation]:
    """Every possession's time span must fall entirely inside a permitted window instance."""
    abs_start = windows_df["day"] * MINUTES_PER_DAY + windows_df["start_min"]
    abs_end = windows_df["day"] * MINUTES_PER_DAY + windows_df["end_min"]
    windows = windows_df.assign(abs_start=abs_start, abs_end=abs_end)

    violations = []
    for p in possessions_df.itertuples():
        fits = ((windows["abs_start"] <= p.start_min) & (p.end_min <= windows["abs_end"])).any()
        if not fits:
            violations.append(
                Violation(
                    rule="possession_within_window",
                    detail=f"possession {p.start_min}-{p.end_min} not fully inside any permitted window",
                    possession_id=p.possession_id,
                )
            )
    return violations


def _check_no_possession_overlap(possessions_df: pd.DataFrame) -> list[Violation]:
    """No two possessions may overlap on the same line with overlapping
    segment ranges -- possession of a line/segment range is one physical
    resource, granted exclusively regardless of coordination."""
    violations = []
    for line, group in possessions_df.groupby("line"):
        rows = list(group.itertuples())
        for i in range(len(rows)):
            for j in range(i + 1, len(rows)):
                a, b = rows[i], rows[j]
                time_overlap = a.start_min < b.end_min and b.start_min < a.end_min
                segment_overlap = a.segment_start <= b.segment_end and b.segment_start <= a.segment_end
                if time_overlap and segment_overlap:
                    violations.append(
                        Violation(
                            rule="no_possession_overlap",
                            detail=(
                                f"possession {a.possession_id} (segments {a.segment_start}-{a.segment_end}, "
                                f"{a.start_min}-{a.end_min}) overlaps {b.possession_id} (segments "
                                f"{b.segment_start}-{b.segment_end}, {b.start_min}-{b.end_min}) on line {line}"
                            ),
                            possession_id=a.possession_id,
                        )
                    )
    return violations


def _check_no_possession_train_overlap(possessions_df: pd.DataFrame, trains_df: pd.DataFrame) -> list[Violation]:
    """No possession may overlap a train path anywhere in its segment range.
    Train times are widened outward to whole minutes (floor start, ceil
    end) so a sub-minute train timing can't hide a real conflict."""
    abs_start = np.floor(trains_df["day"] * MINUTES_PER_DAY + trains_df["start_min"]).astype(int)
    abs_end = np.ceil(trains_df["day"] * MINUTES_PER_DAY + trains_df["end_min"]).astype(int)
    trains = trains_df.assign(abs_start=abs_start, abs_end=abs_end)

    violations = []
    for p in possessions_df.itertuples():
        same_line = trains[trains["line"] == p.line]
        in_range = same_line[(same_line["segment"] >= p.segment_start) & (same_line["segment"] <= p.segment_end)]
        overlap = in_range[(in_range["abs_start"] < p.end_min) & (in_range["abs_end"] > p.start_min)]
        if not overlap.empty:
            train = overlap.iloc[0]
            violations.append(
                Violation(
                    rule="no_possession_train_overlap",
                    detail=(
                        f"possession {p.start_min}-{p.end_min} (segments {p.segment_start}-{p.segment_end}/{p.line}) "
                        f"overlaps train {train['train_id']} ({int(train['abs_start'])}-{int(train['abs_end'])} "
                        f"on segment {train['segment']})"
                    ),
                    possession_id=p.possession_id,
                )
            )
    return violations


def _check_gang_capacity(schedule_df: pd.DataFrame) -> list[Violation]:
    """A department may never have more concurrent jobs than its gang count.
    Sweep-line over start/end events per department; the job whose start
    pushes concurrency past the limit is reported as the violator."""
    violations = []
    for department, group in schedule_df.groupby("department"):
        n_gangs = GANG_COUNTS[department]
        events = sorted(
            [(row.start_min, 1, row.job_id) for row in group.itertuples()]
            + [(row.end_min, -1, row.job_id) for row in group.itertuples()],
            key=lambda e: (e[0], e[1]),  # ends before starts at an equal timestamp
        )
        active = 0
        for time, delta, job_id in events:
            active += delta
            if delta == 1 and active > n_gangs:
                violations.append(
                    Violation(
                        rule="gang_capacity",
                        detail=f"{department} has {active} concurrent jobs at minute {time}, exceeds {n_gangs} gangs",
                        job_id=job_id,
                    )
                )
    return violations


def _check_not_before_report_day(schedule_df: pd.DataFrame, jobs_df: pd.DataFrame) -> list[Violation]:
    """A job can't be blocked before the day its defect was reported."""
    report_day = jobs_df.set_index("id")["day"]
    violations = []
    for block in schedule_df.itertuples():
        if block.job_id not in report_day.index:
            continue  # unresolvable job_id already reported by _check_full_duration
        earliest_allowed = report_day.loc[block.job_id] * MINUTES_PER_DAY
        if block.start_min < earliest_allowed:
            violations.append(
                Violation(
                    rule="not_before_report_day",
                    detail=f"starts at {block.start_min}, before report day (minute {earliest_allowed})",
                    job_id=block.job_id,
                )
            )
    return violations


def _check_within_horizon(possessions_df: pd.DataFrame) -> list[Violation]:
    """Every possession must fall inside [0, HORIZON_DAYS * MINUTES_PER_DAY]."""
    horizon_end = HORIZON_DAYS * MINUTES_PER_DAY
    violations = []
    for p in possessions_df.itertuples():
        if p.start_min < 0 or p.end_min > horizon_end:
            violations.append(
                Violation(
                    rule="within_horizon",
                    detail=f"possession {p.start_min}-{p.end_min} outside horizon [0, {horizon_end}]",
                    possession_id=p.possession_id,
                )
            )
    return violations


def validate(
    schedule_df: pd.DataFrame,
    possessions_df: pd.DataFrame,
    segments_df: pd.DataFrame,
    trains_df: pd.DataFrame,
    windows_df: pd.DataFrame,
    jobs_df: pd.DataFrame,
) -> list[Violation]:
    """Run every feasibility rule against a schedule. Empty list means clean."""
    return (
        _check_no_duplicate_jobs(schedule_df)
        + _check_valid_segment(schedule_df, possessions_df, segments_df)
        + _check_no_segment_overlap(schedule_df)
        + _check_full_duration(schedule_df, jobs_df)
        + _check_job_within_possession(schedule_df, possessions_df)
        + _check_possession_within_window(possessions_df, windows_df)
        + _check_no_possession_overlap(possessions_df)
        + _check_no_possession_train_overlap(possessions_df, trains_df)
        + _check_gang_capacity(schedule_df)
        + _check_not_before_report_day(schedule_df, jobs_df)
        + _check_within_horizon(possessions_df)
    )


def report(violations: list[Violation]) -> None:
    """Print violations grouped by rule."""
    if not violations:
        print("check.validate: no violations -- schedule is clean.")
        return
    print(f"check.validate: {len(violations)} violation(s)")
    by_rule: dict[str, list[Violation]] = {}
    for v in violations:
        by_rule.setdefault(v.rule, []).append(v)
    for rule, items in by_rule.items():
        print(f"\n[{rule}] ({len(items)})")
        for v in items:
            print(f"  {v.job_id or v.possession_id}: {v.detail}")
