# block-planner

## Project

AI block planner for SIH 26027. Coordinates maintenance blocks across
Engineering, S&T and Traction on a synthetic 100 km double-line section, so
departments share windows instead of each shutting the line separately.
Output is a weekly/monthly block schedule.

## Architecture

- `src/config.py` — all constants. Single source of truth; nothing here computes anything.
- `src/data_gen.py` — synthetic section, 30-day timetable, maintenance jobs, ground-truth priority.
- `src/baseline.py` — greedy uncoordinated scheduler (each department schedules independently). Comparison point for the solver.
- `src/check.py` — independent feasibility validator for any schedule (baseline or solver output).
- `src/solver.py` — CP-SAT optimiser (OR-Tools) that schedules jobs across departments jointly.
- `src/model.py` — LightGBM priority classifier, trained against the `data_gen` ground-truth labels.
- `scripts/run.py` — batch entry point wiring data_gen → baseline/solver → check.
- `api/` — FastAPI demo backend exposing the src/ pipeline over HTTP. No
  auth, no rate limiting, no logging framework — hackathon scope, not
  production infrastructure. `docker-compose.yml` + `Dockerfile` run it
  alongside Postgres 16.

## Key decisions already made

- Priority is four classes: `Critical` / `High` / `Medium` / `Low`, with CP-SAT
  objective weights `1000` / `100` / `10` / `1` (`PRIORITY_WEIGHTS` in config).
- Section is 20 segments of 5 km (`N_SEGMENTS`, `SECTION_LENGTH_KM`).
- Planning horizon is 30 days (`HORIZON_DAYS`), ~2.5 jobs/day (`JOBS_PER_DAY`).
- The ground-truth priority rule lives in exactly one function:
  `_ground_truth_priority` in `data_gen.py`. Don't duplicate or reimplement
  this logic elsewhere — everything else treats priority as an input label.
- Blocks may only be placed inside permitted windows: a daily 180-min
  primary (night) window and a shorter 90-min secondary (midday) window,
  corridor-wide, same clock times every day (`PRIMARY_WINDOW_*`,
  `SECONDARY_WINDOW_*` in config; emitted as `windows_df`). `estimated_duration_min`
  is capped at `PRIMARY_WINDOW_DURATION_MIN` so no job is structurally
  unschedulable regardless of scheduler quality — don't raise one without the other.
- Blocks are granted as **possessions**, one level above individual jobs: a
  possession is one line over a contiguous segment range for the *full*
  span of one permitted window instance — trains cannot enter any segment
  in that range for that whole span, however much of it is actually used.
  Multiple jobs may run inside one possession in parallel if on distinct
  segments; jobs on the same segment still can't overlap. Possession
  exclusivity (no two possessions on the same line with overlapping
  segment ranges) is a single physical resource regardless of department
  coordination. `baseline.py` gives each job its own possession covering
  just its segment — the uncoordinated behaviour — which wastes whatever
  part of the window that one job doesn't use; that waste is the headroom
  a coordinating solver closes by sharing possessions across jobs.
- Each department has a fixed gang count for the whole section, not
  per-segment: Engineering 2, S&T 1, Traction 1 (`GANG_COUNTS`). At most
  that many of a department's jobs may run anywhere at once — gangs are
  consumed by jobs, not by possessions. Calibrated by sweep: with the
  realistic (diurnal) timetable, track/window capacity is generous enough
  that gang count is the actual binding constraint on throughput, not
  track availability.
- ~25% of segments are `high_defect_stretch`; job generation is weighted
  toward them (`HIGH_DEFECT_SEGMENT_FRACTION`, `HIGH_DEFECT_WEIGHT_MULTIPLIER`),
  not uniform.
- Train departure times follow a diurnal shape, not uniform: dense
  06:00-23:00 with morning/evening peaks, a pronounced night lull
  23:00-05:00 (`NIGHT_LULL_*`, `*_PEAK_HOUR`, `PEAK_WIDTH_HOURS`,
  `PASSENGER_*`/`GOODS_*` weight constants). The primary window sits in the
  night lull, the secondary window in the midday trough between the two
  peaks — that's what makes possessions actually grantable. Do not revert
  to uniform departure times or move the windows off the lull/trough; this
  was deliberately calibrated (see the train-count-by-hour verification
  in-session) and is now settled.
- `jobs_df` is a starting **backlog** (report day < 0, already outstanding
  at day 0) plus in-horizon arrivals — real divisions don't start a
  planning month with a clean slate. Backlog jobs skew toward higher
  `defect_severity`/`recurrence_count` and elevated `days_overdue` built
  from genuine elapsed time since report, not an independently large
  number (`BACKLOG_*` in config; `generate_backlog_jobs` in `data_gen.py`).
  `priority_class` is assigned once, across backlog + in-horizon together,
  in `generate_dataset` — backlog jobs score higher through the existing
  features, not a separate rule. `BACKLOG_SIZE` is a placeholder (`0`)
  pending calibration; don't treat that as a real value.

## Code standards

- Write the minimum code that does the job. No speculative abstractions, no
  config for things that will never vary, no wrapper classes around single
  functions.
- No defensive try/except around things that should never fail. Let it crash
  loudly.
- No commented-out code, no TODOs left behind, no unused imports or params.
- Type hints on all public functions. Docstrings only where the intent isn't
  obvious from the name.
- Comments explain why, never what.
- Pure functions where possible. Return data, don't mutate arguments.
- All constants come from `config.py`. Never hardcode a number in a module.
- Prefer pandas vectorised operations over row loops.

## Conventions

- Schedule rows are dicts with keys: `job_id`, `segment`, `line`, `start_min`,
  `end_min`, `department`, `priority_class`.
- Possession rows are dicts with keys: `possession_id`, `line`,
  `segment_start`, `segment_end` (inclusive range), `start_min`, `end_min`.
  Every job in `schedule_df` must lie inside some possession covering its
  segment — see the possession model above.
- Times are integer minutes from horizon start (day 0, minute 0).
- Every scheduler (baseline, solver) returns `(schedule_df, possessions_df,
  metrics)`, and every metrics dict has the same shape — keep implementations
  returning identical keys so they're comparable. Keys: `line_blocked_min`
  (sum over possessions of duration × segments covered — NOT a union over
  jobs any more; a job holding a whole possession alone pays for the part
  of the window it doesn't use, which is why this exceeds
  `total_job_duration_min` for the baseline), `total_job_duration_min` (sum
  of placed jobs' own durations — compare the two to show work volume is
  constant while line downtime falls), `jobs_unscheduled`, `n_possessions`
  (replaces the old `n_block_windows`), `mean_delay_days` (dict by
  priority_class, relative to each job's own report day), `mean_wait_days`
  (dict by priority_class, relative to max(horizon start, report day) — see
  the note below on which one to use for comparisons). No `train_minutes_lost` key — it was structurally always
  0 under the possession model (a possession can never be granted where a
  train intrudes, by construction) and carried no comparative information;
  `check.py`'s `no_possession_train_overlap` rule is what actually catches
  that failure mode, with far more detail than a bare metric would.

## Workflow rule

After any change to `baseline.py` or `solver.py`, run `check.validate()` on
the output before considering the phase done.

## data_gen.py signatures (source of truth — read the file, not this list, if they ever diverge)

```python
def generate_segments(rng: np.random.Generator) -> pd.DataFrame
def generate_trains(segments_df, rng, n_passenger_trains=N_PASSENGER_TRAINS, horizon_days=HORIZON_DAYS) -> pd.DataFrame
def generate_jobs(segments_df, trains_df, rng, jobs_per_day=JOBS_PER_DAY, horizon_days=HORIZON_DAYS) -> pd.DataFrame  # in-horizon arrivals only, no priority_class
def generate_backlog_jobs(segments_df, trains_df, rng, backlog_size=BACKLOG_SIZE) -> pd.DataFrame  # report day < 0, no priority_class
def generate_windows(horizon_days: int = HORIZON_DAYS) -> pd.DataFrame
def generate_dataset(seed: int = DEFAULT_SEED, jobs_per_day: float = JOBS_PER_DAY, backlog_size: int = BACKLOG_SIZE) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]
def summarise(segments_df, trains_df, jobs_df) -> None
def _ground_truth_priority(jobs_df: pd.DataFrame, rng: np.random.Generator) -> pd.Series
```

`generate_dataset` returns `(segments_df, trains_df, jobs_df, windows_df)`; `jobs_df` is
`generate_backlog_jobs` concatenated with `generate_jobs`, with `priority_class`
assigned once on the combined table.

`segments_df` columns: `segment_id, start_km, end_km, section_speed_limit, traffic_density, high_defect_stretch`

`trains_df` columns (long format, one row per segment occupied):
`train_id, train_type, day, line, segment, start_min, end_min`

`windows_df` columns (long format, one row per permitted window instance):
`day, window_name, start_min, end_min` — `window_name` is `primary` or
`secondary`; `start_min`/`end_min` are within-day clock minutes, same every
day.

`jobs_df` columns:
`id, department, segment, line, estimated_duration_min, days_overdue,
defect_severity, asset_age_years, traffic_density, days_since_last_maintenance,
defect_type, recurrence_count, section_speed_limit, passenger_train_count,
speed_restriction_active, day, priority_class`
— `day` (report day) can be negative for backlog jobs (`id` prefix `BKL-`);
in-horizon arrivals (`id` prefix `<DEPT>-DD-NNNN`) always have `day >= 0`.

## baseline.py / check.py signatures

```python
def schedule_baseline(jobs_df, trains_df, windows_df) -> tuple[pd.DataFrame, pd.DataFrame, dict]  # (schedule_df, possessions_df, metrics)
def validate(schedule_df, possessions_df, segments_df, trains_df, windows_df, jobs_df) -> list[Violation]
def report(violations: list[Violation]) -> None
```

`Violation` (dataclass): `rule: str, detail: str, job_id: str | None = None, possession_id: str | None = None`
— populated with whichever id the rule is about; job-level rules set
`job_id`, possession-level rules set `possession_id`.

Department processing order (Engineering → S&T → Traction) was checked for
starvation effects at seed 42 by re-running with the order reversed: each
department's scheduled/total ratio was identical either way (0 percentage
point difference). Order is not a meaningful factor in this dataset —
whole-window train-conflict scarcity (~78% of segment/line/window slots
poisoned by some train) and each department's own job volume dominate.

**mean_delay_days vs mean_wait_days — use wait_days for scheduler-behavior
comparisons.** `delay_days = start_day - report_day` confounds two things:
scheduler behavior, and how far in the past a job's report day already was
(`days_overdue` feeds `_ground_truth_priority` at 0.25 weight, so
higher-priority backlog jobs mechanically have more negative report days by
construction). `wait_days = start_day - max(0, report_day)` strips out the
pre-existing backlog age, isolating what the scheduler actually made a job
wait once it was actionable.

On `delay_days`, baseline looks badly priority-inverted: Critical > Low in
20/20 seeds at the locked config (mean 82 vs 32 days). **On `wait_days`,
that inversion mostly disappears**: Critical > Low in only 2/20 seeds, and
mean wait is actually *lowest* for Critical (8.3) vs High (10.1) / Medium
(11.3) / Low (10.8). The `delay_days` gap was overwhelmingly the mechanical
backlog-age artifact, not baseline ignoring priority_class when it picks
what to schedule next. Don't cite the `delay_days` numbers as evidence of a
priority-blind baseline without the `wait_days` figure alongside — report
both, but treat `wait_days` as the one that actually isolates scheduler
behavior for baseline-vs-solver comparisons.

## solver.py signature

```python
def schedule_solver(jobs_df, trains_df, windows_df, weights: dict[str, int], time_limit: float = SOLVE_TIME_LIMIT) -> tuple[pd.DataFrame, pd.DataFrame, dict, dict]
```
Returns `(schedule_df, possessions_df, metrics, solve_info)` — `metrics` is
the same shape as `schedule_baseline`'s; `solve_info` is solver-only
(`status`, `wall_clock_seconds`, `objective_value`, `best_objective_bound`),
not part of the comparable-metrics contract, so don't add it to `metrics`.

`ground_truth_weights(jobs_df) -> dict[str, int]` builds the default
`weights` dict from `PRIORITY_WEIGHTS` on `jobs_df["priority_class"]` — the
Phase 4a starting point per the spec; a future phase may swap in
model-predicted weights, which is exactly why `schedule_solver` takes
`weights` as a plain dict rather than computing it internally.

CP-SAT model: possessions are one candidate per (day, window_name, line) —
not per arbitrary segment sub-range — with a solver-chosen segment range
`[poss_lo, poss_hi]` constrained to one train-free contiguous stretch. A
job's `uses[job, window]` boolean both pins its own start inside that
window (via `OnlyEnforceIf`) and forces the matching possession to cover
its segment. Same-segment jobs get `AddNoOverlap`; gang capacity is
`AddCumulative` per department. This was a real bug caught during testing:
the possession-sharing mechanism alone does *not* prevent two jobs on the
same segment inside the same possession from overlapping in time —
`AddNoOverlap` per (segment, line) is a separate, necessary constraint.

**Possession ranges are derived, not free** (`AddMinEquality`/`AddMaxEquality`
over whichever jobs use a candidate): a possession's `[segment_start,
segment_end]` is always exactly the min-to-max segment of jobs actually
inside it — verified directly (0 possessions padded beyond their job
footprint). The objective separately penalises total range width
(`LINE_BLOCKED_MIN_WEIGHT`, on `line_blocked_min`) and specifically the
*dead* segments inside a derived range that no job occupies
(`DEAD_SEGMENT_MINUTES_WEIGHT`, on `dead_segment_minutes` — e.g. jobs on
segments 3 and 7 force a possession over 3-7, and 4-6 are dead unless
something else lands there). Both weights are deliberately small/secondary
vs. delay — this fixes the *mechanism*, but with the search not yet
converged (below), the numbers don't reliably beat baseline's
`line_blocked_min` yet.

`schedule_solver` warm-starts from `schedule_baseline`'s own solution via
`AddHint` (baseline is milliseconds to compute and always feasible, so it's
free to offer). **Do not run two full-scale solves concurrently** — observed
directly: background CPU contention made one run terminate at 5.26s with a
much worse objective than an isolated run at the same time limit. Always
solve one at a time when comparing timings.

At full scale (~300 jobs incl. backlog), `SOLVE_TIME_LIMIT`-class runs
(60-300s) all come back `FEASIBLE`, not proven optimal. `check.validate()`
is clean (0 violations) at every time limit tested. Swept 60/180/300s at
seed 42: objective improves only ~1.75% total (76.47M → 75.13M) and
`best_objective_bound` is completely static at 2,721,175 across all three —
returns flatten fast, and the ~96% reported gap looks like a structurally
loose LP-relaxation bound rather than a real measure of distance from optimal.

**Confirmed, not just suspected**: `UNSCHEDULED_PENALTY` dominance is the
cause, diagnosed directly (scratchpad copy of the model, not a config/objective
change). At shipped settings (120s, seed 42) the objective breaks down as
delay 1.53%, unscheduled penalty **98.34%**, width 0.09%, dead-segment 0.04%
— the penalty term is essentially the whole objective. Sweeping the penalty
10k/100k/1M/10M (120s each) gives gap% of 42.5/74.3/96.4/99.65 —
**monotonically worse as the penalty grows**, reproducing the frozen-bound
symptom on demand. This is a structural tension, not a tunable mistake: the
penalty must stay far above the worst-case single-job weighted delay
(~200k) to guarantee the solver never drops a schedulable job to dodge a
delay cost, but the higher it is, the looser CP-SAT's bound gets. A run with
the penalty removed and every structurally-eligible job forced present
(diagnostic only, never shipped) came back `UNKNOWN` after 120s — it
couldn't even find a feasible solution, showing some of the unscheduled
count is genuine joint-feasibility tightness, not just penalty trade-offs.
**Conclusion: not fixable by retuning the penalty constant. A real fix
would need a structural reformulation (e.g. two-phase/lexicographic: first
minimize unscheduled count, then optimize delay/possession terms with that
count fixed) — a scoped follow-up, not done here. Until then, treat solver
status as `FEASIBLE` and don't cite the gap% as meaningful; cite
`mean_wait_days` and the direct metric comparisons instead.**
`jobs_unscheduled` and `n_possessions` are close to flat across the sweep;
`line_blocked_min` moves non-monotonically (76,590 → 57,420 → 63,180) since
it's a small secondary objective term, not something the search chases
directly. `mean_wait_days` *does* show a real win over baseline at the same
seed (e.g. Critical 2.9-6.2 across time limits vs. baseline's 5.96, High
7.1-9.4 vs. baseline's 11.04) — that's the metric to cite, not `delay_days`
or the objective/gap.

Runs are not bit-for-bit reproducible seed-to-seed or run-to-run at a fixed
time limit (parallel search, `num_search_workers=8`, wall-clock cutoff) —
unlike baseline, which is a deterministic greedy.

## model.py signature

```python
def train_priority_model(n_seeds: int = N_TRAINING_SEEDS) -> dict  # macro_f1, classification_report, confusion_matrix, labels, test_jobs_df
def score_jobs(df: pd.DataFrame) -> pd.DataFrame  # job_id, predicted_priority_class, proba_<class> per class
def predicted_weights(df: pd.DataFrame) -> dict[str, int]  # PRIORITY_WEIGHTS on predicted class, mirrors solver.ground_truth_weights
def feature_importance(jobs_df: pd.DataFrame) -> pd.DataFrame  # mean |SHAP value| per feature
def generate_training_data(n_seeds: int = N_TRAINING_SEEDS) -> pd.DataFrame
```
Model saved/loaded via joblib at `MODEL_PATH` (`models/priority_classifier.joblib`).

**Feature/leakage decision (deliberate)**: `_ground_truth_priority` scores
from six inputs (`days_overdue` 0.25, `defect_severity` 0.30,
`speed_restriction_active` 0.20, `recurrence_count` 0.10, `traffic_density`
0.10, `section_speed_limit` 0.05) plus injected noise. Those six are **not**
leakage and are included as features — they're real, independently-observable
job attributes that exist before any priority is assigned, exactly what a
human triage process would use; excluding them would leave nothing causally
connected to the label. Only `id` (identifier, not a feature) and
`priority_class` (the target) are excluded. Verified, not assumed: trained
SHAP importances rank all six causal features in the top 7 (by a wide
margin), with every feature that has no causal role in the label
(`asset_age_years`, `days_since_last_maintenance`, `defect_type`,
`passenger_train_count`, `department`, `segment`, `line`,
`estimated_duration_min`) ranking at the bottom — the model is learning the
real structure, not spurious correlation.

Trained on 50 seeds (`N_TRAINING_SEEDS`), 20% holdout (`MODEL_TEST_SIZE`),
stratified split on `DEFAULT_SEED`. Macro-F1 0.836, accuracy 0.838. Per-class
(precision/recall/f1): Critical 0.895/0.772/0.829, High 0.783/0.791/0.787,
Medium 0.824/0.855/0.839, Low 0.894/0.882/0.888. Confusion is concentrated
entirely in adjacent classes (Critical↔High, High↔Medium, Medium↔Low) — the
model never confuses Critical with Low, consistent with the underlying score
being continuous and quantile-bucketed, not a hard rule.

**Ablation (10 seeds, disjoint from the 50 training seeds and from
DEFAULT_SEED): A=ground truth, B=hand-written rule
(`days_overdue * defect_severity`), C=ML-predicted, identical scenarios,
`schedule_solver` at `SOLVE_TIME_LIMIT` each.** `jobs_unscheduled` and
`n_possessions` are statistically indistinguishable across all three (driven
by gang/window capacity, not by which weight scheme is used — expected, not
a null result). The real differentiator is `mean_wait_days` by priority: B
minimizes wait for Medium/Low at the *cost* of Critical/High (wait_Crit 6.75
vs A's 4.09), because its crude proxy doesn't track true priority as
tightly and misallocates urgency across classes. Scoring each variant's
actual outcome by the true `PRIORITY_WEIGHTS` (the fair, apples-to-apples
number: `1000*wait_Crit + 100*wait_High + 10*wait_Med + 1*wait_Low`) — A
4933 (ceiling), **C 5691, B 7675**. **C beats B in 9/10 seeds**, ~26% lower
weighted wait, and sits ~15% off the ground-truth ceiling. Verdict: keep the
ML model, drop the hand-written rule. Not tuned to reach this outcome —
`PRIORITY_WEIGHTS`, the objective, and the model's hyperparameters were
unchanged from their existing/default values for this comparison.

## scripts/run.py signature

```python
def run_comparison(n_seeds: int = N_RUN_SEEDS, seed: int = DEFAULT_SEED) -> pd.DataFrame
def report_comparison(result: pd.DataFrame, out_path: str = OUTPUT_CSV) -> None
```
Runs baseline + solver(ML) + solver(ground truth) on N_RUN_SEEDS identical
scenarios (seeds drawn from `seed`'s RNG stream, not sequential — still
fully reproducible), validates every one, exports the full per-seed table
to `outputs/run_comparison.csv`. `weighted_wait` in the output is
`1000*wait_Crit + 100*wait_High + 10*wait_Med + 1*wait_Low` — the same
fairness score used in the model.py ablation, so results there and here are
directly comparable.

**30-seed batch result (seeds disjoint from training/ablation, `SOLVE_TIME_LIMIT`
each): `check.validate()` clean, 0 violations across all 90 runs.**
`n_possessions` win is **universal** — both solver variants beat baseline in
30/30 seeds (mean ~208 → ~95, ~55% fewer), confirming the coordination
mechanism holds broadly, not just on hand-picked seeds. `weighted_wait` win
is **not** universal: solver_gt beats baseline in 21/30, solver_ml in
21/30 — real wins on average (13.7% and 7.4% mean improvement respectively)
but genuine losses in ~30% of seeds, not just averaged-away noise. Six
seeds (858577, 781563, 735739, 438867, 717466, 85943) are losses for
*both* solver variants — harder instances where baseline's greedy holds up
or the 60s budget isn't enough; worth a look if pursued further, not
explained here. `line_blocked_min` is worse for both solver variants across
the batch too (mean ~33k baseline vs ~75-76k solver, consistent with the
known not-yet-converged-search finding above, not a new problem). Report
`n_possessions` as the solid win; report `weighted_wait` as "wins on
average, not on every seed" — don't claim a universal win there.

## api/ structure and Docker

```
api/__init__.py, main.py, config.py, schemas.py, requirements.txt
api/routers/       # scenarios.py, runs.py -- thin FastAPI routers
api/services/       # persistence.py, solve_runner.py, transform.py -- real logic lives here
api/models/         # tables.py, database.py -- SQLAlchemy ORM only, NOT the
                     # project's models/ dir (joblib artifacts); Pydantic
                     # request/response schemas live in api/schemas.py instead
```

`api/config.py` reads `DATABASE_URL`, `SOLVE_TIME_LIMIT`, `MODEL_PATH` from
the environment with defaults; `SOLVE_TIME_LIMIT` and `MODEL_PATH` defaults
are imported from `src.config`/`src.model`, not re-declared, per the
single-source-of-truth rule. Only endpoint: `GET /health` → `{status,
version, model_loaded}` — `model_loaded` actually calls `joblib.load` on
`MODEL_PATH`, not just an existence check.

`Dockerfile` is `python:3.12-slim` (not 3.14, to stay on a Python version
with guaranteed prebuilt wheels for ortools/lightgbm across platforms —
local dev venv happens to run 3.14, that's not a requirement). Installs
`libgomp1` (LightGBM's compiled core needs OpenMP at runtime; the slim
image doesn't include it). Only `api/` is `COPY`'d into the image — `src/`, `models/`, and `scripts/`
are volume-mounted by `docker-compose.yml` (`./src:/app/src`,
`./models:/app/models`, `./scripts:/app/scripts`), not baked in, so
pipeline edits, retrained models, and script changes show up without a
rebuild. A standalone `docker run` without those mounts won't have `src/`
available; use compose.

**Verified**: `docker compose up --build -d` — both services start clean.
`curl localhost:8000/health` → `{"status":"ok","version":"0.1.0","model_loaded":true}`.
`docker compose exec api python -c "from src.solver import ...; from
src.baseline import ...; from src.model import ...; from src.check import
..."` → imports cleanly, no errors. Stack left running after verification
(not torn down) in case of follow-up poking.

## Persistence (SQLAlchemy 2.x + Alembic)

`api/models/tables.py` — `Scenario` (1) → `Run` (many) → `Result` (1:1, unique
`run_id`). `Approach` enum: `baseline`/`solver_gt`/`solver_ml`. `RunStatus`
enum: `pending`/`running`/`complete`/`failed`. `Result`'s `schedule_json`,
`possessions_json`, `metrics_json`, `validation_violations_json` are JSONB —
whole documents, never queried inside, never normalised into rows.
`metrics_json`'s expected-keys contract (frontend can rely on these; add
more without a migration, but keep the docstring in `tables.py` in sync):
`jobs_unscheduled`, `n_possessions`, `line_blocked_min`, `weighted_wait`,
`wait_days` (dict by priority_class), `total_job_duration_min`.

`api/models/database.py` — engine + session; `SessionLocal` is
`expire_on_commit=False` so a returned ORM object's columns stay readable
after its (self-contained, per-call) session closes — otherwise every
`persistence.py` function would hit `DetachedInstanceError` the moment a
caller touched the object it just got back.

`api/services/persistence.py` — plain functions, no repository/unit-of-work
classes. Grown across three phases (solve-as-background-job, read
endpoints, demo seeding); current full set, source of truth is the file
itself if this list ever drifts:
```python
def create_scenario(seed, backlog_size, jobs_per_day, horizon_days=HORIZON_DAYS, name=None) -> Scenario
def create_run(scenario_id, approach: Approach, solve_time_limit=None) -> Run
def update_run_status(run_id, status: RunStatus, solve_time_actual=None, solver_status=None, error_message=None) -> Run
def save_result(run_id, schedule_json, possessions_json, metrics_json, validation_violations_json, unscheduled_json) -> Result
def get_scenario(scenario_id) -> Scenario | None
def get_scenario_by_name(name) -> Scenario | None
def get_latest_run(scenario_id, approach: Approach) -> Run | None  # any status, not just complete
def get_run(run_id) -> Run | None
def get_results_for_scenario(scenario_id) -> list[Result]
def get_result(run_id) -> Result | None
def get_latest_results_by_approach(scenario_id) -> dict[Approach, Result]  # complete-only, most recent per approach
def list_scenarios_with_latest_run_status() -> list[dict]
```
`update_run_status` stamps `completed_at` automatically the first time
`status` becomes `complete` or `failed` — no separate "complete_run" function
needed for that.

Alembic lives at `api/alembic.ini` + `api/alembic/` (inside `api/` since
`env.py` imports `api.config`/`api.models.tables`, and only `api/` is baked
into the Docker image). **Run it with `python -m alembic`, not bare
`alembic`** — bare `alembic` is a console-script entry point, so
`sys.path[0]` is the script's own directory, not cwd, and `api.config`
fails to import; `python -m alembic` puts cwd (`/app`) on the path. Command:
`docker compose exec api python -m alembic -c api/alembic.ini upgrade head`.
The one migration so far (`6b8f4bac9333`) was generated via
`alembic revision --autogenerate` run from the *host* against the exposed
`localhost:5432` (simpler than generating inside the container, since `api/`
isn't volume-mounted — a file written there mid-container would never reach
the actual project files on disk) — reviewed by hand before applying, matched
the ORM exactly.

**Verified against the real Compose Postgres, not just the migration**: all
three tables + `alembic_version` exist with correct types/FK/unique
constraint (checked via `psql \d`). A throwaway script (copied into the
container at `/app/`, run, then deleted from both container and host —
nothing left behind) called all six `persistence.py` functions in sequence
and asserted the fake schedule/possessions/metrics/violations dicts it saved
came back byte-identical from `get_run`/`get_results_for_scenario`. All
assertions passed, including exact equality on all four JSONB columns.

## Solve-as-background-job

Three endpoints, wired via `app.include_router(...)` in `main.py`:

```
POST /scenarios              body: {name, seed, backlog_size?, jobs_per_day?}
                              -> {id}  -- creates the row only, no data generated yet
POST /scenarios/{id}/runs    body: {approach, solve_time_limit?}
                              -> {id, status: "pending"}  -- 404 if scenario doesn't exist
GET  /runs/{id}               -> {status, solver_status, solve_time_actual, error_message}
                              -- metadata only, never the schedule/possessions payload
```

`api/schemas.py` holds the Pydantic request/response models (`api/models/`
stays ORM-only, per its docstring). `backlog_size`/`jobs_per_day` default
from `src.config`; `name`/`seed` are required, matching the literal spec.

`api/services/solve_runner.py::run_scenario(run_id, scenario_id, approach,
solve_time_limit)` is the whole background job: status -> `running`,
`generate_dataset(seed=..., jobs_per_day=..., backlog_size=...)` from the
scenario's stored params, dispatch on `approach` (`baseline` ->
`schedule_baseline`; `solver_gt`/`solver_ml` -> `schedule_solver` with
`ground_truth_weights`/`predicted_weights`, `solve_time_limit` falling back to
`SOLVE_TIME_LIMIT`), `check.validate(...)`, `save_result(...)`, status ->
`complete`. The whole body is one `try/except Exception` that sets status ->
`failed` with `str(exc)` as `error_message` -- the one place in this codebase
a blanket except is correct, since the explicit requirement is that a run must
never be left stuck in `running`. `metrics_json` is built explicitly (not the
raw scheduler dict passed through) to satisfy the `Result.metrics_json`
contract, including computing `weighted_wait` the same way
`scripts/run.py::_weighted_wait` does — duplicated as a small local constant
rather than imported, since `scripts/` isn't in the Docker image.

**No Celery/Redis/worker process.** `create_run_endpoint` calls
`background_tasks.add_task(run_scenario, ...)` with a **plain (non-async)**
function — Starlette runs a sync background callable via a worker thread
(`run_in_threadpool`), off the event loop, automatically. That's the entire
mechanism satisfying "run the solve in a thread" — no manual `threading` or
`asyncio.to_thread` needed, since `BackgroundTasks` + a sync callable already
is that.

Boundary validation: `POST /scenarios/{id}/runs` checks `get_scenario(id) is
not None` before calling `create_run`, returning a clean 404 instead of
letting the FK `IntegrityError` surface as a raw 500 (added after hitting it
live — see verification below). `get_scenario` was added to
`persistence.py` (a seventh function, needed to re-read a scenario's stored
seed/backlog_size/jobs_per_day inside the background job).

**Verified against the real Compose stack** (`docker compose up --build -d`,
migrations already at head):
- `POST /scenarios` `{"name":"verify-run","seed":42}` → `{"id":2}`.
- `POST /scenarios/2/runs` `{"approach":"solver_ml"}` → `{"id":2,"status":"pending"}`
  in **~23ms** — confirmed non-blocking.
- Polled `GET /runs/2` once/sec: `running` for the full solve, then
  `{"status":"complete","solver_status":"FEASIBLE","solve_time_actual":60.14,...}`
  (default `SOLVE_TIME_LIMIT`, no override given — solver used the full budget).
- While the solve was in flight, `GET /health` was hit on every poll iteration
  and stayed `200 {"status":"ok",...}` throughout, latency 70–250ms each
  time — API was never blocked by the concurrent CP-SAT solve.
- Persisted result for that run: `validation_violations_json` array length
  **0**; `metrics_json` had all contract keys present including
  `weighted_wait`.
- `baseline` run on the same scenario: `pending` → `running` → `complete`
  in ~1s wall clock (`solve_time_actual: 0.1`, `solver_status: "N/A"`),
  0 violations.
- `POST /scenarios/999999/runs` → `404 {"detail":"scenario not found"}`,
  no `runs` row created (confirmed via `psql`; the sequence still advanced,
  which is normal Postgres behavior for a rolled-back insert, not a bug).
- Local `pytest` suite: 13/13 still passing (this feature touches only
  `api/`, no `src/` changes).

## Read endpoints

Four endpoints, all thin routers over `api/services/persistence.py` +
`api/services/transform.py`:

```
GET /runs/{id}/schedule      -> {possessions: [...], jobs: [...], unscheduled: [...]}
GET /runs/{id}/metrics       -> the stored metrics_json, unchanged
GET /scenarios/{id}/comparison -> {scenario_id, metrics: {approach: metrics_json},
                                    comparison_to_baseline: {approach: pct-diff | message}}
GET /scenarios               -> [{id, name, seed, runs: {approach: latest status | null}}]
```
`GET /runs/{id}` and `/schedule`/`/metrics` on it return `404` for an unknown
`run_id`, `409 {"detail": "run is <status>, not complete"}` if the run exists
but hasn't reached `complete` — lets the frontend tell "not found" from "not
ready yet" apart. `GET /scenarios/{id}/comparison` 404s for an unknown
`scenario_id`.

**Two new fields had to be added to what's persisted, because neither is
derivable from the previously-stored JSONB alone**: a schedule row only ever
carried `job_id, segment, line, start_min, end_min, department,
priority_class` — no report day, so per-job `wait_days` couldn't be computed
after the fact — and nothing recorded which jobs never got scheduled at all
(`schedule_baseline`/`schedule_solver` return a *count*, `jobs_unscheduled`,
not the job ids). Both are only reachable inside `solve_runner.py`, where
the full `jobs_df` is still in scope. Fix, in `run_scenario`:
- `schedule_json` rows now carry `wait_days` (`start_day - max(0, report_day)`,
  same formula as `_compute_metrics`'s `mean_wait_days`, computed by merging
  `schedule` against `jobs[["id","day"]]` before serializing).
- New `Result.unscheduled_json` column: `{id, segment, department,
  priority_class}` for every job in `jobs_df` absent from `schedule_df`
  (`jobs.loc[~jobs["id"].isin(schedule["job_id"])]`) — correctly comes back
  as "every job" when a solver run finds no feasible solution at all, since
  `schedule_df` is empty in that case, no special-casing needed.
- Migration `609415618a23` (`down_revision` `6b8f4bac9333`) adds
  `unscheduled_json JSONB NOT NULL DEFAULT '[]'` to `results` — generated via
  `alembic revision --autogenerate` from the host venv (which does have
  alembic/psycopg2 installed locally, unlike fastapi), reviewed, applied
  with `python -m alembic -c api/alembic.ini upgrade head` against the
  exposed `localhost:5432` before rebuilding the image. **Old rows saved
  before this change have no `wait_days` per job and an empty
  `unscheduled_json`** — reading their `/schedule` would `KeyError` on
  `wait_days`; not patched retroactively, since re-running is one POST.

`api/services/transform.py`:
```python
def build_schedule_response(schedule_json, possessions_json, unscheduled_json) -> dict
def build_comparison_response(scenario_id, metrics_by_approach: dict[str, dict]) -> dict
```
`build_schedule_response` renames `possession_id`/`segment_start`/
`segment_end` -> `id`/`start_segment`/`end_segment` on possessions; on each
scheduled job it renames `job_id` -> `id`, derives `duration_min` (`end_min -
start_min`), and derives `possession_id` by matching the job's `(line,
segment, [start_min, end_min])` against whichever possession's range and
window contains it (linear scan over possessions per job — at this scale,
hundreds of jobs times tens-to-hundreds of possessions, this is sub-100ms;
not worth vectorising). Every job matched a possession in verification
(0 unmatched, both runs) — expected, since `check.validate()` already
guarantees this containment property.

`build_comparison_response` recurses into dict-valued metrics (`wait_days`,
`mean_delay_days`) so percentage diffs are computed per priority_class too,
not just on scalar metrics; returns `None` for a metric whose baseline value
is `0`/`NaN` (percentage change against nothing is undefined, not zero). If
`baseline` isn't among the scenario's complete runs, every solver approach's
comparison entry is the literal string `"baseline has not been run for this
scenario"` instead of a crash or a silently-wrong number.

`get_latest_results_by_approach`/`list_scenarios_with_latest_run_status`
(new in `persistence.py`, alongside `get_result` for the single-run lookup)
both do the "most recent per approach" reduction with a single query plus an
in-Python `dict.setdefault` pass ordered by `created_at`/`completed_at`
descending — simpler than a window-function query at this data volume, and
avoids a second SQLAlchemy relationship-loading gotcha (accessing
`run.result` after the session that loaded `run` has closed would raise
`DetachedInstanceError`; both functions dereference it before their `with
get_session()` block exits).

**Verified against the real Compose stack**, scenario 2 (`seed=42`, the
existing "verify-run" scenario), fresh `baseline` (run 5) and `solver_ml`
(run 6) runs to completion:
- `GET /runs/5/schedule`: 200, **70,434 bytes, 40ms**. `GET /runs/6/schedule`:
  200, **60,356 bytes, 21ms**.
- Counts cross-checked against `GET /runs/{id}/metrics` for both: baseline
  `n_possessions=215` = 215 possessions in the schedule response,
  `jobs_unscheduled=84` = 84 entries in `unscheduled`; solver_ml
  `n_possessions=83` = 83 possessions, `jobs_unscheduled=76` = 76
  unscheduled. Total jobs (299) matches across both approaches on the same
  scenario, as expected. 0 jobs with an unmatched `possession_id` in either
  response.
- `GET /scenarios/2/comparison`: both `baseline` and `solver_ml` present
  under `metrics`; `comparison_to_baseline.solver_ml` shows real numbers,
  e.g. `n_possessions: -61.4` (83 vs 215, the coordination win),
  `line_blocked_min: +98.69` (known not-yet-converged-search tradeoff, see
  the solver.py section above), per-class `wait_days` diffs mixed
  (Critical/High worse, Medium/Low better on this particular seed/run — not
  cited as a general finding, just what this one comparison shows).
- `GET /scenarios/1/comparison` (a scenario with only a `solver_gt` run, no
  `baseline` ever run there): `comparison_to_baseline.solver_gt` came back
  as `"baseline has not been run for this scenario"`, not an error.
- 404 confirmed for `/runs/999999/schedule`, `/runs/999999/metrics`,
  `/scenarios/999999/comparison`. 409 confirmed: hit `/schedule` and
  `/metrics` on a run mid-solve (`status: running`) → both
  `409 {"detail":"run is running, not complete"}`.
- `GET /scenarios`: both scenarios listed with `id`/`name`/`seed` and each
  approach's latest status, `null` for approaches never run on that
  scenario.
- Local `pytest`: 13/13 still passing.

## Demo scenario seeding

**Problem: a live 60s CP-SAT solve on stage is a dead demo.** `scripts/seed_demo.py`
pre-solves a fixed set of named scenarios, in-process (direct Python calls,
not through the API's `BackgroundTasks`) — run inside the container so
`DATABASE_URL`/`src`/`api` are already correct:
`docker compose exec api python -m scripts.seed_demo [--force]`.
`docker-compose.yml` now also mounts `./scripts:/app/scripts` (same reason
`src/`/`models/` are mounted — not baked into the image, so edits show up
without a rebuild). Invoked as `python -m scripts.seed_demo`, not `python
scripts/seed_demo.py` — same `sys.path[0]` gotcha as bare `alembic`: a
plain script invocation puts the script's own directory on the path, not
`/app`, so `import src`/`import api` would fail; `-m` puts cwd (`/app`) on
the path instead.

**Idempotent**: a scenario is looked up by name (new `get_scenario_by_name`
in `persistence.py`) rather than recreated on every run, and each
`(scenario, approach)` pair already `complete` (new `get_latest_run`, which
unlike `get_latest_results_by_approach` sees every status, not just
complete — needed here to distinguish "already done" from "never run" from
"failed, needs a retry") is left alone unless `--force`. A prior `failed`
run is *not* treated as done — it's retried automatically without
`--force`, since only `complete` counts as "already done."

Three fixed scenarios, all seed `DEFAULT_SEED` (42) — same section/train
layout across all three so the demo is "one railway, three workload
conditions," not three unrelated random instances — varying only
`backlog_size`:
```
Standard section  backlog_size=BACKLOG_SIZE       (240, the already-calibrated default)
Heavy backlog     backlog_size=BACKLOG_SIZE * 2    (480)
Light load        backlog_size=BACKLOG_SIZE // 4   (60)
```
`jobs_per_day` fixed at the config default for all three (the task's own
framing only called for varying backlog size). Chosen as round multiples of
the value every prior verification in this file already ran against, rather
than a fresh calibration sweep for this task specifically.

**The "Light load" hypothesis did not hold — reporting that honestly rather
than re-picking a number to force the expected narrative.** The a priori
guess was: lighter backlog -> less contention -> baseline and solver
converge, "so we can be honest about where the gain is small." The actual
seeded numbers (below) show the opposite: at `backlog_size=60`,
`jobs_unscheduled=0` for all three approaches (there's enough gang/window
capacity to place everything), and `weighted_wait` improves by the *largest*
margin of the three scenarios (baseline 5290.76 -> solver_gt 1749.81 /
solver_ml 2095.58, roughly 60-67% lower) — because with no scarcity forcing
both approaches into similarly bad outcomes, the solver's coordination edge
shows cleanly and fast, within the 60s budget, on a smaller search space.
**"Standard section" (not "Light load") is the one that happens to show a
small gap** at this seed (weighted_wait 7197.21 -> 7056.88 / 7005.22, only
~2% better) — consistent with the already-documented finding that seed 42
is not one of the strong-win seeds for `weighted_wait` (30-seed batch,
`solver.py` section above: wins in only 21/30 seeds, "not just
averaged-away noise"). **"Heavy backlog" is the closest thing to the
intended "gain is small" case**: `solver_gt`'s weighted_wait (11037.26) is
actually *worse* than baseline's (11005.42) — the documented
`UNSCHEDULED_PENALTY`-dominance/frozen-bound problem (`solver.py` section
above) biting harder on a bigger instance, where the fixed 60s budget covers
proportionally less of a larger search space; `solver_ml` still wins
(9193.88, ~16.5% better) but by less than at the other two scenarios.
Kept `backlog_size=60` for "Light load" anyway — it's still a legitimate,
independently-reasoned choice ("smaller backlog" is what was asked for, on
its own terms), and picking a different number purely to manufacture the
"closer" result would be exactly the kind of tuning-to-reach-an-outcome this
file has consistently avoided elsewhere (see the model.py ablation: "not
tuned to reach this outcome").

**Seeded summary table** (fresh run, `docker compose exec api python -m
scripts.seed_demo`):
```
        scenario  approach   status  solve_time_s  jobs_unscheduled  n_possessions  weighted_wait
Standard section  baseline complete          0.10                84            215        7197.21
Standard section solver_gt complete         60.07                76             87        7056.88
Standard section solver_ml complete         60.09                77             85        7005.22
   Heavy backlog  baseline complete          0.26               311            256       11005.42
   Heavy backlog solver_gt complete         60.19               291             93       11037.26
   Heavy backlog solver_ml complete         60.31               295             86        9193.88
      Light load  baseline complete          0.04                 0            126        5290.76
      Light load solver_gt complete         60.11                 0             74        1749.81
      Light load solver_ml complete         60.08                 0             70        2095.58
```
Total wall clock ~6 minutes (6 CP-SAT solves at ~60s each, sequential —
never concurrent, per the existing rule — plus 3 baselines at well under
1s).

**Verified against the real Compose stack**:
- Fresh run produced the table above; **immediate rerun (no `--force`)
  skipped all 9** (`status` shows `complete (skipped)` for every row,
  `solve_time_s`/metrics unchanged from the fresh run) in **~1.7s total**
  versus ~6 minutes fresh.
- `SELECT name, COUNT(*) FROM scenarios ... GROUP BY name`: exactly 1 row
  each for "Standard section"/"Heavy backlog"/"Light load" after the
  rerun — no duplicates.
- `validation_violations_json` array length **0** for all 9 runs (`psql`
  query joining `results`/`runs`/`scenarios`).
- `GET /scenarios/{id}/summary` timed for all three (ids 3/4/5): **16-98ms**
  (first call per scenario ~20-100ms including connection setup, repeat
  calls consistently 16-26ms) — fast enough for a scenario-picker UI to
  hit directly. Response includes `id`/`name`/`seed`/`backlog_size`/
  `jobs_per_day`/`horizon_days` plus `metrics`/`comparison_to_baseline`
  (same shape `/comparison` returns) in one call, ~1.5-1.6KB each.
- `api/routers/scenarios.py::_build_comparison` factors the
  `get_latest_results_by_approach` + `build_comparison_response` pairing
  out of both `/comparison` and the new `/summary`, avoiding duplicating
  that logic across the two endpoints.
- Local `pytest`: 13/13 still passing.

## Pre-demo bug pass

**Real bug found and fixed, not just theoretical**: a priority class with
zero placed jobs makes `.reindex(order)` in `_compute_metrics` (both
`baseline.py` and `solver.py`) produce `NaN` for that class in
`mean_delay_days`/`mean_wait_days` — same for solver.py's early-exit
branch (no feasible solution found at all: previously hardcoded
`float("nan")` for every class). Postgres `jsonb` rejects `NaN` outright
(not valid JSON syntax), so `save_result` threw a raw
`psycopg2.errors.InvalidTextRepresentation`, leaving the run `failed` with
an ugly SQL traceback as `error_message` instead of a clean status.
**Reproduced live**: `POST` a `solver_gt` run with `solve_time_limit: 0.01`
on a tiny scenario → `UNKNOWN` status, all-NaN metrics, confirmed 500-style
failure via the real API before the fix.

Fix: both files now convert NaN -> `None` right after the `reindex` (via
`pd.isna`), and solver.py's early-exit branch sets `None` directly instead
of `float("nan")`. This has two knock-on fixes, both real, both caught by
re-testing rather than assumed safe: `_weighted_wait` (duplicated in
`api/services/solve_runner.py` and `scripts/run.py`) multiplied
`mean_wait_days[cls]` directly — `None * int` raises `TypeError` where
`NaN * int` used to silently propagate, so it now returns `None` for the
whole score if *any* class is `None`, rather than crash or silently treat
a missing class as zero (which would understate the score). And
`transform.py::_pct_diff` did `value - baseline_value`, which raises on
`None` the same way — now short-circuits to `None` whenever either side is
`None`, not just when `baseline_value` is falsy/NaN.

**Verified end-to-end after the fix**: the exact same previously-failing
request (`solver_gt`, `solve_time_limit: 0.01`) now returns
`status: complete`, `metrics` with `null` in place of every missing value,
and `GET /scenarios/{id}/comparison` against it returns `null` for the
undefined percentage diffs while still computing the real ones (e.g.
`n_possessions: -100.0`) -- no crash anywhere in the chain.

**Also pinned `requirements.txt` and `api/requirements.txt`** to the exact
versions already verified running in the container (previously
unpinned) — a `--no-cache` rebuild on presentation day could otherwise
have silently pulled newer, untested releases of `pandas`/`ortools`/
`fastapi`/etc. Verified the pinned set still resolves and builds cleanly
(`docker compose build --no-cache api`).

**Full fresh-machine simulation**, to catch anything that only breaks on
a clean checkout: built and ran an isolated `docker compose -p
bp_freshtest` stack (separate network/volume, same ports, main stack
stopped first to free them) from scratch — confirmed `GET /scenarios`
correctly 500s before migrations are applied (expected, not a bug; already
documented in the runbook), `alembic upgrade head` applies both migrations
cleanly in order on an empty database, and `python -m scripts.seed_demo`
reproduces all 9 demo runs with 0 validation violations. Torn down after
verification; the main stack's own data (and its `bugcheck-tiny` scratch
scenario created while reproducing the NaN bug, deleted afterward) was
untouched throughout since it lives in a separate named volume.

Local `pytest`: 13/13 passing after every change in this pass. No other
bugs found in this review — `pyflakes` across `src/`, `api/`, `scripts/`,
`tests/` reported nothing (no unused imports, no undefined names).
