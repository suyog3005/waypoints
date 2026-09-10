"""Tests for src/check.py.

These are the checker's own correctness proof: for every rule, a minimal
schedule + possession set is built that breaks exactly that rule and
nothing else, and the matching violation must be the only one reported. A
known-good schedule must come back clean.
"""

import pandas as pd

from src.check import validate
from src.config import GANG_COUNTS, HORIZON_DAYS
from src.data_gen import MINUTES_PER_DAY

SCHEDULE_COLS = ["job_id", "segment", "line", "start_min", "end_min", "department", "priority_class"]
POSSESSION_COLS = ["possession_id", "line", "segment_start", "segment_end", "start_min", "end_min"]
JOBS_COLS = ["id", "day", "estimated_duration_min"]
TRAINS_COLS = ["train_id", "train_type", "day", "line", "segment", "start_min", "end_min"]
WINDOWS_COLS = ["day", "window_name", "start_min", "end_min"]


def _segments(ids=(0, 1, 2, 3)):
    return pd.DataFrame({"segment_id": list(ids)})


def _schedule(rows):
    return pd.DataFrame(rows, columns=SCHEDULE_COLS)


def _possessions(rows):
    return pd.DataFrame(rows, columns=POSSESSION_COLS)


def _jobs(rows):
    return pd.DataFrame(rows, columns=JOBS_COLS)


def _trains(rows):
    return pd.DataFrame(rows, columns=TRAINS_COLS)


def _windows(rows):
    return pd.DataFrame(rows, columns=WINDOWS_COLS)


def _only_rule(violations, rule):
    assert violations, f"expected a '{rule}' violation, got none"
    assert all(v.rule == rule for v in violations), f"unexpected rules fired: {[v.rule for v in violations]}"


def test_valid_schedule_is_clean():
    schedule = _schedule(
        [
            ("J1", 0, "Up", 60, 120, "Engineering", "Low"),
            ("J2", 1, "Up", 100, 160, "S&T", "Low"),  # different segment: fine even though times overlap
        ]
    )
    possessions = _possessions(
        [
            ("POSS-J1", "Up", 0, 0, 60, 240),
            ("POSS-J2", "Up", 1, 1, 60, 240),
        ]
    )
    jobs = _jobs([("J1", 0, 60), ("J2", 0, 60)])
    trains = _trains([("PAX-1", "Passenger", 0, "Up", 5, 60, 120)])  # unrelated segment, no conflict
    windows = _windows([(0, "primary", 60, 240)])

    assert validate(schedule, possessions, _segments(), trains, windows, jobs) == []


def test_segment_overlap_detected():
    schedule = _schedule(
        [
            ("J1", 0, "Up", 60, 120, "Engineering", "Low"),
            ("J2", 0, "Up", 100, 160, "S&T", "Low"),  # overlaps J1 on the same segment
        ]
    )
    possessions = _possessions([("POSS-1", "Up", 0, 0, 60, 240)])  # covers both jobs' time+segment
    jobs = _jobs([("J1", 0, 60), ("J2", 0, 60)])
    trains = _trains([])
    windows = _windows([(0, "primary", 60, 240)])

    violations = validate(schedule, possessions, _segments(), trains, windows, jobs)
    _only_rule(violations, "no_segment_overlap")


def test_full_duration_mismatch_detected():
    schedule = _schedule([("J1", 0, "Up", 60, 150, "Engineering", "Low")])  # 90 min block
    possessions = _possessions([("POSS-1", "Up", 0, 0, 60, 240)])
    jobs = _jobs([("J1", 0, 60)])  # but job needs only 60 min
    trains = _trains([])
    windows = _windows([(0, "primary", 60, 240)])

    violations = validate(schedule, possessions, _segments(), trains, windows, jobs)
    _only_rule(violations, "full_duration")


def test_job_within_possession_detected():
    schedule = _schedule([("J1", 1, "Up", 60, 120, "Engineering", "Low")])  # segment 1
    possessions = _possessions([("POSS-1", "Up", 0, 0, 60, 240)])  # only covers segment 0
    jobs = _jobs([("J1", 0, 60)])
    trains = _trains([])
    windows = _windows([(0, "primary", 60, 240)])

    violations = validate(schedule, possessions, _segments(), trains, windows, jobs)
    _only_rule(violations, "job_within_possession")


def test_possession_within_window_detected():
    schedule = _schedule([("J1", 0, "Up", 300, 360, "Engineering", "Low")])
    possessions = _possessions([("POSS-1", "Up", 0, 0, 300, 360)])  # job fits its possession...
    jobs = _jobs([("J1", 0, 60)])
    trains = _trains([])
    windows = _windows([(0, "primary", 60, 240)])  # ...but the possession itself isn't in any window

    violations = validate(schedule, possessions, _segments(), trains, windows, jobs)
    _only_rule(violations, "possession_within_window")


def test_possession_overlap_detected():
    schedule = _schedule(
        [
            ("J1", 0, "Up", 60, 120, "Engineering", "Low"),
            ("J2", 3, "Up", 130, 190, "S&T", "Low"),
        ]
    )
    possessions = _possessions(
        [
            ("POSS-1", "Up", 0, 2, 60, 240),  # segments 0-2
            ("POSS-2", "Up", 1, 3, 60, 240),  # segments 1-3: overlaps POSS-1's range on 1-2
        ]
    )
    jobs = _jobs([("J1", 0, 60), ("J2", 0, 60)])
    trains = _trains([])
    windows = _windows([(0, "primary", 60, 240)])

    violations = validate(schedule, possessions, _segments(), trains, windows, jobs)
    _only_rule(violations, "no_possession_overlap")


def test_possession_train_overlap_detected():
    schedule = _schedule([("J1", 0, "Up", 60, 90, "Engineering", "Low")])
    possessions = _possessions([("POSS-1", "Up", 0, 0, 60, 240)])
    jobs = _jobs([("J1", 0, 30)])
    trains = _trains([("PAX-1", "Passenger", 0, "Up", 0, 100, 150)])  # inside the possession's range+span
    windows = _windows([(0, "primary", 60, 240)])

    violations = validate(schedule, possessions, _segments(), trains, windows, jobs)
    _only_rule(violations, "no_possession_train_overlap")


def test_gang_capacity_exceeded_detected():
    n_gangs = GANG_COUNTS["S&T"]
    # n_gangs + 1 concurrent S&T jobs, each on its own segment/possession so
    # no other rule can also fire -- isolates the gang constraint.
    schedule = _schedule([(f"J{i}", i, "Up", 60, 120, "S&T", "Low") for i in range(n_gangs + 1)])
    possessions = _possessions([(f"POSS-{i}", "Up", i, i, 60, 240) for i in range(n_gangs + 1)])
    jobs = _jobs([(f"J{i}", 0, 60) for i in range(n_gangs + 1)])
    trains = _trains([])
    windows = _windows([(0, "primary", 60, 240)])

    violations = validate(schedule, possessions, _segments(range(n_gangs + 1)), trains, windows, jobs)
    _only_rule(violations, "gang_capacity")


def test_scheduled_before_report_day_detected():
    schedule = _schedule([("J1", 0, "Up", 60, 120, "Engineering", "Low")])
    possessions = _possessions([("POSS-1", "Up", 0, 0, 60, 240)])
    jobs = _jobs([("J1", 1, 60)])  # reported day 1, but block is on day 0
    trains = _trains([])
    windows = _windows([(0, "primary", 60, 240)])

    violations = validate(schedule, possessions, _segments(), trains, windows, jobs)
    _only_rule(violations, "not_before_report_day")


def test_outside_horizon_detected():
    horizon_end = HORIZON_DAYS * MINUTES_PER_DAY
    last_day = (horizon_end - 30) // MINUTES_PER_DAY
    schedule = _schedule([("J1", 0, "Up", horizon_end - 50, horizon_end, "Engineering", "Low")])
    possessions = _possessions([("POSS-1", "Up", 0, 0, horizon_end - 50, horizon_end + 100)])  # spills past horizon
    jobs = _jobs([("J1", last_day, 50)])
    trains = _trains([])
    # generously wide window on the last day so only the horizon rule fires
    windows = _windows([(last_day, "primary", 0, 2000)])

    violations = validate(schedule, possessions, _segments(), trains, windows, jobs)
    _only_rule(violations, "within_horizon")


def test_duplicate_job_detected():
    schedule = _schedule(
        [
            ("J1", 0, "Up", 60, 120, "Engineering", "Low"),
            ("J1", 1, "Up", 300, 360, "Engineering", "Low"),  # same job_id, disjoint placement
        ]
    )
    possessions = _possessions([("POSS-1", "Up", 0, 0, 60, 120), ("POSS-2", "Up", 1, 1, 300, 360)])
    jobs = _jobs([("J1", 0, 60)])
    trains = _trains([])
    windows = _windows([(0, "primary", 0, 1440)])

    violations = validate(schedule, possessions, _segments(), trains, windows, jobs)
    _only_rule(violations, "no_duplicate_jobs")


def test_invalid_segment_detected():
    schedule = _schedule([("J1", 99, "Up", 60, 120, "Engineering", "Low")])  # segment 99 doesn't exist
    possessions = _possessions([("POSS-1", "Up", 99, 99, 60, 240)])  # neither does this possession's range
    jobs = _jobs([("J1", 0, 60)])
    trains = _trains([])
    windows = _windows([(0, "primary", 0, 300)])

    violations = validate(schedule, possessions, _segments(), trains, windows, jobs)
    _only_rule(violations, "valid_segment")


def test_empty_schedule_is_clean():
    schedule = _schedule([])
    possessions = _possessions([])
    jobs = _jobs([("J1", 0, 60)])
    trains = _trains([])
    windows = _windows([(0, "primary", 0, 200)])

    assert validate(schedule, possessions, _segments(), trains, windows, jobs) == []
