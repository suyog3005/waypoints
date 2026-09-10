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
- [MAP_VISUALIZATION_ARCHITECTURE.md](./MAP_VISUALIZATION_ARCHITECTURE.md) — **NEW**
  (2026-09-09): Detailed design for Phase 10 map-based visualization, including 3D
  tiling strategy (X, Y, Time), real-time polling, Maplibre GL JS stack,
  backend tile versioning. Based on analysis of RIVM INFRA production railway system.

Read those files before making architectural decisions. This file (`agent.md`)
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
- **Phases 9–14: Phase 9A DONE (Foundation & Shell).** Phase 9A (Frontend foundation)
  completed 2026-09-09. Tailwind + shadcn/ui + TanStack Query set up, app shell
  (root layout, sidebar, topbar, theme toggle) built, shared primitives complete
  (StatusBadge, DataTable, FilterBar, EmptyState, ErrorState, KpiCard,
  CorrelationIdBadge), routing catch-all in place, dashboard page (KPI cards +
  skeleton tables) built, full build verified (87.3 kB First Load JS). npm install
  fixed: added `--registry=https://registry.npmjs.org` to bypass slow/blocked Siemens
  Artifactory (configured in user `.npmrc`). Phases 9B (Core Read + Write Features)
  and 9C (Visualization & Polish) DONE.
- **Phase 10a (Map-based Railway Visualization): 10a.1–10a.10 ALL DONE.**
  Frontend (10a.1–10a.7): Maplibre GL JS 5.24.0 map at `/infrastructure/map` with
  3 Zustand stores (map/tile/time, `subscribeWithSelector` + `persist`), core
  components (MapContainer, TrainLayer, BlockLayer, TimeControls, MapSidebar), API
  hooks (useBaseGraph, useTrainPositions, usePollingCoordinator), tile utilities
  (`lib/tile-management.ts`, `lib/train-positioning.ts`), train clustering + popups +
  restriction overlay, time-travel slider. Build verified (15 routes, 0 errors).
  Backend (10a.8–10a.9): Read Store projections `TrainPosition`/`BaseGraphNode`/
  `BaseGraphEdge`/`DataTile` + migration `0002_map_projections.py`; shared
  `db/readstore/tiling.py` (UTC time-bucketing, identical on write+read); ETL builds
  positions/base-graph/data-tiles with version-bump-on-change (delta transfer);
  Query Service `POST /trainpositions` (delta transfer, Redis TTL 10 s) +
  `GET /basegraph` (Redis TTL 1 h); API Gateway proxy routes for both. Field names
  aligned to frontend (`speed`, `trackId`) and time-bucketing made UTC-consistent.
  **10a.10 (Integration Testing) DONE** — verified E2E against a live local
  PostgreSQL (Operational `waypoints` + Read Store `waypoints_read`, no Redis →
  cache-off). Found & fixed 4 real bugs: (1) duplicate `CREATE TYPE` in the
  Operational migration (manual enum loop + `op.create_table` auto-emit), (2)
  multi-bucket tiling (a position must live in every 15-min bucket it spans, not
  just its `from_time` bucket), (3) missing CORS on the API Gateway (preflight
  405), (4) delta-transfer wipe (flat `positions` list → changed to tile-grouped
  `tiles` + frontend per-tile cache merge). Also fixed a 5th, frontend-only bug
  surfaced during testing: an infinite re-render loop ("Maximum update depth
  exceeded") caused by `updateTileVersion` creating a new Map every poll + the
  merge effect depending on `tiles`. Verified: base graph renders (6 nodes),
  trains render (3 markers + block segments), time-travel slider works, layer
  toggles work, delta transfer (first poll 3 positions / unchanged poll empty, no
  wipe), CORS preflight 200.

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

### 2026-09-10 — Phase 10a.10 Complete (Integration Testing — 5 bugs found & fixed)

- **Phase 10a.10 Status**: ✅ COMPLETE — full E2E verified against live local PostgreSQL (Operational `waypoints` + Read Store `waypoints_read`; no Redis → Query Service runs cache-off).
- **Environment**: Local PostgreSQL 18 (Docker/Rancher daemon would not start). Credentials `postgres` / `ColdVagabond@30` (URL-encode `@` as `%40`; in the Alembic env var use `%%40` to survive configparser interpolation). Python via `uv` (Siemens Artifactory unreachable → `uv run --default-index https://pypi.org/simple`). Services import the shared `db` package from repo root → set `PYTHONPATH=<repo root>`.
- **Bug 1 — duplicate `CREATE TYPE` (Operational migration)**: `db/migrations/versions/0001_initial_schema.py` manually looped `enum_type.create(bind, checkfirst=True)` AND `op.create_table` auto-emits `CREATE TYPE` for named-enum columns → `DuplicateObject` on a fresh DB. Removed the manual loop. Verified: generated SQL now has 7 unique `CREATE TYPE` (was 14).
- **Bug 2 — multi-bucket tiling**: a position was stored only in its `from_time` bucket tile, but the frontend requests the *current display-time* bucket, so a train active 19:06–23:06 UTC was invisible at 20:00. Added `position_tiles(x, y, from_time, to_time) -> list[str]` (every 15-min bucket in the span) to `db/readstore/tiling.py`; ETL `_build_data_tiles` now counts each position in every spanned tile; Query Service `train_positions.py` groups positions by every spanned tile.
- **Bug 3 — missing CORS on API Gateway**: frontend (localhost:3003) fetches cross-origin from localhost:8000; preflight `OPTIONS /basegraph` returned 405. Added `cors_origins` (localhost/127.0.0.1 :3000–3003) to `services/api-gateway/app/config.py` and `CORSMiddleware` (added LAST = outermost, so it answers preflight before auth) in `app/main.py`. Verified: preflight 200 with `Access-Control-Allow-Origin: http://localhost:3003`.
- **Bug 4 — delta-transfer wipe (trains disappeared)**: response was a flat `positions` list; an unchanged-tile poll returned 0 positions and the frontend replaced state with empty → trains vanished. Changed `TrainPositionsResponse` to `tiles: dict[str, list[TrainPositionOut]]` (grouped by tile, the delta unit) in `services/query-service/app/schemas.py` + router; frontend `use-train-positions.ts` type updated; `use-polling-coordinator.ts` now keeps a per-tile cache (`tilePositionsRef`) and merges deltas (replace per-tile, prune non-visible, flatten). Verified: first poll `{'0_0_...': 3}`, unchanged poll `{}` (no wipe).
- **Bug 5 — infinite re-render loop (frontend, surfaced during testing)**: "Maximum update depth exceeded" in `tile.store.ts`. `updateTileVersion` created a new Map every poll → `tileVersionCache` ref changed → `tiles` useMemo recomputed → merge effect (dep `tiles`) re-ran → `updateTileVersion` again → loop. Fixed two ways: (a) `updateTileVersion` is now a no-op when the version is unchanged (`frontend/stores/tile.store.ts`); (b) the merge effect no longer depends on `tiles` — visible IDs are read from a ref (`visibleIdsRef`) so the effect only runs when `data` changes (`frontend/lib/hooks/use-polling-coordinator.ts`).
- **Seed** (`db/seed.py`): added a 3rd track (TRK-C "Goods Loop"), a 2nd train (56789 PASSENGER), and 3 `TrainSchedule` entries spanning current time so the map has live data on a fresh seed.
- **Cleanup**: removed the TEMP `window.__map` debug line from `MapContainer.tsx`; deleted temp scripts `_check_db.py`, `_delta_test.py`, `_refresh_schedules.py`; added `uv.lock` to `.gitignore`.
- **Verified in browser (Playwright)**: base graph renders (6 nodes), trains render (3 markers + 3 block segments), time-travel slider (trains persist at +50 min), layer toggles (Trains → visibility none/visible), delta transfer (no wipe), CORS preflight 200. The only remaining console noise is Next.js 14 dev-mode RSC manifest warnings (known dev-server quirk, non-functional).

### 2026-09-09 — Phase 10a.8 + 10a.9 Complete (Backend Map Endpoints + Tile Versioning)

- **Phase 10a.8 Status**: ✅ COMPLETE — `POST /trainpositions` + `GET /basegraph` in Query Service
- **Phase 10a.9 Status**: ✅ COMPLETE — tile version tracking in ETL (delta transfer)
  - **Read Store models** (`db/readstore/models.py`): added `TrainPosition`, `BaseGraphNode`, `BaseGraphEdge`, `DataTile` (tile_id PK, version UUID, train_count, signature, last_updated).
  - **Shared tiling module** (`db/readstore/tiling.py`, NEW): dependency-light `TILE_SIZE_M` (10 000), `TIME_BUCKET_MINUTES` (15), `time_bucket()`, `tile_id()`, `position_tile()`. Used by BOTH the ETL (write) and Query Service (read) so tile IDs are identical.
  - **ETL** (`db/readstore/etl.py`): `_track_geometry()` (schematic grid: each track horizontal, 10 km, 2.5 km row spacing), `_build_train_positions()` (train at track midpoint per schedule window), `_build_base_graph()` (each track = edge between `{code}-A`/`{code}-B` nodes), `_build_data_tiles()`, `_sync_data_tiles()` (bumps version UUID only when train_count or signature changes; deletes stale tiles). `sync_read_store()` now writes all new projections.
  - **Migration** (`db/readstore/migrations/versions/0002_map_projections.py`, NEW): hand-authored tables for the 4 new projections (no live Postgres to autogenerate).
  - **Schemas** (`services/query-service/app/schemas.py`): `_CamelModel` base (to*camel alias generator, populate_by_name, from_attributes). `TrainPositionOut` (speed serialized as `speed` via validation_alias `speed_kmph`), `DataTileIn`, `TrainPositionsRequest`, `TrainPositionsMeta`, `TrainPositionsResponse`, `BaseGraphNodeOut`, `BaseGraphEdgeOut` (`from*`→ wire`from`, `track_id`→`trackId`), `BaseGraphOut`.
  - **Routers** (Query Service): `routers/train_positions.py` (POST /trainpositions — delta transfer: returns positions only for changed tiles + all latest versions; Redis TTL 10 s), `routers/basegraph.py` (GET /basegraph — Redis TTL 1 h). Both registered in `app/main.py`.
  - **API Gateway** (`services/api-gateway/app/routers/reads.py`): added `GET /basegraph` + `POST /trainpositions` proxy routes (forward() passes POST body via `content=body`).
  - **CRITICAL FIX — field-name alignment**: frontend `TrainPosition.speed` ↔ backend `speed_kmph` (now serialized as `speed`); frontend `BaseGraphEdge.trackId` ↔ backend `track_id` (now serialized as `trackId`). Verified via `model_dump(by_alias=True)`.
  - **CRITICAL FIX — time-bucketing UTC consistency**: frontend `roundToInterval` now formats via `new Date(bucketed).toISOString().slice(0,16)` (UTC); backend `time_bucket()` now buckets + formats in UTC. Both produce identical tile IDs (verified: `12_-1_2026-08-31T09:15`). Previously the frontend bucketed on UTC epoch but formatted in local time, and the backend bucketed on local epoch — mismatched whenever the TZ offset wasn't a multiple of 15 min, which would have broken delta transfer.
  - **Verification**: all Python files `py_compile` clean; Query Service + API Gateway import OK with `/basegraph` + `/trainpositions` registered (OpenAPI); ETL imports + `_track_geometry`/`_build_data_tiles` smoke test pass; Pydantic camelCase serialization confirmed.
  - **Note**: Full E2E (live Postgres + Redis + running services) deferred to 10a.10 — no live DB in this environment.

- **Next Immediate Action** (10a.10): Integration testing — stand up Read Store + Redis, run ETL, verify E2E map flow (base graph render, train positions, delta transfer, time-travel).

### 2026-09-09 — Phase 10a.2 Complete (State Management + localStorage)

- **Phase 10a.2 Status**: ✅ COMPLETE
  - **localStorage Persistence Added**:
    - `map.store.ts`: viewport (zoom, center, extent) + layersVisible persisted via `persist` middleware
    - `time.store.ts`: timeOffset + customTimeEnabled persisted via `persist` middleware
    - `tile.store.ts`: NOT persisted (session-specific tile cache, rebuilt on each viewport change)
  - **Sidebar Navigation Updated**:
    - Added Map link (`/infrastructure/map`) with `Map` icon from lucide-react
    - Placed between Track Network and Trains in nav order
  - **Build Status**: ✅ 15 routes, 0 errors, 87.5 kB shared First Load JS
  - **Persistence Strategy**:
    - `partialize` used to exclude non-persistable state (selections, businessClock, tile cache)
    - Storage keys: `map-store`, `time-store`
    - Zustand `persist` middleware handles hydration on app load

- **Next Immediate Action** (10a.3): Create 5 core map components (MapContainer, TrainLayer, BlockLayer, TimeControls, MapSidebar)

### 2026-09-09 — Phase 10a.3 Complete (Core Map Components)

- **Phase 10a.3 Status**: ✅ COMPLETE
  - **5 Core Components Built** (`frontend/components/map/`):
    - `MapContainer.tsx`: Maplibre GL wrapper. Initializes map with Cartesian style, renders base graph (nodes as circles, edges as lines, station labels), wires move/zoom events → map.store, applies layer visibility. Includes `toLon`/`toLat` coordinate helpers (1 deg ≈ 111 320 m) + mock base graph.
    - `TrainLayer.ts`: `trainPositionsToGeoJSON()`, `filterByTime()`, `MOCK_TRAIN_POSITIONS`. Clustering wired in 10a.6.
    - `BlockLayer.ts`: `deriveBlocks()` (2 000 m segment heuristic per train), `blocksToGeoJSON()`.
    - `TimeControls.tsx`: Offset slider (−10 to +50 min, 5 s step), display time (date-fns), reset-to-now. Reads/writes time.store.
    - `MapSidebar.tsx`: Layer visibility toggles (baseGraph/trains/blocks/labels) + train list from `useTrains({active_only:true})` using `TrainOut` fields (train_id, train_number, is_active, train_type, schedule_count).
  - **Map Page Updated**: `app/infrastructure/map/page.tsx` now renders `<MapContainer />` (was inline placeholder).
  - **index.ts Updated**: Re-exports all map components + types.
  - **Build Status**: ✅ 15 routes, 0 errors. Map page = 287 kB (includes Maplibre GL), shared First Load JS 87.6 kB.
  - **Note**: Train/block layers render data via GeoJSON builders but are not yet added as Maplibre layers (deferred to 10a.6). Base graph renders from mock data (real `useBaseGraph` in 10a.4).

- **Next Immediate Action** (10a.4): Create API hooks (useBaseGraph, useTrainPositions) + utilities (tile-management.ts, train-positioning.ts)

### 2026-09-09 — Phase 10a.4 Complete (API Hooks + Tile Utilities)

- **Phase 10a.4 Status**: ✅ COMPLETE
  - **API Hooks** (`frontend/lib/hooks/`):
    - `use-base-graph.ts`: `useBaseGraph()` — GET /basegraph, staleTime 1h, gcTime 6h, no refetch on focus. Returns `BaseGraphData`.
    - `use-train-positions.ts`: `useTrainPositions({tiles, enabled})` — POST /trainpositions with tile versioning (delta transfer), refetchInterval 2s. Returns `TrainPositionsResponse` (positions + meta.dataTileVersions + meta.businessClock).
  - **Utilities** (`frontend/lib/`):
    - `tile-management.ts`: `roundToInterval` (15-min buckets), `positionToTile`, `getVisibleTiles` (viewport → tile IDs), `calculateTileBoundaries`, `parseTileId`. Constants: `DEFAULT_TILE_SIZE` (10 km), `TIME_BUCKET_MINUTES` (15).
    - `train-positioning.ts`: `filterPositionsByTime`, `deriveBlocksFromPositions`, `interpolatePosition` (for smooth animation).
  - **Hooks index updated**: re-exports `useBaseGraph`, `useTrainPositions`, `TrainPositionsResponse`.
  - **Build Status**: ✅ 15 routes, 0 errors. Map page 287 kB, shared First Load JS 87.6 kB.
  - **Note**: Hooks are created but not yet wired into MapContainer (deferred to 10a.5 polling coordinator). Tile version cache updates from response meta also deferred to 10a.5.

- **Next Immediate Action** (10a.5): Wire map events → tile recalculation + polling coordinator (fetch visible tiles every 2s, merge into stores)

### 2026-09-09 — Phase 10a.5 Complete (Map Events + Polling Loop)

- **Phase 10a.5 Status**: ✅ COMPLETE
  - **Polling Coordinator** (`frontend/lib/hooks/use-polling-coordinator.ts`):
    - Reads viewport extent (map.store) + display time (time.store) reactively.
    - Computes visible tile IDs via `getVisibleTiles()`, attaches cached versions from tile.store.
    - Feeds tiles into `useTrainPositions` (2 s refetchInterval).
    - On response: updates tile version cache (delta transfer) + syncs business clock from `meta.businessClock`.
    - Returns `{ positions, isLoading, error, visibleTiles, displayTime }`.
  - **MapContainer Wiring**:
    - `useBaseGraph()` now supplies live base graph (falls back to mock while loading).
    - `usePollingCoordinator()` drives train + block data.
    - New effects push time-filtered positions into `trains` GeoJSON source and derived blocks into `blocks` source.
    - `addTrainLayers` (circle, minzoom 12, red) + `addBlockLayers` (line, amber, opacity 0.5) added on map load.
  - **Build Status**: ✅ 15 routes, 0 errors. Map page 288 kB, shared First Load JS 87.6 kB.
  - **Note**: Train layer uses simple circles (clustering deferred to 10a.6). No popups yet. Restriction overlay not yet rendered (needs backend data).

- **Next Immediate Action** (10a.6): Map layers polish — train clustering, popups, restriction overlay, label minZoom tuning

### 2026-09-09 — Phase 10a.6 Complete (Map Layers + Rendering)

- **Phase 10a.6 Status**: ✅ COMPLETE
  - **Train Clustering** (`MapContainer.tsx`):
    - `trains` source now `cluster: true` (clusterMaxZoom 13, clusterRadius 45).
    - `train-cluster` (color/radius step by point_count) + `train-cluster-count` (abbreviated count) + `train-point` (individual, no cluster) layers.
  - **Interactions** (`wireMapInteractions`):
    - Cluster click → `getClusterExpansionZoom` → `easeTo` zoom-in.
    - Train point click → Maplibre `Popup` (trainId, track, speed) + `selectTrain` in map.store.
    - Cursor pointer on hover for cluster + point layers.
  - **Restriction Overlay**: `restrictions` source + `restriction-segments` layer (red dashed). Sidebar toggle added. Data fed by backend (10a.8).
  - **Glyphs**: Added `glyphs` source (demotiles.maplibre.org) so symbol/text layers (station labels, cluster counts) render.
  - **Layer Visibility**: Now includes `train-cluster-count` + `restriction-segments`.
  - **Build Status**: ✅ 15 routes, 0 errors. Map page 278 kB, shared First Load JS 87.6 kB.
  - **Note**: Restriction layer renders but has no data yet (backend 10a.8). Cluster count font uses 'Open Sans Bold' from the glyphs source.

- **Next Immediate Action** (10a.7): Verify map integration into app router — sidebar nav link, responsive layout, (shell) layout behavior

### 2026-09-09 — Phase 10a.7 Complete (Map Integration into App Router)

- **Phase 10a.7 Status**: ✅ COMPLETE
  - **Route**: `/infrastructure/map` in app router (outside `(shell)` group, but root layout still wraps it with Sidebar + Topbar).
  - **Sidebar Nav**: Map link (Map icon) — added in 10a.2, verified present.
  - **Topbar Title**: Added "Infrastructure Map" to the titles map.
  - **Layout Fix**: Map page height changed from `h-screen` (overflowed padded `<main>`) to `h-[calc(100vh-5.5rem)]` (topbar h-14 = 3.5rem + main padding 2×1rem = 2rem). Added `rounded-lg` + `overflow-hidden`. Loading fallback now uses `h-full`.
  - **Build Status**: ✅ 15 routes, 0 errors. Map page 278 kB, shared First Load JS 87.6 kB.
  - **Note**: Map is fully integrated into the app shell. Frontend Phase 10a (10a.1–10a.7) is now COMPLETE. Remaining: backend (10a.8–10a.9) + integration testing (10a.10).

- **Next Immediate Action** (10a.8): Backend `POST /trainpositions` endpoint in Query Service (tile versioning + delta transfer)

### 2026-09-09 — Phase 10a.1 Complete (Infrastructure Scaffolding)

- **Phase 10a.1 Status**: ✅ COMPLETE
  - **Dependencies Installed**:
    - `maplibre-gl@^5.24.0` ✅ (25 packages)
    - `zustand@^4.5.7` ✅ (2 packages)
    - `dexie@^4.4.2` ✅ (1 package)
  - **File Structure Created**:
    - `/frontend/stores/` directory with 3 Zustand stores (map, tile, time)
    - `/frontend/components/map/` directory for map components
    - `/frontend/app/infrastructure/map/page.tsx` (placeholder UI with sidebar + map area)
    - Proper TypeScript interfaces and selectors in all stores
  - **Build Status**: ✅ 15 routes, 0 errors, 87.5 kB shared First Load JS
  - **Dev Server**: ✅ Running on http://localhost:3001 with file watching enabled
  - **Git Commit**: `db29d05` - "feat: Phase 10a.1 - Map infrastructure scaffolding"

- **Zustand Store Architecture**:
  - `map.store.ts`: Viewport (zoom, center, extent), feature selection, layer visibility
  - `tile.store.ts`: Visible tiles, version cache, loading state, failed tile tracking
  - `time.store.ts`: Business clock, time offset, custom time picker, displayTime() method
  - All stores use `subscribeWithSelector` middleware for efficient component re-renders
  - Pattern: Stores created with stubs; will be enhanced with localStorage in 10a.2

- **Next Immediate Action** (10a.2): Add localStorage persistence to stores + sidebar navigation update

### 2026-09-09 — Phase 9C Visualization & Polish (DONE) + Phase 10 Map Architecture Designed

- **Phase 9C Completion**:
  - **Recharts Integration** (`npm install` added recharts 2.12.0 + dependencies)
  - **FreshnessIndicator** (`components/freshness-indicator.tsx`): Shows "Last synced X ago" with Clock icon, color-coded (green <1 min, amber >1 min stale), tooltip shows full formatDateTime
  - **BlockGantt** (`components/block-gantt.tsx`): Recharts BarChart visualizing block schedules by track with duration (minutes) and bar coloring by block status
  - **Updated /plans/[id]**: Added FreshnessIndicator to metadata section + new "Block Schedule Visualization" card with BlockGantt component
  - **Stub Pages Created**:
    - `/network` — simplified schematic showing infrastructure: section-grouped tracks with active/inactive badges, KPI cards (sections, total, active, inactive), note about React Flow being unavailable (package version error)
    - `/alerts` — event feed layout with severity KPI cards (critical, warnings, info), empty state, placeholder for Kafka integration + Sonner toasts
    - `/settings` — appearance (theme Light/Dark/System via next-themes), department dropdown, notification checkboxes, API config display (read-only), placeholder for RBAC/approval workflows
  - **Build Verification**: ✅ npm run build successful
    - 14 routes (3 static root + 11 dynamic app shell)
    - First Load JS shared: 87.5 kB (stable baseline)
    - /plans/[id]: 103 kB (includes Recharts bundle)
    - All pages compile without errors or warnings
    - Dev server (`npm run dev`) runs successfully, compiling all routes
  - **Note**: React Flow (@xyflow/react) package version unavailable (attempted install of @^11.10.0 and @^11.9.0 both failed); deferred to Phase 10b+ if needed. Network page uses tabular/card-based schematic instead.

- **Phase 10 Map Architecture Designed**:
  - **New Document**: Created `docs/MAP_VISUALIZATION_ARCHITECTURE.md` (comprehensive 11-section design doc)
  - **Architecture Comparison**: Analyzed RIVM INFRA (production railway visualization) and derived lessons for team-waypoints:
    - RIVM uses OpenLayers 10 + NgRx + RabbitMQ (ETL backend) + HTTP polling (frontend)
    - Team-waypoints: Recommend Maplibre GL JS + Zustand + TanStack Query + IndexedDB (Dexie)
    - 3D data tiling strategy (X, Y, Time) with tile versioning to achieve delta transfer (only changed data)
    - Cartesian coordinate system (schematic) vs RIVM's microscopically-accurate infrastructure
  - **Phase 10a-10c Breakdown**:
    - **Phase 10a** (MVP, 11 days): Core map rendering, base graph from GET /basegraph, 3D tile computation + polling, train positions, time-travel controls, layer toggles, backend tile versioning
    - **Phase 10b** (advanced, 10 days): WebSocket upgrade, restriction overlays, label collision avoidance, playback controls, block occupancy visualization
    - **Phase 10c** (polish, 5+ days): Worker thread for tile math, tile pre-fetching, mobile responsiveness, accessibility
  - **Key Decisions**:
    - Map engine: **Maplibre GL JS** (lighter than OpenLayers, better vector tile + Cartesian support, ~200 kB gzipped)
    - State: **TanStack Query + Zustand** (not NgRx; simpler for Next.js/React)
    - Real-time: **HTTP polling (2 sec)** initially, WebSocket upgrade in Phase 10b
    - Caching: **IndexedDB (Dexie) + localStorage** (same as RIVM pattern)
    - Persistence: localStorage for layer visibility, filter state, custom clock settings

- **Documentation Updated**:
  - `docs/plan.md` Phase 9C section: marked all 7 tasks DONE, added React Flow unavailability note
  - `docs/plan.md` Phase 10: Expanded from stub "Real-Time Loop Wiring" into comprehensive Phase 10a/10b/10c with detailed task lists, effort estimates, dependencies
  - `docs/plan.md` Phase 11-15: Renumbered from Phase 10-14 to Phase 12-15 to accommodate new 10a/10b/10c
  - **New Reference**: Agent notes now point to `docs/MAP_VISUALIZATION_ARCHITECTURE.md` for future map-related work

- **Frontend Tech Stack (confirmed for Phase 10)**:
  - Maplibre GL JS 4.x for map rendering
  - Dexie ^4.4.2 for IndexedDB (already in use for Playwright tests, can be added to frontend)
  - Zustand (new, simple global store for map UI state)
  - Keep TanStack Query for API data fetching (no change to Phase 9C hookss)
  - Keep Tailwind + shadcn/ui for non-map panels (sidebar, details, settings)

### 2026-09-09 — Phase 9B Core Read + Write Features (DONE)

- **API Hooks** (`lib/hooks/*`): Implemented 5 query hooks + 2 mutation hooks:
  - `usePlans(filters?)` — GET /plans with status/section_id filtering
  - `useBlocks(filters?)` — GET /blocks with plan_id/track_id filtering
  - `useTracks(filters?)` — GET /tracks with section_id/active_only filtering
  - `useTrains(filters?)` — GET /trains with active_only filtering
  - `useCreateBlockRequest()` — POST /block-requests (mutation)
  - `useUpdateBlockRequest(requestId)` — PATCH /block-requests/{id} (mutation)
  - All hooks use TanStack Query with staleTime=10s, retry=1, no refetchOnWindowFocus
  - `lib/hooks/types.ts` defines 10+ response types matching backend schemas exactly
- **Pages Built**:
  - `/dashboard` — now dynamic, KPI cards pull real data (active plans, pending requests, block hours, merge ratio)
  - `/plans` — list with status/section filtering (Suspense + useSearchParams pattern)
  - `/plans/[id]` — detail view, metadata + blocks table with block metadata (track, start/end, duration, merge status, request count)
  - `/requests` — list page structure (placeholder data for now)
  - `/requests/[id]` — detail view structure (placeholder, awaiting block-requests API endpoint)
  - `/requests/new` — full form with react-hook-form + zod validation, Technical + Operational conditional fields
  - `/trains` — list using useTrains, shows train number, type, schedule count, active status
  - `/trains/[id]` — detail view with train metadata, awaiting schedule data endpoint
- **Form Implementation** (`/requests/new`):
  - Dual-mode form: Technical (train stops, railway line, direction, restriction type, train type, finance ref) or Operational (reason, reason details, duration, safety notes)
  - Zod validation schema with defaults (priority='normal', is_emergency=false, request_type='technical')
  - react-hook-form wired to form state, @hookform/resolvers for validation
  - Side panel with form guide / context
  - TODO: wire mutation submission to useCreateBlockRequest
- **Dependencies Added**: react-hook-form 7.52.0, @hookform/resolvers 3.4.0 (already had zod, date-fns)
- **Next.js Patterns**:
  - Used Suspense boundary + separate client component (PlansContent, RequestsContent) to wrap useSearchParams calls, avoiding static prerender errors
  - Dashboard converted to client component, no longer static prerendered
  - formatDateTime now consistently takes ISO string, not Date objects
  - All pages in (shell) layout properly inherit sidebar + topbar
- **Build Verification**: ✅ npm run build successful
  - 9 routes total (3 new from Phase 9A)
  - /requests/new: 27.6 kB page size (forms add overhead)
  - Other new pages: 1-5 kB
  - Shared First Load JS: 87.3 kB (same as 9A baseline)
  - 9 routes: 3 static prerendered (/, /\_not-found, [.slug]), 6 dynamic (dashboard, plans, plans/[id], requests, requests/[id], trains, trains/[id], requests/new)

### 2026-09-09 — Phase 9A Frontend Foundation & Shell complete (DONE)

- Added `/frontend/` source tree with full Phase 9A implementation:
  - **Config files**: `tsconfig.json`, `next.config.mjs`, `postcss.config.mjs`,
    `tailwind.config.ts`, `components.json`, `next-env.d.ts`.
  - **Dependencies**: Updated `package.json` with Tailwind, shadcn/ui, TanStack Query,
    lucide-react, next-themes, sonner, date-fns, zod, react-hook-form, tailwind-merge,
    class-variance-authority, @radix-ui/react-slot. **npm install fix**: Added
    `--registry=https://registry.npmjs.org` to bypass slow Siemens Artifactory
    (configured in user `.npmrc`). 401 packages installed successfully in ~2 minutes.
  - **Styling**: `app/globals.css` (Tailwind reset + CSS variables for light/dark modes
    - status color convention from frontend-plan.md §2).
  - **shadcn/ui primitives**: `components/ui/button.tsx`, `badge.tsx`, `card.tsx`,
    `input.tsx`, `table.tsx`, `skeleton.tsx`, `separator.tsx`, `sonner.tsx` (Toaster
    wrapper).
  - **Providers**: `components/providers/theme-provider.tsx` (next-themes),
    `query-provider.tsx` (TanStack Query).
  - **Utilities**: `lib/utils.ts` (cn() classname merger), `lib/api/client.ts` (typed
    fetch wrapper + correlation-ID passthrough), `lib/format.ts` (IST-aware date/time
    formatters).
  - **App shell**: `app/layout.tsx` (root, wires ThemeProvider + QueryProvider +
    Toaster), `components/layout/sidebar.tsx` (nav sidebar with active link styling),
    `components/layout/topbar.tsx` (header with breadcrumb + CorrelationIdBadge +
    ThemeToggle), `components/theme-toggle.tsx` (Sun/Moon button).
  - **Shared primitives**: `StatusBadge` (status → color + label), `DataTable` (generic
    table with loading/error/empty states), `FilterBar` (URL-param-backed filters),
    `EmptyState` (consistent "no data" panel), `ErrorState` (error + retry UI),
    `KpiCard` (metric card with icon + value), `CorrelationIdBadge` (dev-only
    correlation ID display), `PageHeader` (title + description + action slot),
    `StubCard` (page-not-yet-built indicator).
  - **Routing skeleton**: `app/page.tsx` (redirects to /dashboard), `app/dashboard/page.tsx`
    (KPI cards + skeleton tables), `app/[...slug]/page.tsx` (catch-all for unbuilt
    routes — shows "Not built yet" + back link; real pages in 9B/9C automatically
    override).
- **Build verification**: `npm run build` succeeds; full production build: 87.3 kB First
  Load JS, 5 static pages, 0 errors.
- Updated `docs/plan.md` Phase 9A section to mark as DONE with full task checklist.
- Updated `docs/agent.md` Section 4 status to reflect Phase 9A complete + Phases 9B/9C
  not started.
- **Note**: Git history (commit authors) was rewritten to use `suyog3005 <suyoggosavi30@gmail.com>`
  to remove all traces of company email/name per user request (separate task, completed
  before Phase 9A).

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
