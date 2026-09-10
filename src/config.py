"""Central configuration for block-planner.

All constants used across the project (data generation, baseline heuristics,
solver, and validation checks) are defined here so they have a single source
of truth.
"""

# Length of the railway section being modeled, in kilometers.
SECTION_LENGTH_KM = 100

# Number of track segments the section is divided into.
N_SEGMENTS = 20

# Planning horizon, in days.
HORIZON_DAYS = 30

# Average number of maintenance jobs generated per day.
JOBS_PER_DAY = 2.5

# Number of passenger trains to schedule around maintenance blocks.
N_PASSENGER_TRAINS = 40

# Priority weights used when scoring/penalizing job scheduling decisions.
PRIORITY_WEIGHTS = {
    "Critical": 1000,
    "High": 100,
    "Medium": 10,
    "Low": 1,
}

# CP-SAT objective (src/solver.py): per-job cost is weight * delay_days,
# weight coming from a caller-supplied dict (default: PRIORITY_WEIGHTS on
# ground-truth priority_class). UNSCHEDULED_PENALTY comfortably exceeds the
# worst plausible single-job weight * delay_days (1000 * ~200 days), so the
# solver only drops a job when no feasible placement exists at all, never as
# a cost trade-off. LINE_BLOCKED_MIN_WEIGHT is deliberately small -- a
# tie-breaker toward tighter possessions, not a term that competes with delay.
UNSCHEDULED_PENALTY = 1_000_000
LINE_BLOCKED_MIN_WEIGHT = 1
# Penalises a possession spanning segments no job in it actually uses (e.g.
# jobs on segments 3 and 7 forcing a possession over 3-7, wasting 4,5,6).
# Distinct from LINE_BLOCKED_MIN_WEIGHT: that penalises total range width
# (used + dead segments together); this penalises only the dead ones, which
# is the more direct lever against grouping far-apart jobs pointlessly.
DEAD_SEGMENT_MINUTES_WEIGHT = 1

# Default random seed for reproducible data generation.
DEFAULT_SEED = 42

# Time limit (in seconds) for the solver to find a solution.
SOLVE_TIME_LIMIT = 60

# Diurnal shape for train departure times (generate_trains): dense daytime
# traffic (06:00-23:00) with morning and evening peaks, a pronounced night
# lull (23:00-05:00). This is what makes the block windows below actually
# usable -- a possession needs its whole window train-free, so the windows
# are placed inside the lull and the midday trough between the two peaks.
# Departure hour is sampled from these weights, then a uniform minute
# within that hour.
NIGHT_LULL_START_HOUR = 23  # sparse traffic begins at 23:00
NIGHT_LULL_END_HOUR = 5  # sparse traffic ends at 05:00
MORNING_PEAK_HOUR = 8  # centre of the morning peak
EVENING_PEAK_HOUR = 19  # centre of the evening peak
PEAK_WIDTH_HOURS = 1.5  # Gaussian width (std dev, in hours) of each peak

PASSENGER_NIGHT_WEIGHT = 0.05  # relative departure density during the night lull
PASSENGER_DAY_BASE_WEIGHT = 1.0  # relative density across 06:00-23:00, before peaks
PASSENGER_PEAK_AMPLITUDE = 2.5  # extra relative density added at each peak's centre

GOODS_NIGHT_WEIGHT = 0.3  # goods traffic is flatter than passenger but still thins overnight
GOODS_DAY_BASE_WEIGHT = 1.0  # relative density across 06:00-23:00, before peaks
GOODS_PEAK_AMPLITUDE = 0.3  # goods barely responds to the passenger rush hours

# Permitted maintenance block windows: corridor-wide (all segments, both
# lines closed together), same clock times every day of the horizon. A block
# may only be placed inside one of these -- see src/baseline.py. Job
# estimated_duration_min is capped at PRIMARY_WINDOW_DURATION_MIN so every
# job can in principle fit in at least the primary window.
PRIMARY_WINDOW_START_MIN = 60  # 01:00 -- centre of the 23:00-05:00 night lull
PRIMARY_WINDOW_DURATION_MIN = 180  # until 04:00
SECONDARY_WINDOW_START_MIN = 780  # 13:00 -- midday trough, between the morning and evening peaks
SECONDARY_WINDOW_DURATION_MIN = 90  # until 14:30

# Gang resources per department, shared across the whole section (not
# per-segment): a department can have at most this many jobs running
# anywhere at the same instant. A realistic crew complement for a 100 km
# section; also the point in the calibration sweep where department
# imbalance was smallest.
GANG_COUNTS = {"Engineering": 2, "S&T": 1, "Traction": 1}

# Defect clustering: fraction of segments designated as high-defect
# stretches, and how much more likely a job is to land on one of them
# versus a normal segment when jobs are generated.
HIGH_DEFECT_SEGMENT_FRACTION = 0.25
HIGH_DEFECT_WEIGHT_MULTIPLIER = 4

# Starting backlog: jobs already outstanding at day 0, not just fresh
# in-horizon arrivals -- real divisions begin a planning month with
# accumulated overdue maintenance. Calibrated by sweep: 240 lands the
# baseline in the 60-75% scheduled band with the smallest department
# spread among in-band candidates (66.0% scheduled, 8.9pp spread).
BACKLOG_SIZE = 240
BACKLOG_MAX_LOOKBACK_DAYS = 180  # a backlog job was first reported at most this many days before day 0
BACKLOG_LOOKBACK_SCALE = 45  # exponential scale (days) for how far back that report day is
BACKLOG_OVERDUE_SLACK_SCALE = 8  # extra days_overdue on top of elapsed-since-report (same shape as in-horizon jobs)
BACKLOG_SEVERITY_WEIGHTS = [1, 1, 2, 3, 4]  # relative weights for defect_severity 1-5, skewed high vs in-horizon's uniform draw
BACKLOG_RECURRENCE_MEAN = 3.0  # Poisson mean for recurrence_count, vs 0.8 for in-horizon jobs

# src/model.py: training data is generate_dataset() run across this many
# distinct seeds and concatenated, so the classifier sees varied
# section/timetable/backlog draws rather than one fixed scenario.
N_TRAINING_SEEDS = 50
MODEL_TEST_SIZE = 0.2

# scripts/run.py: number of scenarios in the baseline-vs-solver batch
# comparison. Seeds are drawn from DEFAULT_SEED's own RNG stream, not
# sequential, so "30 random seeds" is still fully reproducible.
N_RUN_SEEDS = 30
