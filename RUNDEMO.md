# RUNDEMO — bringing the frontend up against the integrated stack

Reproduces the demo state: a seeded block-planner scenario, one CP-SAT plan
computed from it, and the frontend's Plans pages reading that plan through
the real read path (query-service + api-gateway), not
`frontend/lib/demo-data.ts`.

Kafka/Redpanda, the command-service and Redis are **not** part of this demo
— the optimizer is invoked directly (bypassing the Kafka consumer), and the
query-service's Redis cache is best-effort (it runs cache-off if Redis isn't
reachable). Skipping them means any page that writes (new block request) or
reads master data (departments/users) won't work — see the end of this doc.

Run every command from the repo root unless a `cd` is shown. Commands assume
`bash`/`zsh` and Docker Desktop running.

## Ports

| Service | Port | Notes |
|---|---|---|
| Sandbox Postgres | **5433** | host port; container's own 5432. Default (`infra/docker-compose.yml`) is 5432 — use 5433 if something else already owns 5432 on your machine. |
| query-service | 8002 | matches its own default (`services/query-service/app/config.py`) |
| api-gateway | **8000** (default) | this dev machine already had an unrelated project's container on 8000, so this session runs it on **8010** instead — see the callout in step 7. Use 8000 if it's free on yours. |
| Next.js frontend | 3000 | `next dev` default |

## 0. One-time setup

```bash
python3 -m venv .venv-demo
.venv-demo/bin/pip install \
  sqlalchemy alembic psycopg2-binary \
  ortools lightgbm scikit-learn shap joblib pandas numpy \
  pydantic pydantic-settings \
  fastapi "uvicorn[standard]" redis httpx

cd frontend && npm install && cd ..
```

## 1. Start the sandbox Postgres

```bash
docker run -d --name waypoints-postgres \
  -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=block_planning \
  -p 5433:5432 postgres:16-alpine
```

If `waypoints-postgres` already exists and is just stopped: `docker start waypoints-postgres`.

Create the read store database (separate from the operational DB, same
Postgres instance — mirrors `infra/postgres-init/01-create-read-db.sql`):

```bash
docker exec waypoints-postgres psql -U postgres -d postgres -c "CREATE DATABASE block_planning_read;"
```

## 2. Migrate + seed the operational DB

```bash
cd db
DATABASE_URL="postgresql+psycopg2://postgres:postgres@localhost:5433/block_planning" \
  ../.venv-demo/bin/python -m alembic upgrade head
cd ..

DATABASE_URL="postgresql+psycopg2://postgres:postgres@localhost:5433/block_planning" \
  .venv-demo/bin/python -m scripts.seed_from_pipeline
```

Idempotent by section name — re-running without `--force` just reports
"already exists; skipping". Pass `--force` to rebuild the scenario (fresh
Tracks/TrainSchedules/BlockRequests; Departments/Users/Trains are
get-or-create and stay put).

## 3. Run the CP-SAT pipeline once (produces the Plan)

```bash
DATABASE_URL="postgresql+psycopg2://postgres:postgres@localhost:5433/block_planning" \
  .venv-demo/bin/python -m scripts.run_optimization_once
```

This calls `app.planner.run_optimization()` directly — the same code path
the Kafka consumer (`app/consumer.py`) would trigger on an
`optimization.requested` event, just invoked synchronously so Kafka doesn't
need to be running for the demo. Takes up to `solve_time_limit` seconds
(default 60 — `services/optimization-service/app/config.py`). Every
`SUBMITTED` request in the section is still eligible after this — the
planner doesn't mark requests scheduled — so **running it again adds a
second plan** rather than replacing the first (CP-SAT isn't deterministic
run-to-run, so a re-run won't reproduce the same block count). Only do this
once per fresh seed unless you intend to compare multiple plans.

## 4. Migrate the read store + run the ETL sync

```bash
cd db/readstore
READ_STORE_URL="postgresql+psycopg2://postgres:postgres@localhost:5433/block_planning_read" \
  ../../.venv-demo/bin/python -m alembic upgrade head
cd ../..

DATABASE_URL="postgresql+psycopg2://postgres:postgres@localhost:5433/block_planning" \
READ_STORE_URL="postgresql+psycopg2://postgres:postgres@localhost:5433/block_planning_read" \
  .venv-demo/bin/python -m db.readstore.etl
```

One-shot full refresh. Re-run this any time the operational DB changes and
you want the read side to catch up (`--loop --interval 30` polls
continuously instead of running once).

## 5. Start the query-service

```bash
READ_STORE_URL="postgresql+psycopg2://postgres:postgres@localhost:5433/block_planning_read" \
REDIS_URL="redis://localhost:6379/0" \
  .venv-demo/bin/python -m uvicorn --app-dir services/query-service app.main:app --host 0.0.0.0 --port 8002
```

Redis isn't part of this demo. If nothing is listening on 6379 you'll see
`Redis unavailable ...; running without cache` in the log — that's expected
and harmless; the service falls through to the read store on every request.

## 6. Start the api-gateway

```bash
QUERY_SERVICE_URL="http://localhost:8002" \
COMMAND_SERVICE_URL="http://localhost:8001" \
  .venv-demo/bin/python -m uvicorn --app-dir services/api-gateway app.main:app --host 0.0.0.0 --port 8000
```

> **Port conflict callout**: if 8000 is already taken (it was on this dev
> machine, by an unrelated project's container), pick another port, e.g.
> 8010: add `--port 8010` above, and point the frontend at it in step 7
> (`NEXT_PUBLIC_API_GATEWAY_URL=http://localhost:8010`). `COMMAND_SERVICE_URL`
> points at a port nothing is listening on in this demo — that's fine; only
> requests that hit `/block-requests`, `/departments` or `/users` will fail
> (502), and command-service is out of scope here (see below).

## 7. Point the frontend at the gateway and start it

```bash
cd frontend
echo "NEXT_PUBLIC_API_GATEWAY_URL=http://localhost:8000" > .env.local   # or :8010, see step 6's callout
npm run dev
cd ..
```

Visit **http://localhost:3000/plans**.

## Tearing down

```bash
kill %1 %2 %3 2>/dev/null   # frontend / query-service / api-gateway, if run in this shell's job list
docker stop waypoints-postgres && docker rm waypoints-postgres   # destroys the seeded data
```

## What's deliberately out of scope here

- **command-service** (writes, plus `/departments` and `/users` reads) — not
  started. `/requests`, `/requests/new`, and the departments/users lookups
  it needs will 502 through the gateway.
- **Kafka/Redpanda** — not started. Step 3 calls the planner directly instead
  of going through `app/consumer.py`'s Kafka trigger.
- **Redis** — optional; the query-service runs cache-off without it (step 5).
