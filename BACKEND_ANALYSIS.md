# block-planner backend — handoff for frontend integration

This document explains what's been built so far, why it's shaped the way it
is, and everything you need to start wiring a frontend against it. It's a
snapshot, not a living doc — for anything that changes after this is
written, `CLAUDE.md` at the repo root is the authoritative, continuously
updated source (it has the full decision history, every verification run,
and every gotcha discovered along the way). Read this first for the shape
of the system; go to `CLAUDE.md` when you need the "why" behind a specific
design choice or a deeper dive into the scheduling algorithms themselves.

## 1. What this system does

SIH 26027: railway maintenance blocks. Three departments (Engineering,
S&T, Traction) need to close sections of track to do maintenance work.
Today they each grab track time independently, which wastes capacity. This
project demonstrates that a shared, coordinated schedule — computed by a
constraint solver — beats the uncoordinated status quo, on a synthetic but
realistic 100km double-track railway section over a 30-day planning
horizon.

Concretely, the backend:
1. **Generates** a synthetic problem instance (track layout, train
   timetable, a backlog of maintenance jobs) from a seed.
2. **Schedules** it three different ways — a greedy uncoordinated baseline,
   and two variants of a CP-SAT solver that coordinates across departments
   (one using ground-truth job priorities, one using an ML-predicted
   priority).
3. **Validates** every schedule independently against physical feasibility
   rules (no double-booked track, no train/maintenance conflicts, etc.).
4. **Persists** everything to Postgres and serves it over a REST API.

The frontend's job is to let a user pick a scenario, kick off runs, watch
them complete, and visualize/compare the resulting schedules — most
importantly as a Gantt-style chart of possessions and jobs, plus
side-by-side metric comparisons against the baseline.

## 2. Repo layout

```
src/            the scheduling pipeline itself (pure Python + pandas + OR-Tools + LightGBM)
  config.py       every tunable constant -- single source of truth
  data_gen.py     synthetic section/trains/jobs/windows generator
  baseline.py     greedy uncoordinated scheduler
  solver.py       CP-SAT coordinated scheduler
  model.py        LightGBM job-priority classifier
  check.py        independent feasibility validator (runs against ANY schedule)

api/            FastAPI backend exposing src/ over HTTP + Postgres persistence
  main.py         app entry point, CORS, /health
  config.py       env vars (DATABASE_URL, SOLVE_TIME_LIMIT, MODEL_PATH)
  schemas.py      Pydantic request/response models
  routers/        thin HTTP layer (scenarios.py, runs.py)
  services/       real logic (persistence.py, solve_runner.py, transform.py)
  models/         SQLAlchemy ORM (tables.py, database.py) + Alembic migrations
                  -- NOT the same as the repo-root models/ dir below

scripts/
  run.py          batch CLI: run data_gen -> baseline/solver -> check over many seeds
  seed_demo.py    provisions fixed named demo scenarios, pre-solved (see §7)

models/         joblib artifact for the trained priority classifier (mounted into the container)
tests/          pytest suite for src/
docker-compose.yml, Dockerfile   the whole stack: api + postgres
CLAUDE.md       full project history / decisions / verified findings (long, detailed)
```

**Important distinction**: `api/models/` is SQLAlchemy ORM code
(`tables.py`, `database.py`). The repo-root `models/` is a directory
holding the trained ML model's `.joblib` file. Same word, unrelated
things — don't confuse them when navigating.

## 3. Domain concepts you need to know

- **Job**: one maintenance task. Belongs to a department (Engineering /
  S&T / Traction), sits on one `segment` (of 20, each 5km) and one `line`
  (Up/Down), has an `estimated_duration_min`, and a `priority_class`
  (`Critical` / `High` / `Medium` / `Low`).
- **Backlog vs in-horizon jobs**: the job list isn't a clean slate. Some
  jobs are already overdue at day 0 (`day < 0`, id prefix `BKL-`); others
  arrive during the 30-day horizon (`day >= 0`).
- **Window**: maintenance can only happen inside two daily permitted
  windows — a 180-minute night window and a shorter 90-minute midday
  window, same clock times every day, section-wide.
- **Possession**: the actual unit that gets granted. A possession blocks
  one line over a contiguous range of segments for the full span of one
  window instance — no train can enter that range for that whole span.
  Multiple jobs can share one possession if they're on different segments
  within its range. **This is the central coordination mechanism**: the
  uncoordinated baseline gives every job its own possession (wasteful —
  it blocks a whole window slot for just one job's segment); the solver
  packs multiple jobs into shared possessions. The demonstrated win is
  mostly "far fewer possessions for the same work," not "faster
  scheduling."
- **Approach**: one of three ways to produce a schedule for a given
  scenario —
  - `baseline`: greedy, each department schedules independently, no
    coordination.
  - `solver_gt`: CP-SAT solver, using each job's true `priority_class` as
    the optimization weight.
  - `solver_ml`: CP-SAT solver, using an ML-predicted `priority_class`
    instead of the ground truth (the realistic case — in production you
    wouldn't have ground-truth priority, you'd have a model's guess).
- **Scenario**: a named, reproducible problem instance — a seed plus
  `backlog_size`/`jobs_per_day` parameters. The same scenario can have
  multiple runs (one per approach) so they're directly comparable.

## 4. Data model (Postgres, via SQLAlchemy)

Three tables, `Scenario` (1) → `Run` (many) → `Result` (1:1):

```python
class Scenario:
    id, name, seed, backlog_size, jobs_per_day, horizon_days, created_at

class Run:
    id, scenario_id, approach, status, solve_time_limit, solve_time_actual,
    solver_status, error_message, created_at, completed_at

class Result:
    id, run_id, schedule_json, possessions_json, metrics_json,
    validation_violations_json, unscheduled_json   # all JSONB
```

```python
Approach = "baseline" | "solver_gt" | "solver_ml"
RunStatus = "pending" | "running" | "complete" | "failed"
```

A `Scenario` row alone is just parameters — no schedule exists until a
`Run` is created and solved. A `Run` moves through
`pending -> running -> complete` (or `-> failed`) and only gets a `Result`
row once it reaches `complete`. **The frontend never queries the ORM
directly — this is just useful background for understanding the JSON
shapes the API hands back.**

## 5. How a run actually executes (background jobs, no task queue)

There's deliberately no Celery/Redis/worker process here — it's a
single-node hackathon demo. `POST /scenarios/{id}/runs` creates the `Run`
row (`status: pending`) and hands the actual work to FastAPI's
`BackgroundTasks`, which runs it in a worker thread automatically (since
the background function is a plain synchronous function, not `async def`)
— so the API keeps responding to other requests (including polling the
very run you just started) while a CP-SAT solve is in flight for up to 60
seconds.

The background function (`api/services/solve_runner.py::run_scenario`)
does, in order: set status to `running` → regenerate the scenario's data
from its stored seed/params → run the requested approach → validate the
result → save schedule/possessions/metrics/violations → set status to
`complete`. If *anything* in that chain throws, it's caught and the run is
marked `failed` with the exception message — a run can never be left
stuck in `running`.

**This means the frontend must poll.** There is no websocket/SSE push.
Flow for the frontend:
1. `POST /scenarios/{id}/runs` → get back `{id, status: "pending"}` immediately.
2. Poll `GET /runs/{id}` (cheap, metadata-only) until `status` is
   `complete` or `failed`. A sensible interval is 1-2s; a `solver_gt`/
   `solver_ml` run can take up to `SOLVE_TIME_LIMIT` (60s by default),
   `baseline` finishes in well under a second.
3. Once `complete`, fetch `GET /runs/{id}/schedule` and/or
   `GET /runs/{id}/metrics` for the actual payload.
4. If `failed`, `GET /runs/{id}` includes `error_message`.

## 6. API reference

Base URL when running via docker-compose: `http://localhost:8000`. CORS is
open to `http://localhost:*` and `http://127.0.0.1:*` (any port) — a
frontend dev server on any local port will work without extra config; no
other origins are allowed (no auth either — this is demo-scope only, don't
build in front of it as if it were production-hardened).

### `GET /health`
Liveness + whether the ML model actually loaded.
```json
{"status": "ok", "version": "0.1.0", "model_loaded": true}
```

### `GET /scenarios`
List every scenario with each approach's most recent run status. Cheap,
no payloads — good for a scenario picker's initial load.
```json
[
  {
    "id": 3,
    "name": "Standard section",
    "seed": 42,
    "runs": {"baseline": "complete", "solver_gt": "complete", "solver_ml": "complete"}
  }
]
```
`runs` always has all three approach keys; value is `null` if that
approach has never been run on this scenario.

### `POST /scenarios`
Create a scenario (parameters only — **no data is generated yet**, that
happens lazily the first time a run against it executes).
```json
// request
{"name": "My scenario", "seed": 123, "backlog_size": 240, "jobs_per_day": 2.5}
// backlog_size / jobs_per_day are optional, default from src/config.py
// name and seed are required

// response  200
{"id": 6}
```

### `POST /scenarios/{scenario_id}/runs`
Kick off a run. Returns immediately — does not wait for the solve.
```json
// request
{"approach": "solver_ml", "solve_time_limit": 60}
// approach: "baseline" | "solver_gt" | "solver_ml"  (required)
// solve_time_limit: optional seconds, ignored for baseline, defaults to
// SOLVE_TIME_LIMIT (60) if omitted for a solver approach

// response  200
{"id": 17, "status": "pending"}
```
`404 {"detail": "scenario not found"}` if `scenario_id` doesn't exist.

### `GET /runs/{run_id}`
Status metadata only — never the schedule payload (poll this, not
`/schedule`, while waiting).
```json
{"status": "complete", "solver_status": "FEASIBLE", "solve_time_actual": 60.09, "error_message": null}
```
`status`: `pending` | `running` | `complete` | `failed`.
`solver_status`: OR-Tools status string (`"FEASIBLE"`/`"OPTIMAL"`/etc.) for
solver approaches, literal `"N/A"` for baseline, `null` before completion.
`404` if `run_id` doesn't exist.

### `GET /runs/{run_id}/schedule`
The full Gantt data source. **404** if the run doesn't exist, **409**
`{"detail": "run is <status>, not complete"}` if it exists but hasn't
finished — use this to distinguish "wrong id" from "still solving" in the
UI.
```json
{
  "possessions": [
    {"id": "POSS-001-primary-Down-5", "line": "Down", "start_segment": 5, "end_segment": 8, "start_min": 1500, "end_min": 1680}
  ],
  "jobs": [
    {
      "id": "BKL-0001", "possession_id": "POSS-004-primary-Down-6", "segment": 6, "line": "Down",
      "department": "Engineering", "priority_class": "Medium",
      "start_min": 5920, "end_min": 6000, "wait_days": 4, "duration_min": 80
    }
  ],
  "unscheduled": [
    {"id": "BKL-0000", "segment": 14, "department": "Traction", "priority_class": "High"}
  ]
}
```
Notes for rendering:
- `start_min`/`end_min` are integer minutes from horizon start (day 0,
  minute 0) — divide by 1440 for day index, mod 1440 for clock time within
  the day.
- Every scheduled job's `possession_id` always points at an entry in
  `possessions` (verified: 0 unmatched in every test run) — a job's
  segment always falls inside its possession's `[start_segment,
  end_segment]` range and its time window inside the possession's.
  Multiple jobs can share one `possession_id`.
- `unscheduled` jobs have no `start_min`/`end_min`/`line`/`possession_id`
  at all — they never got placed. Show them separately (e.g. a "did not
  fit" list), not on the Gantt timeline.
- `wait_days` is how many days the job waited to start, relative to when
  it became actionable (report day, floored at horizon start) — the
  metric this project treats as the fair scheduler-behavior signal (see
  §8 for why, vs. the more naively-obvious `delay_days`, which isn't
  exposed per-job on this endpoint, only aggregated in `/metrics`).
- Response sizes are real payloads: ~60-70KB for a full scenario (hundreds
  of jobs/possessions). Fast though — verified 20-40ms server-side.
  Fine to fetch whole and render client-side; no pagination.

### `GET /runs/{run_id}/metrics`
Just the metrics dict, small and fast — poll/fetch this independently of
the schedule if you just need summary numbers. Same 404/409 rules as
`/schedule`.
```json
{
  "jobs_unscheduled": 76,
  "n_possessions": 83,
  "line_blocked_min": 68490.0,
  "total_job_duration_min": 22075.0,
  "weighted_wait": 8550.89,
  "wait_days": {"Critical": 7.47, "High": 9.38, "Medium": 13.28, "Low": 10.09},
  "mean_delay_days": {"Critical": 71.53, "High": 57.12, "Medium": 40.86, "Low": 24.8}
}
```
`wait_days`/`mean_delay_days` are keyed by `priority_class`. This exact
key set is a contract other code relies on — don't expect fields to
disappear, new ones may be added over time without a version bump.

### `GET /scenarios/{scenario_id}/comparison`
Metrics for every **complete** run on a scenario, keyed by approach, plus
`baseline`-relative percentage differences.
```json
{
  "scenario_id": 3,
  "metrics": {
    "baseline":  { "...": "full metrics dict, same shape as /metrics" },
    "solver_gt": { "...": "..." },
    "solver_ml": { "...": "..." }
  },
  "comparison_to_baseline": {
    "solver_gt": {
      "n_possessions": -59.53,
      "weighted_wait": -1.95,
      "wait_days": {"Critical": -0.84, "High": -9.78, "Medium": 15.06, "Low": -5.38},
      "...": "one entry per metric key, recursing into dict-valued ones"
    },
    "solver_ml": { "...": "..." }
  }
}
```
Percentage diff sign convention: **negative = lower than baseline**
(no "good"/"bad" judgment baked in — e.g. a negative `n_possessions` is an
improvement, a negative `weighted_wait` is an improvement, but a negative
`total_job_duration_min` wouldn't necessarily be — the frontend/consumer
decides what "better" means per metric). A metric entry is `null` if the
baseline value was `0`/`NaN` (percentage change against nothing is
undefined). **If `baseline` was never run on this scenario**,
`comparison_to_baseline` for every solver approach is the literal string
`"baseline has not been run for this scenario"` instead of a number —
check for a string vs. an object before rendering. `404` for an unknown
`scenario_id`; no 409 here (it just reports whatever complete runs exist,
possibly none).

### `GET /scenarios/{scenario_id}/summary`
Scenario parameters + everything `/comparison` returns, in one call — use
this for a scenario-picker/detail view instead of two round trips.
Verified fast: 16-98ms.
```json
{
  "id": 3, "name": "Standard section", "seed": 42,
  "backlog_size": 240, "jobs_per_day": 2.5, "horizon_days": 30,
  "metrics": { "...": "same as /comparison" },
  "comparison_to_baseline": { "...": "same as /comparison" }
}
```

## 7. Demo data already seeded — use this to start building today

You don't have to create scenarios or wait 60 seconds for anything —
`scripts/seed_demo.py` has already pre-solved three fixed, named
scenarios against the live stack (all 9 runs `complete`, 0 validation
violations). As of this writing:

| scenario_id | name             | seed | backlog_size | notes |
|---|---|---|---|---|
| 3 | Standard section | 42 | 240 | the main demo case |
| 4 | Heavy backlog    | 42 | 480 | worse maintenance debt |
| 5 | Light load       | 42 | 60  | lighter load |

Each has three `complete` runs (`baseline`, `solver_gt`, `solver_ml`) —
try e.g. `GET /scenarios/3/summary` or `GET /runs/8/schedule` (scenario
3's `baseline` run) right now. Run ids for scenario 3 are 8/9/10
(baseline/solver_gt/solver_ml respectively) as of this writing, but
**don't hardcode run ids in the frontend** — always resolve them via
`GET /scenarios/{id}` or `/summary`'s parent list, since re-running or
reseeding will create new ones. If this data ever looks stale or
inconsistent, `docker compose exec api python -m scripts.seed_demo` is
idempotent and safe to rerun (it skips anything already `complete`).

## 8. Things worth knowing before you build the UI

- **Not every solver run beats baseline.** This is a real, measured
  finding (see `CLAUDE.md`), not a bug: across a 30-seed batch,
  `n_possessions` improves in 30/30 seeds (the reliable win — lead with
  this), but `weighted_wait` only improves in ~21/30 seeds. Don't build a
  UI that assumes green-across-the-board; a comparison view should be
  able to show a metric getting worse without looking broken.
- **Solver `solver_status` is usually `"FEASIBLE"`, not `"OPTIMAL"`** —
  CP-SAT runs out of its time budget before proving optimality at this
  problem size. That's expected, not an error state.
- **`wait_days` vs `mean_delay_days`**: `wait_days` isolates scheduler
  behavior (relative to when a job became actionable); `mean_delay_days`
  is relative to the job's original report day, which confounds
  scheduler behavior with how overdue the job already was at day 0. If
  you show only one of these two in a headline UI, use `wait_days`.
- **Runs aren't bit-for-bit reproducible** for `solver_gt`/`solver_ml`
  (parallel search, wall-clock cutoff) — rerunning the same scenario/
  approach can give slightly different numbers. `baseline` is fully
  deterministic.
- **`jobs_unscheduled`** isn't a failure — jobs can legitimately not fit
  in the horizon given gang/window capacity. It's a first-class metric to
  display, and the specific unscheduled jobs are in `/schedule`'s
  `unscheduled` list.

## 9. Running the stack locally

```
docker compose up -d --build        # starts api (:8000) + postgres (:5432)
curl localhost:8000/health          # sanity check
docker compose exec api python -m alembic -c api/alembic.ini upgrade head   # if migrations aren't applied yet
docker compose exec api python -m scripts.seed_demo   # populate the 3 demo scenarios (idempotent)
```
`src/`, `models/`, and `scripts/` are volume-mounted into the container —
editing them locally takes effect without a rebuild. `api/` is baked into
the image at build time, so changes there need `docker compose up -d --build`.

## 10. Where the source of truth actually lives

This document is a snapshot for onboarding. For anything authoritative —
exact function signatures, every verified numeric finding, the full
reasoning behind design decisions, migration history — go to `CLAUDE.md`
at the repo root. It's organized chronologically by feature phase and is
kept in sync with the code as it changes; this document is not
guaranteed to be.
