# Agent Notes — AI-Powered Automatic Block Planning System

> **This file is the living memory for any coding agent working in this repository.**
> It is scoped only to this application. It must be kept in sync with the actual
> state of the repo at all times.
>
> **MANDATORY RULE: Any time a change is made anywhere in this repo (code, config,
> docs, schema, infra), this file's [Change Log](#change-log) must be updated in the
> same turn, with a dated entry describing what changed and where.** This applies to
> every future session, not just the one that created this file.

---

## 1. Purpose of This Repo (main)

An AI-powered railway block planning platform (Smart India Hackathon problem
statement). Full context lives in:

- [application_architecture_flow.md](./application_architecture_flow.md) — system
  architecture, components, read/write/real-time flows, extended feature set.
- [database_schema.md](./database_schema.md) — PostgreSQL schema for the Operational DB.
- [plan.md](./plan.md) — phase-by-phase build plan (source of truth for "what's next").
- [frontend-plan.md](./frontend-plan.md) — frontend brainstorm/design reference (stack,
  pages, components, the track-schematic "map" decision) and Phase 9 sub-phase
  breakdown (9A/9B/9C).

Read those three files before making architectural decisions. This file (`agent.md`)
is for **operational, repo-state notes** — not a duplicate of the architecture.

---

## 2. Confirmed Stack (do not re-litigate without user approval)

- API Gateway, Command Service, Query Service: **Python + FastAPI**.
- AI + Optimization Service: **Python** (OR-Tools/PuLP optimizer, scikit-learn optional).
- DB: **SQLAlchemy models** are the single source of truth, **Alembic** for migrations.
  (Prisma was considered and rejected — see plan.md history.)
- Frontend: **React / Next.js**.
- Local infra: **Docker Compose** (Postgres, Kafka/Redpanda, Redis, all services).
- CI: GitHub Actions (lint/test/build).
- MVP scope = architecture Sections 1–26 only. Sections 27–32 (RBAC, approvals,
  corridor bundling, notifications, weather, simulation, audit) are backlog — do not
  build unless explicitly asked.

---

## 3. Repo Structure

```text
/docs
  application_architecture_flow.md   - architecture spec (source of truth)
  database_schema.md                 - Postgres schema spec (source of truth)
  plan.md                             - phased build plan
  frontend-plan.md                    - frontend brainstorm/design reference (Phase 9)
  agent.md                            - this file
/db
  pyproject.toml                      - sqlalchemy + alembic deps
  __init__.py
  session.py                          - SQLAlchemy engine/session factory (reads DATABASE_URL)
  seed.py                             - local dev/demo seed script (python -m db.seed)
  alembic.ini                         - Alembic config (sqlalchemy.url overridden by env.py)
  models/                             - shared SQLAlchemy models (core-MVP, Phase 1 DONE)
    base.py                            - Base + TimestampMixin
    enums.py                           - Python enums mirroring Postgres ENUM types
    org.py                             - Zone, Division, Section
    identity.py                        - Department, User (roles/RBAC deferred)
    network.py                         - Track, TrackDependency, Asset, Train, TrainSchedule,
                                          Restriction, Maintenance
    requests.py                        - BlockRequest, BlockRequestAffectedTrack,
                                          TechnicalRequest, OperationalRequest
    planning.py                        - Constraint, OptimizationRun, OptimizationResult,
                                          Plan, Block, PlanItem, BlockAffectedTrack
    events.py                          - Event
  migrations/                          - Alembic env + versions (Operational DB)
    env.py                              - reads DATABASE_URL, target_metadata = Base.metadata
    script.py.mako
    versions/0001_initial_schema.py     - hand-authored initial schema (see Section 4 note)
  readstore/                           - Read Store (separate DB, Phase 6 DONE)
    __init__.py
    base.py                             - ReadStoreBase + SyncedMixin (synced_at stamp)
    session.py                          - engine/session factory (reads READ_STORE_URL)
    models.py                           - projections: PlanSummary, BlockView, TrackView,
                                          TrainView (denormalized, no cross-DB FKs)
    etl.py                              - polling full-refresh sync (python -m db.readstore.etl)
    alembic.ini                         - Read Store Alembic config (READ_STORE_URL)
    migrations/
      env.py                            - reads READ_STORE_URL, target_metadata = ReadStoreBase.metadata
      script.py.mako
      versions/0001_initial_read_store.py - hand-authored initial projection schema
  .env.example                          - DATABASE_URL + READ_STORE_URL
/contracts
  pyproject.toml                      - pydantic dep (shared event contracts)
  README.md                           - how to use the contracts + versioning rules
  __init__.py
  events/
    __init__.py                        - re-exports event classes + EVENT_REGISTRY
    base.py                            - BaseEvent envelope + EventSource
    schemas.py                         - typed payload models (BlockRequestPayload, ...)
    events.py                          - concrete event classes + EVENT_REGISTRY + make_event()
    topics.py                          - Kafka topic names + EVENT_TOPIC_MAP
    json_schemas/                      - JSON Schema (draft 2020-12) per event type, v1
      block_request.submitted.v1.json
      block_request.updated.v1.json
      optimization.requested.v1.json
      optimization.result.v1.json
      track.status_changed.v1.json
      train.delay.v1.json
/services
  api-gateway/         (FastAPI, port 8000) - routes reads->query-service, writes->command-service
    app/
      main.py            - FastAPI app + lifespan (httpx client), middleware, includes routers
      config.py          - Settings (port, command_service_url, query_service_url, auth_enabled,
                           upstream_timeout_seconds)
      middleware.py      - CorrelationIdMiddleware (X-Correlation-Id) + StubAuthMiddleware (bearer)
      proxy.py           - forward(): httpx proxy helper (filters hop-by-hop headers, injects
                           correlation ID, streams upstream response)
      routers/
        reads.py           - GET /plans /blocks /tracks /trains -> Query Service
        writes.py          - POST /block-requests, PATCH /block-requests/{id} -> Command Service
  command-service/      (FastAPI, port 8001) - write path, validates + publishes to Kafka
    app/
      main.py            - FastAPI app + lifespan (starts/stops KafkaPublisher)
      config.py          - Settings (port, database_url, kafka_brokers, kafka_enabled)
      db.py              - get_db() session dependency (imports config first)
      kafka.py           - KafkaPublisher (best-effort; log-only fallback if broker down)
      schemas.py         - BlockRequestCreate/Update/Response (reuses contracts payloads)
      validation.py      - validate_create() business rules (Sections 11-12)
      routers/
        block_requests.py - POST /block-requests, PATCH /block-requests/{id}
  query-service/         (FastAPI, port 8002) - read path, Redis cache-aside + Read Store
    app/
      main.py            - FastAPI app + lifespan (builds best-effort Cache), includes routers
      config.py          - Settings (port, read_store_url, redis_url, cache_ttl_seconds)
      db.py              - get_read_store() session dependency (imports config first)
      cache.py           - Cache (best-effort Redis cache-aside) + cache_key + cache_get_or_load
      serialize.py       - row_to_dict() ORM -> JSON-serializable dict
      schemas.py         - PlanSummaryOut, BlockOut, TrackOut, TrainOut
      routers/
        plans.py           - GET /plans (filter status, section_id)
        blocks.py          - GET /blocks (filter plan_id, track_id)
        tracks.py          - GET /tracks (filter section_id, active_only)
        trains.py          - GET /trains (filter active_only)
  optimization-service/  (Python, no HTTP port - Kafka consumer) - Shadow Finder + optimizer
    app/
      main.py            - entrypoint: runs the Kafka consumer loop (python -m app.main)
      config.py          - Settings (database_url, kafka_brokers, kafka_consumer_group)
      db.py              - SessionLocal (imports config first so DATABASE_URL is set)
      shadow_finder.py   - pure: RequestWindow, group_by_track, find_overlapping_clusters
      optimizer.py       - pure: MergedBlock, merge_windows (interval-union)
      planner.py         - run_optimization(): loads SUBMITTED requests, merges, persists
                           Plan/Blocks/PlanItems/affected tracks, marks SCHEDULED, metrics
      consumer.py        - async Kafka consumer (optimization.requests + plan.commands),
                           runs planner, publishes optimization.result
  each service: pyproject.toml, app/__init__.py, app/main.py, .env.example
/frontend
  package.json (Next.js), .env.example, .eslintrc.json, .prettierrc
/infra
  docker-compose.yml   - Phase 4: postgres (16-alpine, db block_planning), redpanda
                         (Kafka-compatible broker), redis (7-alpine), each with healthcheck.
                         Phase 6: postgres also mounts ./postgres-init to create the
                         separate Read Store db (block_planning_read) on first boot.
                         Phase 11 will add the app services + frontend.
  bootstrap_topics.py  - idempotent script creating the Kafka topics from
                         contracts.events.topics (run after `docker compose up`)
  postgres-init/
    01-create-read-db.sql - CREATE DATABASE block_planning_read (runs on first boot only)
Root: .gitignore, .editorconfig, pyproject.toml (shared ruff/black config)
```

## 4. Current Implementation Status

- **Phase 0 (Repo & Tooling Scaffold): DONE.** All service folders, manifests, env
  examples, and lint/format configs exist. No real business logic yet — `app/main.py`
  in each service is a placeholder FastAPI app with only a `/health` endpoint (or, for
  optimization-service, a placeholder `main()` print).
- **Phase 1 (Database Layer): DONE.** SQLAlchemy models for the core-MVP schema live in
  `/db/models` (`base.py`, `enums.py`, `org.py`, `identity.py`, `network.py`,
  `requests.py`, `planning.py`, `events.py`). Alembic is configured (`db/alembic.ini`,
  `db/migrations/env.py`) with a hand-authored initial migration
  (`db/migrations/versions/0001_initial_schema.py` — no live Postgres was available to
  autogenerate). A seed script exists at `db/seed.py`. Tables **included**: zones,
  divisions, sections, departments, users, tracks, track_dependencies, assets, trains,
  train_schedules, restrictions, maintenance, block_requests,
  block_request_affected_tracks, technical_requests, operational_requests, constraints,
  optimization_runs, optimization_results, plans, blocks, plan_items,
  block_affected_tracks, events. Tables **excluded** (backlog, Sections 27-32):
  stations, roles, user_roles, corridor_groups, corridor_group_requests,
  approval_steps, escalations, simulation_runs, simulation_results,
  block_execution_reports, notifications, notification_recipients,
  weather_observations, weather_risk_assessments, audit_logs.
- **Phase 2 (Shared Contracts): DONE.** `/contracts/` holds the Kafka event bus
  contract (architecture Section 15): `events/base.py` (BaseEvent envelope),
  `events/schemas.py` (typed payloads), `events/events.py` (concrete event classes
  `BlockRequestSubmitted`, `BlockRequestUpdated`, `OptimizationRequested`,
  `OptimizationResult`, `TrackStatusChanged`, `TrainDelay` + `EVENT_REGISTRY` +
  `make_event()`), `events/topics.py` (Kafka topic names + `EVENT_TOPIC_MAP`), and 6
  JSON Schema files under `events/json_schemas/`. JSON Schemas are hand-written to
  match the Pydantic models (Pydantic not installed in authoring env) — regenerate &
  diff once a service installs pydantic. See `contracts/README.md`.
- **Phase 3 (Command Service): DONE.** `/services/command-service/app/` now has the
  write path: `config.py` (Settings), `db.py` (session dependency), `kafka.py`
  (best-effort `KafkaPublisher` with log-only fallback), `schemas.py` (API models
  reusing `contracts` payloads), `validation.py` (business rules),
  `routers/block_requests.py` (POST `/block-requests`, PATCH `/block-requests/{id}`),
  and `main.py` (lifespan wiring the publisher). Create validates (Sections 11-12),
  persists request + technical/operational extension + affected tracks + an `events`
  row, commits, then publishes `block_request.submitted` to `plan.commands`. Update
  only allows DRAFT/SUBMITTED requests and publishes `block_request.updated`.
  Also fixed `db/models/events.py` to add `server_default=now()` on `received_at`/
  `created_at` (was missing vs the migration).
- **Phase 4 (Kafka & Broker Setup): DONE.** `/infra/docker-compose.yml` now defines
  `postgres` (16-alpine, db `block_planning`, port 5432), `redpanda` (Kafka-compatible
  broker, port 9092, no Zookeeper), and `redis` (7-alpine, port 6379), each with a
  healthcheck. `/infra/bootstrap_topics.py` idempotently creates the topics from
  `contracts.events.topics`. Run: `docker compose -f infra/docker-compose.yml up -d`
  then `python infra/bootstrap_topics.py`. (Not actually run in this sandbox — no
  Docker; verify on first real `up`.)
- **Phase 5 (AI + Optimization Service): DONE.** `/services/optimization-service/app/`
  is now a Kafka consumer worker (no HTTP). `shadow_finder.py` (pure) groups requests
  by track and finds transitively-overlapping window clusters (Section 17).
  `optimizer.py` (pure) does deterministic interval-union merge of overlapping/touching
  windows into `MergedBlock`s (Sections 18, 20). `planner.py` orchestrates: loads
  `SUBMITTED` block requests, runs the merge per track, persists a `Plan` (PROPOSED) +
  `Block`s + `PlanItem`s (traceability) + `BlockAffectedTrack`s, marks source requests
  `SCHEDULED`, computes metrics, and records an `OptimizationRun` (RUNNING→SUCCEEDED/
  FAILED) + `OptimizationResult`. `consumer.py` subscribes to `optimization.requests`
  and `plan.commands`, deserializes events via `EVENT_REGISTRY`, calls
  `run_optimization()`, and publishes `optimization.result` to `optimization.results`
  (best-effort producer). `main.py` runs the consumer loop. Also fixed
  `db/models/planning.py` to add `server_default=text("now()")` on
  `OptimizationRun.created_at`, `OptimizationResult.created_at`, and
  `PlanItem.created_at` (the migration already had these defaults; the models were
  missing them, which would have failed `alembic check`).
- **Phase 6 (Read Store & CDC/ETL): DONE.** The Read Store is a **separate** Postgres
  database (`block_planning_read`) holding denormalized, dashboard-oriented projections
  (architecture Section 8). New package `/db/readstore/`: `base.py` (`ReadStoreBase` +
  `SyncedMixin` with a `synced_at` freshness stamp), `session.py` (engine/session reading
  `READ_STORE_URL`), `models.py` (four projections — `PlanSummary`, `BlockView`,
  `TrackView`, `TrainView` — aligned with Phase 7's `/plans`, `/blocks`, `/tracks`,
  `/trains` GET endpoints; **no cross-DB foreign keys** since Postgres does not support
  them across databases), `etl.py` (polling **full-refresh** sync: reads the Operational
  DB, recomputes each projection in Python, and atomically delete-all + insert per table;
  supports `--loop --interval N` for continuous polling), plus its own Alembic
  (`readstore/alembic.ini`, `readstore/migrations/env.py` reading `READ_STORE_URL` with
  `target_metadata = ReadStoreBase.metadata`, and a hand-authored
  `0001_initial_read_store.py`). Infra: `infra/postgres-init/01-create-read-db.sql`
  creates `block_planning_read` on first Postgres boot (mounted into the compose
  `postgres` service); `db/.env.example` now documents `READ_STORE_URL`. True CDC
  (Debezium) remains backlog — polling is the MVP approach.
- **Phase 7 (Query Service): DONE.** `/services/query-service/app/` now serves the read
  path (architecture Sections 5–6): `config.py` (Settings: port, read_store_url,
  redis_url, cache_ttl_seconds; mirrors READ_STORE_URL), `db.py` (`get_read_store()`
  session dependency), `cache.py` (best-effort `Cache` wrapper over Redis + `cache_key`
  - `cache_get_or_load` cache-aside helper — degrades to no-cache if Redis is down),
    `serialize.py` (`row_to_dict`), `schemas.py` (response models mirroring the Read Store
    projections), and four routers — `GET /plans` (filter status/section_id),
    `GET /blocks` (filter plan_id/track_id), `GET /tracks` (filter section_id/active_only),
    `GET /trains` (filter active_only). Each endpoint checks Redis first, on a miss reads
    the Read Store projection and populates the cache with a TTL. `main.py` builds the
    `Cache` in the lifespan and includes the routers. The read path never touches Kafka.
    Also aligned `query-service/.env.example` to use `READ_STORE_URL` (was
    `READ_STORE_DATABASE_URL`, which didn't match `db.readstore.session`).
- **Phase 8 (API Gateway): DONE.** `/services/api-gateway/app/` is now a lightweight
  reverse proxy (architecture Section 4): `config.py` (Settings: port,
  command_service_url, query_service_url, auth_enabled, upstream_timeout_seconds),
  `middleware.py` (`CorrelationIdMiddleware` generates/forwards/echoes `X-Correlation-Id`
  per Section 4 items 85-86; `StubAuthMiddleware` does a bearer-token presence check when
  `auth_enabled` — real RBAC is backlog, Section 27), `proxy.py` (`forward()` httpx helper
  that filters hop-by-hop headers, injects the correlation ID, and streams the upstream
  response back, returning 502 if the upstream is unreachable), and two routers —
  `reads.py` (`GET /plans`, `/blocks`, `/tracks`, `/trains` → Query Service) and
  `writes.py` (`POST /block-requests`, `PATCH /block-requests/{id}` → Command Service).
  `main.py` builds a shared `httpx.AsyncClient` in the lifespan, adds the middleware
  (correlation-ID outermost so even auth 401s carry the header), and includes the
  routers. The gateway holds no business logic.
- **Phases 9–14: NOT STARTED (implementation).** Phase 9 (Frontend) has a planning doc,
  [frontend-plan.md](./frontend-plan.md), and is now split into 9A/9B/9C in
  [plan.md](./plan.md) — no frontend code has been written yet.

Always check this section before assuming a phase is complete — update it immediately
when a phase's tasks are finished.

## 5. Conventions

- Ports: api-gateway=8000, command-service=8001, query-service=8002,
  optimization-service=none (background Kafka consumer only).
- Every service has its own `pyproject.toml` (independent dependency sets); shared
  lint config (`ruff`/`black`) lives in the **root** `pyproject.toml` only.
- `.env.example` files exist per service/db/frontend; never commit real `.env` files
  (already covered by root `.gitignore`).
- DB models are defined once in `/db/models` and imported by whichever service needs
  them (command-service, query-service, optimization-service) — do not redefine models
  per-service.
- **Cross-package imports:** services import `db.*` and `contracts.*` as top-level
  packages (e.g. `from db.models import ...`, `from contracts.events import ...`).
  This requires the **repo root** to be on `sys.path` — run services from the repo root
  or install `db` and `contracts` as editable packages (`pip install -e ./db -e
./contracts`). `db.session` reads `DATABASE_URL` at import time, so a service must
  set it (via its `config.py`) **before** importing `db.session` (see
  `command-service/app/db.py`).
- Frontend uses Next.js App/Pages structure — to be decided when Phase 9 starts.

## 6. How to Run (fill in as phases complete)

- Not yet runnable end-to-end (app services not yet in compose — Phase 11).
- Infra: `docker compose -f infra/docker-compose.yml up -d` starts Postgres, Redpanda
  (Kafka), and Redis. Then `python infra/bootstrap_topics.py` creates the topics.
- Command Service: from `services/command-service`, `uvicorn app.main:app --reload`
  (port 8001). It needs `DATABASE_URL` reachable; if Kafka is down it still works and
  just logs events instead of publishing (see `kafka.py`).
- Query Service: from `services/query-service`, `uvicorn app.main:app --reload`
  (port 8002). It needs `READ_STORE_URL` reachable (and the Read Store migrated + synced
  — see Read Store above). If Redis is down it still serves reads, just without caching
  (see `cache.py`). Endpoints: `GET /plans`, `GET /blocks`, `GET /tracks`, `GET /trains`.
- API Gateway: from `services/api-gateway`, `uvicorn app.main:app --reload` (port 8000).
  It is the frontend's entry point and proxies to the other services, so start the
  Command Service and Query Service first. Reads (`GET /plans`, `/blocks`, `/tracks`,
  `/trains`) go to the Query Service; writes (`POST /block-requests`,
  `PATCH /block-requests/{id}`) go to the Command Service. It injects `X-Correlation-Id`
  on every request/response; set `AUTH_ENABLED=true` to require a bearer token.
- Optimization Service: it is a long-running Kafka consumer (no HTTP port). Run
  `python -m app.main` from inside `services/optimization-service/` with the repo root
  on `sys.path` (e.g. `PYTHONPATH=.. python -m app.main` on Unix, or
  `$env:PYTHONPATH=".."; python -m app.main` on Windows). It needs `DATABASE_URL` and
  `KAFKA_BROKERS` reachable, blocks on the consumer loop, and exits on Ctrl-C.
- DB layer: with a Postgres instance reachable at `DATABASE_URL` (see `db/.env.example`),
  run `alembic -c db/alembic.ini upgrade head` from the repo root to apply
  `0001_initial_schema`, then `python -m db.seed` to insert sample data. Not yet
  wired into Docker Compose (that happens in Phase 4/11) — no Postgres has actually
  been run against this migration in this environment yet, so treat it as unverified
  until first real `upgrade head` succeeds.
- Read Store: the separate `block_planning_read` database is created automatically on
  first Postgres boot (via `infra/postgres-init/`). Migrate it with
  `alembic -c db/readstore/alembic.ini upgrade head` (needs `READ_STORE_URL` set). Then
  sync projections from the Operational DB with `python -m db.readstore.etl` (one-shot)
  or `python -m db.readstore.etl --loop --interval 30` (continuous polling). Both need
  `DATABASE_URL` (read) and `READ_STORE_URL` (write) reachable.

---

## 7. Change Log

> Newest entries at the top. One entry per agent turn that changes the repo.

### 2026-09-10 — Frontend brainstorm doc + Phase 9 split into sub-phases (planning only, no code)

- Added [docs/frontend-plan.md](./frontend-plan.md): full frontend brainstorm covering
  stack decisions (Next.js App Router, Tailwind, shadcn/ui, TanStack Query/Table,
  react-hook-form + zod, Recharts, sonner), design system/status color convention,
  information architecture (routes), page-by-page breakdown (dashboard, request forms,
  plan detail with merge explainability, track network, trains, alerts/settings stubs),
  a basic-to-advanced component inventory, data-fetching/polling strategy, and the
  "map" decision: since `stations`/GIS data is backlog (architecture Section 29.6), the
  MVP uses a **schematic track/dependency network diagram (React Flow + dagre layout)**
  instead of a geographic map; a real `react-leaflet` GPS map is documented as a
  stretch/backlog path once station coordinates exist. Also documents a proposed folder
  structure and open questions to confirm at Phase 9A kickoff.
- Rewrote the Phase 9 section of `docs/plan.md`: split the single flat task list into
  **Phase 9A (Foundation & Shell)**, **Phase 9B (Core Read + Write Features)**, and
  **Phase 9C (Visualization & Polish)**, each with a concrete task list, and pointed it
  at `docs/frontend-plan.md` for full rationale.
- Updated this file's Section 3 (repo structure) and Section 1 (key docs) to list
  `docs/frontend-plan.md`.
- No code changes in this turn — planning/documentation only, ahead of Phase 9A
  implementation.

### 2026-09-09 — Phase 8 API Gateway implemented

- Added `/services/api-gateway/app/`: `config.py` (Settings: port, command_service_url,
  query_service_url, auth_enabled, upstream_timeout_seconds), `middleware.py`
  (`CorrelationIdMiddleware` — generates/forwards/echoes `X-Correlation-Id` per Section 4
  items 85-86; `StubAuthMiddleware` — bearer-token presence check when `auth_enabled`,
  real RBAC is backlog Section 27), `proxy.py` (`forward()` httpx helper: filters
  hop-by-hop headers, injects the correlation ID, streams the upstream response, returns
  502 if the upstream is unreachable), and two routers — `reads.py` (`GET /plans`,
  `/blocks`, `/tracks`, `/trains` → Query Service) and `writes.py` (`POST /block-requests`,
  `PATCH /block-requests/{id}` → Command Service).
- Rewrote `main.py` with a lifespan that builds a shared `httpx.AsyncClient`, adds the
  middleware (correlation-ID outermost so even auth 401s carry the header), and includes
  the routers. The gateway holds no business logic (Section 4 items 87-89).
- Updated `api-gateway/.env.example` to document `AUTH_ENABLED` and
  `UPSTREAM_TIMEOUT_SECONDS`.
- Ran `get_errors` on all new/changed files — no static errors.
- Updated `docs/plan.md` to mark Phase 8 done.

### 2026-09-09 — Phase 7 Query Service implemented

- Added `/services/query-service/app/`: `config.py` (Settings: port, read_store_url,
  redis_url, cache_ttl_seconds; mirrors READ_STORE_URL), `db.py` (get_read_store session
  dependency), `cache.py` (best-effort Redis `Cache` + `cache_key` + `cache_get_or_load`
  cache-aside helper — degrades to no-cache if Redis is unreachable), `serialize.py`
  (row_to_dict), `schemas.py` (PlanSummaryOut/BlockOut/TrackOut/TrainOut), and four
  routers: `plans.py` (GET /plans, filter status/section_id), `blocks.py` (GET /blocks,
  filter plan_id/track_id), `tracks.py` (GET /tracks, filter section_id/active_only),
  `trains.py` (GET /trains, filter active_only).
- Each endpoint uses cache-aside: check Redis -> on miss read the Read Store projection
  -> populate cache with TTL (architecture Section 6). The read path never touches Kafka.
- Rewrote `main.py` with a lifespan that builds the `Cache` and includes the routers.
- Aligned `query-service/.env.example` to use `READ_STORE_URL` (was
  `READ_STORE_DATABASE_URL`, which didn't match `db.readstore.session`) and added
  `CACHE_TTL_SECONDS`.
- Ran `get_errors` on all new/changed files — no static errors.
- Updated `docs/plan.md` to mark Phase 7 done.

### 2026-09-09 — Phase 6 Read Store & CDC/ETL implemented

- Added `/db/readstore/` package: `base.py` (`ReadStoreBase` + `SyncedMixin` with
  `synced_at`), `session.py` (engine/session reading `READ_STORE_URL`), `models.py`
  (four denormalized projections — `PlanSummary`, `BlockView`, `TrackView`, `TrainView`
  — aligned with Phase 7's GET endpoints; no cross-DB FKs since the Read Store is a
  separate Postgres database), and `etl.py` (polling full-refresh sync: reads the
  Operational DB, recomputes each projection in Python, atomically delete-all + insert
  per table; `--loop --interval N` for continuous polling).
- Added Read Store Alembic: `readstore/alembic.ini`, `readstore/migrations/env.py`
  (reads `READ_STORE_URL`, `target_metadata = ReadStoreBase.metadata`),
  `readstore/migrations/script.py.mako`, `readstore/migrations/__init__.py`, and a
  hand-authored `readstore/migrations/versions/0001_initial_read_store.py`.
- Infra: added `infra/postgres-init/01-create-read-db.sql` (creates
  `block_planning_read` on first Postgres boot) and mounted it into the compose
  `postgres` service. Updated `db/.env.example` to document `READ_STORE_URL`.
- Ran `get_errors` on all new files — no static errors. (No live Postgres in this
  sandbox, so the Read Store migration + ETL are unverified until first real run.)
- Updated `docs/plan.md` to mark Phase 6 done.

### 2026-09-09 — Phase 5 AI + Optimization Service implemented

- Added `/services/optimization-service/app/`: `config.py` (Settings: database_url,
  kafka_brokers, kafka_consumer_group; mirrors DATABASE_URL), `db.py` (SessionLocal,
  imports config first), `shadow_finder.py` (pure: RequestWindow, group_by_track,
  find_overlapping_clusters via sweep), `optimizer.py` (pure: MergedBlock,
  merge_windows interval-union), `planner.py` (run_optimization orchestration +
  PlanMetrics/OptimizationOutcome), `consumer.py` (async AIOKafkaConsumer loop +
  best-effort producer), and rewrote `main.py` to run the consumer.
- Planner flow: load `SUBMITTED` block requests (optionally scoped by track) -> build
  RequestWindows -> merge per track -> persist Plan (PROPOSED) + Blocks + PlanItems +
  BlockAffectedTracks -> mark requests SCHEDULED -> compute metrics -> record
  OptimizationRun (RUNNING->SUCCEEDED/FAILED) + OptimizationResult.
- Consumer subscribes to `optimization.requests` + `plan.commands`, dispatches
  `OptimizationRequested` via EVENT_REGISTRY, runs the planner, and publishes
  `optimization.result` (only when a plan is created, since plan_id is required in the
  payload).
- Fixed `db/models/planning.py`: added `server_default=text("now()")` to
  `OptimizationRun.created_at`, `OptimizationResult.created_at`, and
  `PlanItem.created_at` (migration already had these; models were missing them).
- Added `make_event` to `contracts/events/__init__.py` re-exports (it was defined in
  `events.py` but not re-exported).
- Ran `get_errors` on all new/changed files — no static errors.
- Updated `docs/plan.md` to mark Phase 5 done.

### 2026-09-09 — Phase 4 Kafka & broker setup implemented

- Populated `/infra/docker-compose.yml` with `postgres` (16-alpine, db
  `block_planning`), `redpanda` (Kafka-compatible broker, no Zookeeper), and `redis`
  (7-alpine), each with a healthcheck and a `pgdata` volume.
- Added `/infra/bootstrap_topics.py` — idempotent script that creates the Kafka topics
  defined in `contracts.events.topics` (skips ones that already exist).
- Verified compose file structure (postgres/redpanda/redis/pgdata present) and ran
  `get_errors` on `bootstrap_topics.py` — no static errors. (Docker not available in
  this sandbox, so the compose stack was not actually started.)
- Updated `docs/plan.md` to mark Phase 4 done.

### 2026-09-09 — Phase 3 Command Service implemented

- Added `/services/command-service/app/`: `config.py` (Settings via pydantic-settings,
  mirrors DATABASE_URL into os.environ), `db.py` (get_db session dependency),
  `kafka.py` (KafkaPublisher — best-effort, falls back to log-only if broker
  unreachable), `schemas.py` (BlockRequestCreate/Update/Response reusing contracts
  payload models), `validation.py` (validate_create business rules per Sections 11-12),
  `routers/__init__.py`, `routers/block_requests.py` (POST + PATCH endpoints), and
  rewrote `main.py` with a lifespan that starts/stops the publisher.
- Write flow: validate -> persist (BlockRequest + Technical/OperationalRequest +
  affected tracks + events row) -> commit -> publish to `plan.commands`.
- Fixed `db/models/events.py`: added `server_default=text("now()")` to `received_at`
  and `created_at` to match the migration (previously the model lacked the default).
- Ran `get_errors` on all new/changed files — no static errors.
- Updated `docs/plan.md` to mark Phase 3 done.

### 2026-09-09 — Phase 2 shared event contracts implemented

- Added `/contracts/` package: `pyproject.toml`, `README.md`, `__init__.py`.
- Added `contracts/events/base.py` (BaseEvent envelope + EventSource),
  `contracts/events/schemas.py` (typed payload models), `contracts/events/events.py`
  (6 concrete event classes + EVENT_REGISTRY + make_event helper),
  `contracts/events/topics.py` (Kafka topic constants + EVENT_TOPIC_MAP), and
  `contracts/events/__init__.py` (re-exports).
- Added 6 JSON Schema (draft 2020-12) files under `contracts/events/json_schemas/`
  (block_request.submitted/updated, optimization.requested/result,
  track.status_changed, train.delay) — hand-written to match the Pydantic models
  since Pydantic is not installed in this environment; validated all 6 parse as JSON.
- Ran `get_errors` on all new Python files — no static errors.
- Updated `docs/plan.md` to mark Phase 2 done.

### 2026-09-08 — Phase 1 database layer implemented

- Added SQLAlchemy models under `db/models/` covering the core-MVP schema from
  `database_schema.md` (org hierarchy, identity, track network, block requests,
  constraints, optimization, plans/blocks, events). See Section 3 above for the
  full file list and Section 4 for the included/excluded table list.
- Added `db/session.py` (engine/session factory) and `db/seed.py` (demo seed data).
- Configured Alembic: `db/alembic.ini`, `db/migrations/env.py` (target_metadata =
  `Base.metadata`), `db/migrations/script.py.mako`, and a hand-authored
  `db/migrations/versions/0001_initial_schema.py` (no live Postgres was available
  in this environment to run `alembic revision --autogenerate`; this migration was
  written directly from `database_schema.md` instead — re-verify with
  `alembic check` once Postgres is reachable).
- Added `db/__init__.py`, `db/migrations/__init__.py` so the package imports
  cleanly (`db.models`, `db.session`, `db.seed`).
- Updated `docs/plan.md` to mark Phase 1 done.
- Ran `get_errors` against all new/changed Python files — no static errors.

### 2026-09-08 — Phase 0 scaffold created

- Created monorepo layout: `/services/{api-gateway,command-service,query-service,
optimization-service}`, `/frontend`, `/db`, `/infra`.
- Added per-service `pyproject.toml` with initial dependency sets, `.env.example`
  files, and placeholder `app/main.py` (FastAPI stub with `/health`, or a print
  placeholder for optimization-service).
- Added root `.gitignore`, `.editorconfig`, and root `pyproject.toml` with shared
  `[tool.ruff]`/`[tool.black]` config.
- Added `frontend/package.json` (Next.js scaffold), `.eslintrc.json`, `.prettierrc`.
- Added `infra/docker-compose.yml` as an empty placeholder (services to be filled in
  Phase 4 and Phase 11).
- Created this file (`docs/agent.md`) and established the mandatory update rule.
- No database, Kafka, Redis, or business logic implemented yet — that starts at
  Phase 1.
