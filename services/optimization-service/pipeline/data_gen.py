"""Synthetic data generation for block-planner.

Generates three related DataFrames for a synthetic double-line railway
section:

  segments  -- the physical track, split into fixed-length segments
  trains    -- a 30-day timetable of passenger + goods traffic, in long
               format (one row per segment occupied by one train)
  jobs      -- maintenance jobs raised against that track, each carrying a
               hidden ground-truth `priority_class` used later as the
               training signal for the risk model (src/model.py)

Everything is driven off a single numpy Generator seeded once in
generate_dataset(), so a given `seed` reproduces the exact same section,
timetable and job list end to end.
"""

import numpy as np
import pandas as pd

from src.config import (
    BACKLOG_LOOKBACK_SCALE,
    BACKLOG_MAX_LOOKBACK_DAYS,
    BACKLOG_OVERDUE_SLACK_SCALE,
    BACKLOG_RECURRENCE_MEAN,
    BACKLOG_SEVERITY_WEIGHTS,
    BACKLOG_SIZE,
    DEFAULT_SEED,
    EVENING_PEAK_HOUR,
    GOODS_DAY_BASE_WEIGHT,
    GOODS_NIGHT_WEIGHT,
    GOODS_PEAK_AMPLITUDE,
    HIGH_DEFECT_SEGMENT_FRACTION,
    HIGH_DEFECT_WEIGHT_MULTIPLIER,
    HORIZON_DAYS,
    JOBS_PER_DAY,
    MORNING_PEAK_HOUR,
    N_PASSENGER_TRAINS,
    N_SEGMENTS,
    NIGHT_LULL_END_HOUR,
    NIGHT_LULL_START_HOUR,
    PASSENGER_DAY_BASE_WEIGHT,
    PASSENGER_NIGHT_WEIGHT,
    PASSENGER_PEAK_AMPLITUDE,
    PEAK_WIDTH_HOURS,
    PRIMARY_WINDOW_DURATION_MIN,
    PRIMARY_WINDOW_START_MIN,
    SECONDARY_WINDOW_DURATION_MIN,
    SECONDARY_WINDOW_START_MIN,
    SECTION_LENGTH_KM,
)

LINES = ("Up", "Down")
MINUTES_PER_DAY = 1440

DEPARTMENTS = ["Engineering", "S&T", "Traction"]
DEPARTMENT_WEIGHTS = [0.5, 0.3, 0.2]
DEPARTMENT_PREFIX = {"Engineering": "ENG", "S&T": "SNT", "Traction": "TRC"}

DEFECT_TYPES = {
    "Engineering": [
        "Rail Fracture",
        "Ballast Deficiency",
        "Track Geometry Defect",
        "Weld Failure",
        "Fastening/Fitting Loose",
        "Formation Failure",
    ],
    "S&T": [
        "Signal Failure",
        "Point Machine Failure",
        "Track Circuit Failure",
        "Communication Link Failure",
        "Interlocking Fault",
        "Level Crossing Gate Fault",
    ],
    "Traction": [
        "OHE Wire Breakage",
        "Insulator Flashover",
        "Feeder/Sub-station Fault",
        "Traction Motor Fault",
        "Traction Power Supply Fault",
        "Pantograph Damage",
    ],
}


def generate_segments(rng: np.random.Generator) -> pd.DataFrame:
    """Build the 20 x 5km segments of the double-line section.

    Each segment gets a section_speed_limit (60-130 kmph, in 5 kmph steps)
    and a traffic_density in [0.15, 0.95] representing how heavily loaded
    that stretch of track is overall (passenger + goods). ~25% of segments
    are marked high_defect_stretch (e.g. old rail, poor drainage) -- jobs
    are generated preferentially on these in generate_jobs().
    """
    seg_len_km = SECTION_LENGTH_KM / N_SEGMENTS
    speed_choices = np.arange(60, 131, 5)

    segment_id = np.arange(N_SEGMENTS)
    start_km = segment_id * seg_len_km
    end_km = start_km + seg_len_km
    section_speed_limit = rng.choice(speed_choices, size=N_SEGMENTS)
    traffic_density = np.round(rng.uniform(0.15, 0.95, size=N_SEGMENTS), 3)

    n_high_defect = round(N_SEGMENTS * HIGH_DEFECT_SEGMENT_FRACTION)
    high_defect_ids = rng.choice(N_SEGMENTS, size=n_high_defect, replace=False)
    high_defect_stretch = np.isin(segment_id, high_defect_ids)

    return pd.DataFrame(
        {
            "segment_id": segment_id,
            "start_km": start_km,
            "end_km": end_km,
            "section_speed_limit": section_speed_limit,
            "traffic_density": traffic_density,
            "high_defect_stretch": high_defect_stretch,
        }
    )


def _random_route(rng: np.random.Generator, min_len: int, max_len: int):
    """Pick a contiguous run of segments and a line (Up/Down) for a train."""
    route_len = int(rng.integers(min_len, max_len + 1))
    start = int(rng.integers(0, N_SEGMENTS - route_len + 1))
    segments = list(range(start, start + route_len))
    line = rng.choice(LINES)
    if line == "Down":
        segments = segments[::-1]
    return segments, line


def _diurnal_hour_weights(night_weight: float, day_base_weight: float, peak_amplitude: float) -> np.ndarray:
    """Relative departure density per hour-of-day: near-zero across the
    night lull (NIGHT_LULL_START_HOUR to NIGHT_LULL_END_HOUR), a flat
    daytime baseline elsewhere, with Gaussian morning/evening peaks added
    on top. Normalized to sum to 1."""
    hours = np.arange(24)
    is_night = (hours >= NIGHT_LULL_START_HOUR) | (hours < NIGHT_LULL_END_HOUR)
    morning_bump = peak_amplitude * np.exp(-0.5 * ((hours - MORNING_PEAK_HOUR) / PEAK_WIDTH_HOURS) ** 2)
    evening_bump = peak_amplitude * np.exp(-0.5 * ((hours - EVENING_PEAK_HOUR) / PEAK_WIDTH_HOURS) ** 2)
    weights = np.where(is_night, night_weight, day_base_weight + morning_bump + evening_bump)
    return weights / weights.sum()


def _sample_diurnal_minute(rng: np.random.Generator, hour_weights: np.ndarray) -> float:
    """Sample a departure time (minutes from midnight) from an hourly diurnal shape."""
    hour = int(rng.choice(24, p=hour_weights))
    return hour * 60.0 + float(rng.uniform(0, 60))


def generate_trains(
    segments_df: pd.DataFrame,
    rng: np.random.Generator,
    n_passenger_trains: int = N_PASSENGER_TRAINS,
    horizon_days: int = HORIZON_DAYS,
) -> pd.DataFrame:
    """Build a 30-day timetable in long format (one row per segment/train).

    - 40 passenger trains, each with a fixed route and fixed daily departure
      time, repeated identically on every day of the horizon.
    - A goods forecast: a Poisson-distributed number of freight trains per
      day, each with its own random route and departure time, running
      noticeably slower than passenger trains.

    Departure times follow a diurnal shape, not a uniform one: dense
    06:00-23:00 with morning/evening peaks, sparse 23:00-05:00 (see
    _diurnal_hour_weights and the PASSENGER_*/GOODS_* constants in config).
    Goods traffic is flatter than passenger but still thins overnight.

    Per-segment dwell time is derived from that segment's speed limit and a
    train-type speed factor, so faster segments produce shorter occupancy
    windows.
    """
    speed_limits = segments_df.set_index("segment_id")["section_speed_limit"]
    passenger_hour_weights = _diurnal_hour_weights(
        PASSENGER_NIGHT_WEIGHT, PASSENGER_DAY_BASE_WEIGHT, PASSENGER_PEAK_AMPLITUDE
    )
    goods_hour_weights = _diurnal_hour_weights(GOODS_NIGHT_WEIGHT, GOODS_DAY_BASE_WEIGHT, GOODS_PEAK_AMPLITUDE)
    rows = []

    for t in range(n_passenger_trains):
        segments, line = _random_route(rng, 3, 20)
        depart_min = _sample_diurnal_minute(rng, passenger_hour_weights)
        speed_factor = rng.uniform(0.85, 1.0)
        train_id = f"PAX-{t:03d}"
        for day in range(horizon_days):
            cursor = depart_min
            for seg in segments:
                speed = speed_limits[seg] * speed_factor
                duration = 5.0 / speed * 60.0
                rows.append(
                    (train_id, "Passenger", day, line, seg, round(cursor, 1), round(cursor + duration, 1))
                )
                cursor += duration

    for day in range(horizon_days):
        n_goods = int(rng.poisson(15))
        for g in range(n_goods):
            segments, line = _random_route(rng, 2, N_SEGMENTS)
            depart_min = _sample_diurnal_minute(rng, goods_hour_weights)
            speed_factor = rng.uniform(0.45, 0.65)
            train_id = f"GDS-{day:02d}-{g:03d}"
            cursor = depart_min
            for seg in segments:
                speed = speed_limits[seg] * speed_factor
                duration = 5.0 / speed * 60.0
                rows.append(
                    (train_id, "Goods", day, line, seg, round(cursor, 1), round(cursor + duration, 1))
                )
                cursor += duration

    return pd.DataFrame(
        rows, columns=["train_id", "train_type", "day", "line", "segment", "start_min", "end_min"]
    )


def _ground_truth_priority(jobs_df: pd.DataFrame, rng: np.random.Generator) -> pd.Series:
    """The ONE place the hidden ground-truth priority_class label is decided.

    latent risk score = weighted sum of min-max normalized risk factors
    (weights sum to 1.0, chosen to reflect operational judgement):

        days_overdue              0.25  longer overdue -> more urgent
        defect_severity           0.30  primary severity signal (1-5 scale)
        speed_restriction_active  0.20  already forcing a speed restriction -> urgent
        recurrence_count          0.10  chronic/recurring defects escalate faster
        traffic_density           0.10  busier segment -> more trains exposed to the defect
        section_speed_limit       0.05  higher line speed -> higher consequence if left unfixed

    A small Gaussian noise term (sd=0.03, on the same 0-1 scale as the
    normalized score) is added on top, so the class boundary is not a
    perfectly deterministic function of the inputs -- this mirrors
    real-world labeling noise and stops the label from being trivially
    reverse-engineerable from any single feature.

    The resulting score is then cut into buckets by quantile (not by fixed
    thresholds), which is what guarantees the target class balance of
    roughly Critical 10% / High 25% / Medium 40% / Low 25% regardless of
    the exact shape of the underlying feature distributions.
    """

    def minmax(s: pd.Series) -> pd.Series:
        lo, hi = s.min(), s.max()
        if hi - lo < 1e-9:
            return pd.Series(0.5, index=s.index)
        return (s - lo) / (hi - lo)

    score = (
        0.25 * minmax(jobs_df["days_overdue"])
        + 0.30 * minmax(jobs_df["defect_severity"])
        + 0.20 * jobs_df["speed_restriction_active"].astype(float)
        + 0.10 * minmax(jobs_df["recurrence_count"])
        + 0.10 * minmax(jobs_df["traffic_density"])
        + 0.05 * minmax(jobs_df["section_speed_limit"])
    )
    score = score + rng.normal(0, 0.03, size=len(jobs_df))

    labels = pd.qcut(
        score,
        q=[0, 0.25, 0.65, 0.90, 1.0],
        labels=["Low", "Medium", "High", "Critical"],
    )
    return labels.astype(str)


def _segment_sampling_probs(segments_df: pd.DataFrame) -> np.ndarray:
    """Segment sampling weights for job placement: HIGH_DEFECT_WEIGHT_MULTIPLIER
    times more likely on a high_defect_stretch segment than a normal one."""
    weights = np.where(segments_df["high_defect_stretch"], HIGH_DEFECT_WEIGHT_MULTIPLIER, 1.0)
    return weights / weights.sum()


def generate_jobs(
    segments_df: pd.DataFrame,
    trains_df: pd.DataFrame,
    rng: np.random.Generator,
    jobs_per_day: float = JOBS_PER_DAY,
    horizon_days: int = HORIZON_DAYS,
) -> pd.DataFrame:
    """Generate in-horizon maintenance jobs across Engineering, S&T and Traction.

    The number of jobs raised each day is Poisson(jobs_per_day), so the
    total over the horizon averages jobs_per_day * horizon_days while still
    varying day to day. Each job's segment is sampled weighted toward
    high_defect_stretch segments (see generate_segments), not uniformly.
    Does not assign priority_class -- generate_dataset() does that once,
    across this table and the backlog together (see generate_backlog_jobs).
    """
    seg_lookup = segments_df.set_index("segment_id")
    passenger_trains = trains_df[trains_df["train_type"] == "Passenger"]
    passenger_counts = passenger_trains.groupby(["segment", "line"])["train_id"].nunique()

    segment_ids = segments_df["segment_id"].to_numpy()
    segment_probs = _segment_sampling_probs(segments_df)

    records = []
    job_counter = 0
    for day in range(horizon_days):
        n_today = int(rng.poisson(jobs_per_day))
        for _ in range(n_today):
            department = rng.choice(DEPARTMENTS, p=DEPARTMENT_WEIGHTS)
            segment = int(rng.choice(segment_ids, p=segment_probs))
            line = rng.choice(LINES)
            seg_row = seg_lookup.loc[segment]

            defect_severity = int(rng.integers(1, 6))
            days_overdue = int(np.clip(rng.exponential(8), 0, 90))
            p_restriction = float(
                np.clip(0.05 + 0.15 * (defect_severity / 5) + 0.15 * (min(days_overdue, 30) / 30), 0, 0.9)
            )

            job_counter += 1
            records.append(
                {
                    "id": f"{DEPARTMENT_PREFIX[department]}-{day:02d}-{job_counter:04d}",
                    "department": department,
                    "segment": segment,
                    "line": line,
                    # capped at PRIMARY_WINDOW_DURATION_MIN: every job must be
                    # able to fit inside at least the primary window
                    "estimated_duration_min": int(rng.integers(45, PRIMARY_WINDOW_DURATION_MIN + 1)),
                    "days_overdue": days_overdue,
                    "defect_severity": defect_severity,
                    "asset_age_years": round(float(rng.uniform(1, 40)), 1),
                    "traffic_density": float(seg_row["traffic_density"]),
                    "days_since_last_maintenance": int(np.clip(rng.exponential(150), 10, 720)),
                    "defect_type": rng.choice(DEFECT_TYPES[department]),
                    "recurrence_count": int(np.clip(rng.poisson(0.8), 0, 6)),
                    "section_speed_limit": int(seg_row["section_speed_limit"]),
                    "passenger_train_count": int(passenger_counts.get((segment, line), 0)),
                    "speed_restriction_active": bool(rng.random() < p_restriction),
                    "day": day,
                }
            )

    return pd.DataFrame.from_records(records)


def generate_backlog_jobs(
    segments_df: pd.DataFrame,
    trains_df: pd.DataFrame,
    rng: np.random.Generator,
    backlog_size: int = BACKLOG_SIZE,
) -> pd.DataFrame:
    """Generate jobs already outstanding at day 0 -- a starting backlog.

    Real divisions don't begin a planning month with a clean slate; they
    carry accumulated overdue maintenance. Each backlog job's report `day`
    is negative (an exponentially-distributed number of days before day 0,
    capped at BACKLOG_MAX_LOOKBACK_DAYS), and days_overdue is built as
    elapsed-time-since-report plus the same overdue-at-time-of-report slack
    in-horizon jobs get -- so it's genuinely large, not just independently
    sampled large. defect_severity and recurrence_count are drawn from
    distributions skewed toward chronic, long-deferred defects.
    speed_restriction_active reuses the same severity/overdue-driven formula
    as in-horizon jobs, so it rises on its own from those elevated inputs
    rather than through a separate rule. Same schema as generate_jobs()
    (minus priority_class, assigned once in generate_dataset()).
    """
    seg_lookup = segments_df.set_index("segment_id")
    passenger_trains = trains_df[trains_df["train_type"] == "Passenger"]
    passenger_counts = passenger_trains.groupby(["segment", "line"])["train_id"].nunique()

    segment_ids = segments_df["segment_id"].to_numpy()
    segment_probs = _segment_sampling_probs(segments_df)
    severity_probs = np.array(BACKLOG_SEVERITY_WEIGHTS) / sum(BACKLOG_SEVERITY_WEIGHTS)

    records = []
    for i in range(backlog_size):
        department = rng.choice(DEPARTMENTS, p=DEPARTMENT_WEIGHTS)
        segment = int(rng.choice(segment_ids, p=segment_probs))
        line = rng.choice(LINES)
        seg_row = seg_lookup.loc[segment]

        report_day = -int(np.clip(rng.exponential(BACKLOG_LOOKBACK_SCALE), 1, BACKLOG_MAX_LOOKBACK_DAYS))
        days_overdue = -report_day + int(np.clip(rng.exponential(BACKLOG_OVERDUE_SLACK_SCALE), 0, 30))
        defect_severity = int(rng.choice([1, 2, 3, 4, 5], p=severity_probs))
        p_restriction = float(
            np.clip(0.05 + 0.15 * (defect_severity / 5) + 0.15 * (min(days_overdue, 30) / 30), 0, 0.9)
        )

        records.append(
            {
                "id": f"BKL-{i:04d}",
                "department": department,
                "segment": segment,
                "line": line,
                "estimated_duration_min": int(rng.integers(45, PRIMARY_WINDOW_DURATION_MIN + 1)),
                "days_overdue": days_overdue,
                "defect_severity": defect_severity,
                "asset_age_years": round(float(rng.uniform(1, 40)), 1),
                "traffic_density": float(seg_row["traffic_density"]),
                "days_since_last_maintenance": int(np.clip(rng.exponential(150), 10, 720)),
                "defect_type": rng.choice(DEFECT_TYPES[department]),
                "recurrence_count": int(np.clip(rng.poisson(BACKLOG_RECURRENCE_MEAN), 0, 6)),
                "section_speed_limit": int(seg_row["section_speed_limit"]),
                "passenger_train_count": int(passenger_counts.get((segment, line), 0)),
                "speed_restriction_active": bool(rng.random() < p_restriction),
                "day": report_day,
            }
        )

    return pd.DataFrame.from_records(records)


def generate_windows(horizon_days: int = HORIZON_DAYS) -> pd.DataFrame:
    """Daily permitted maintenance windows for the whole corridor: a primary
    night window and a shorter secondary window, same clock times every day.
    A block may only be placed inside one of these -- see src/baseline.py.
    Deterministic (no rng): this is a fixed operating policy, not sampled.
    """
    days = np.arange(horizon_days)
    primary = pd.DataFrame(
        {
            "day": days,
            "window_name": "primary",
            "start_min": PRIMARY_WINDOW_START_MIN,
            "end_min": PRIMARY_WINDOW_START_MIN + PRIMARY_WINDOW_DURATION_MIN,
        }
    )
    secondary = pd.DataFrame(
        {
            "day": days,
            "window_name": "secondary",
            "start_min": SECONDARY_WINDOW_START_MIN,
            "end_min": SECONDARY_WINDOW_START_MIN + SECONDARY_WINDOW_DURATION_MIN,
        }
    )
    return pd.concat([primary, secondary], ignore_index=True).sort_values(["day", "start_min"]).reset_index(drop=True)


def generate_dataset(seed: int = DEFAULT_SEED, jobs_per_day: float = JOBS_PER_DAY, backlog_size: int = BACKLOG_SIZE):
    """Main entry point: generate segments, trains, jobs and windows from one seed.

    jobs_df is the backlog (report day < 0, already outstanding at day 0)
    concatenated with in-horizon arrivals, with priority_class assigned once
    across the combined table -- backlog jobs score higher on their own
    merit (elevated days_overdue, defect_severity, recurrence_count) rather
    than through a separate rule.

    Returns (segments_df, trains_df, jobs_df, windows_df).
    """
    rng = np.random.default_rng(seed)
    segments_df = generate_segments(rng)
    trains_df = generate_trains(segments_df, rng)
    backlog_df = generate_backlog_jobs(segments_df, trains_df, rng, backlog_size=backlog_size)
    arrivals_df = generate_jobs(segments_df, trains_df, rng, jobs_per_day=jobs_per_day)
    jobs_df = pd.concat([backlog_df, arrivals_df], ignore_index=True)
    jobs_df["priority_class"] = _ground_truth_priority(jobs_df, rng)
    windows_df = generate_windows()
    return segments_df, trains_df, jobs_df, windows_df


def summarise(segments_df: pd.DataFrame, trains_df: pd.DataFrame, jobs_df: pd.DataFrame) -> None:
    """Print class balance, feature distributions and daily job counts."""
    pd.set_option("display.width", 120)

    print("=" * 70)
    print("SEGMENTS")
    print("=" * 70)
    print(segments_df.describe())

    print()
    print("=" * 70)
    print(f"TRAINS  (rows={len(trains_df)})")
    print("=" * 70)
    print(trains_df.groupby("train_type")["train_id"].nunique())

    daily_occupied_min = (
        trains_df.assign(duration=trains_df["end_min"] - trains_df["start_min"])
        .groupby(["segment", "line", "day"])["duration"]
        .sum()
    )
    daily_occupancy_pct = daily_occupied_min / MINUTES_PER_DAY * 100
    worst_day_pct = daily_occupancy_pct.groupby(["segment", "line"]).max()
    print("\nBusiest segment/line occupancy (% of that day occupied by trains, worst day in the horizon):")
    print(worst_day_pct.sort_values(ascending=False).head())
    print(f"Max single-day segment/line occupancy: {worst_day_pct.max():.1f}%")

    print()
    print("=" * 70)
    print(f"JOBS  (n={len(jobs_df)})")
    print("=" * 70)

    print("\nClass balance (%):")
    order = ["Critical", "High", "Medium", "Low"]
    balance = jobs_df["priority_class"].value_counts(normalize=True).reindex(order) * 100
    print(balance.round(1))

    print("\nDepartment distribution (%):")
    print((jobs_df["department"].value_counts(normalize=True) * 100).round(1))

    print("\nNumeric feature distributions:")
    numeric_cols = [
        "estimated_duration_min",
        "days_overdue",
        "defect_severity",
        "asset_age_years",
        "traffic_density",
        "days_since_last_maintenance",
        "recurrence_count",
        "section_speed_limit",
        "passenger_train_count",
    ]
    print(jobs_df[numeric_cols].describe().T)

    print(f"\nspeed_restriction_active rate: {jobs_df['speed_restriction_active'].mean():.2%}")

    print("\nDaily job counts:")
    print(jobs_df.groupby("day").size())


if __name__ == "__main__":
    segments, trains, jobs, windows = generate_dataset(seed=DEFAULT_SEED)
    summarise(segments, trains, jobs)
