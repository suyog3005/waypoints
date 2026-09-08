# Build Plan & Workflow — AI-Powered Automatic Block Planning System

> This document is the step-wise implementation plan for building the system described in
> [application_architecture_flow.md](./application_architecture_flow.md) and
> [database_schema.md](./database_schema.md). It divides the work into phases, and each
> phase into single-task units sized so an individual agent/developer can pick up and
> complete one task at a time.

---

## 1. Confirmed Stack Decisions

- **API Gateway, Command Service, Query Service**: Python + FastAPI.
- **AI + Optimization Service**: Python (OR-Tools / PuLP for the optimizer; scikit-learn
  optional for ML-based prediction, per architecture Section 16).
- **Database schema & migrations**: SQLAlchemy models are the single source of truth
  (matches the Python backend, no cross-stack schema duplication), with **Alembic** for
  versioned migrations.
- **Local infra**: Docker Compose (Postgres, Kafka/Redpanda, Redis, all services) plus
  basic CI (lint/test/build via GitHub Actions).
- **Frontend**: React / Next.js (per architecture Section 3).
- **Scope**: Full core MVP = architecture Sections 1–26 (write path, read path, real-time
  loop, basic optimizer, frontend forms/dashboard). Extended features from Sections
  27–32 (RBAC/org hierarchy, approvals, corridor bundling, notifications, weather,
  simulation, audit) are a documented backlog phase, **not** built in the MVP.
- **CDC**: simplified to a polling ETL script for the MVP; true CDC (e.g. Debezium) is
  deferred to backlog.

---

## 2. Phase Breakdown

Each numbered sub-item is one task, sized for one agent/developer to complete at a time.
Dependencies are noted so independent tasks can run in parallel.

### Phase 0 — Repo & Tooling Scaffold ✅ DONE (2026-09-08)

_No dependencies — do this first._

1. Create monorepo layout: `/services/api-gateway`, `/services/command-service`,
   `/services/query-service`, `/services/optimization-service`, `/frontend`, `/db`
   (SQLAlchemy models + Alembic), `/infra` (Docker Compose).
2. Add root tooling: `pyproject.toml`/`requirements.txt` per Python service,
   `package.json` for the frontend, shared `.editorconfig`, `.gitignore`,
   `ruff`/`black` for Python and `eslint`/`prettier` for the frontend.
3. Add `.env.example` files per service (DB URL, Kafka brokers, Redis URL).

> See [docs/agent.md](./agent.md) for the current repo-state snapshot and change log.

### Phase 1 — Database Layer ✅ DONE (2026-09-08)

_Depends on Phase 0._

1. Translate the core-MVP tables from [database_schema.md](./database_schema.md)
   (skip the Section 3/4/7/10.3/12–14 extended-feature tables) into SQLAlchemy models
   under `/db/models`.
2. Configure Alembic and generate the initial migration
   (`alembic revision --autogenerate`).
3. Write a seed script (departments, tracks, trains, sample block requests) for local
   development and demos.

> Note: no live Postgres instance was available in this environment, so the initial
> migration (`db/migrations/versions/0001_initial_schema.py`) was hand-authored from
> `database_schema.md` rather than generated via `--autogenerate`. Re-verify with
> `alembic check` once Postgres is running (Phase 4/11). See
> [docs/agent.md](./agent.md) for the exact table list included/excluded.

### Phase 2 — Shared Contracts ✅ DONE (2026-09-09)

_Depends on Phase 1. Can run in parallel with Phase 3._

1. Define Kafka event JSON Schemas per architecture Section 15 (`plan.commands`,
   `train.events`, `optimization.results`, etc.) under `/contracts/events/`.
2. Hand-write matching Pydantic models for use across the Python services.

> Implemented in `/contracts/`: `events/base.py` (BaseEvent envelope),
> `events/schemas.py` (typed payloads), `events/events.py` (concrete event
> classes + `EVENT_REGISTRY` + `make_event()`), `events/topics.py` (Kafka topic
> names + `EVENT_TOPIC_MAP`), and 6 JSON Schema files under
> `events/json_schemas/`. See [contracts/README.md](../contracts/README.md) and
> [docs/agent.md](./agent.md) for details.

### Phase 3 — Command Service ✅ DONE (2026-09-09)

_Depends on Phases 1, 2._

1. Scaffold the FastAPI app with `/block-requests` POST/PATCH endpoints covering both
   technical and operational request types.
2. Add validation logic (architecture Sections 11/12 fields) using the SQLAlchemy
   models from Phase 1.
3. Publish the validated command as a Kafka event on `plan.commands`.

> Implemented in `/services/command-service/app/`: `config.py` (settings), `db.py`
> (session dependency), `kafka.py` (best-effort `KafkaPublisher`), `schemas.py`
> (API request/response models reusing `contracts` payloads), `validation.py`
> (business validation), `routers/block_requests.py` (POST/PATCH), and `main.py`
> (lifespan wiring the publisher). Events are persisted to the `events` table and
> published to `plan.commands`. See [docs/agent.md](./agent.md).

### Phase 4 — Kafka & Broker Setup ✅ DONE (2026-09-09)

_Depends on Phase 0. Can run in parallel with Phase 3._

1. Add Kafka (or Redpanda) + Zookeeper (if needed) to the Docker Compose file.
2. Write a topic-bootstrap script creating the topics listed in architecture Section 14.

> Implemented in `/infra/`: `docker-compose.yml` now defines `postgres` (16-alpine,
> db `block_planning`), `redpanda` (Kafka-compatible broker, no Zookeeper needed), and
> `redis` (7-alpine), each with a healthcheck. `bootstrap_topics.py` creates the topics
> from `contracts.events.topics` (idempotent — skips existing). Run:
> `docker compose -f infra/docker-compose.yml up -d` then
> `python infra/bootstrap_topics.py`. See [docs/agent.md](./agent.md).

### Phase 5 — AI + Optimization Service ✅ DONE (2026-09-09)

_Depends on Phases 2, 4._

1. Scaffold a Kafka consumer skeleton subscribing to `plan.commands` and relevant
   operational event topics.
2. Implement Shadow Finder overlap detection (architecture Section 17): group requests
   by track and time window.
3. Implement a basic OR-Tools/PuLP feasibility + merge optimizer (architecture Sections
   18/20), hard-constraints-only for the MVP.
4. Write the resulting Plan / Blocks / Plan Items back to the Operational DB via the
   shared SQLAlchemy models.

> Implemented in `/services/optimization-service/app/` (Kafka consumer worker, no HTTP):
> `shadow_finder.py` (pure overlap clustering, Section 17), `optimizer.py` (pure
> interval-union merge — the deterministic MVP strategy for Sections 18/20; full
> OR-Tools/PuLP constraint programming is backlog), `planner.py` (loads `SUBMITTED`
> requests, merges per track, persists Plan/Blocks/PlanItems/affected tracks, marks
> requests `SCHEDULED`, records OptimizationRun + OptimizationResult with metrics),
> `consumer.py` (subscribes `optimization.requests` + `plan.commands`, publishes
> `optimization.result`), `main.py` (runs the loop). Also fixed missing
> `server_default=now()` on three `created_at` columns in `db/models/planning.py` and
> re-exported `make_event` from `contracts.events`. See [docs/agent.md](./agent.md).

### Phase 6 — Read Store & CDC/ETL ✅ DONE (2026-09-09)

_Depends on Phase 1. Can run in parallel with Phase 5._

1. Design Read Store projection tables (denormalized plan/block/train views).
2. Write a simple polling ETL script syncing the Operational DB into the Read Store
   (full CDC/Debezium deferred to backlog).

> Implemented in `/db/readstore/` (a **separate** Postgres database,
> `block_planning_read`, per architecture Section 8): `base.py` (ReadStoreBase +
> SyncedMixin), `session.py` (reads `READ_STORE_URL`), `models.py` (four denormalized
> projections — `PlanSummary`, `BlockView`, `TrackView`, `TrainView` — aligned with
> Phase 7's GET endpoints; no cross-DB FKs), `etl.py` (polling full-refresh sync with
> `--loop --interval N`), and its own Alembic (`readstore/alembic.ini` +
> `migrations/env.py` reading `READ_STORE_URL` + hand-authored
> `0001_initial_read_store.py`). Infra: `infra/postgres-init/01-create-read-db.sql`
> creates the read DB on first boot (mounted into compose); `db/.env.example` documents
> `READ_STORE_URL`. True CDC (Debezium) remains backlog. See [docs/agent.md](./agent.md).

### Phase 7 — Query Service ✅ DONE (2026-09-09)

_Depends on Phase 6._

1. Scaffold the FastAPI app with `/plans`, `/blocks`, `/tracks`, `/trains` GET endpoints.
2. Implement the Redis cache-aside pattern: check cache → Read Store on miss →
   populate cache (architecture Section 6).

> Implemented in `/services/query-service/app/`: `config.py` (Settings), `db.py`
> (get_read_store session dependency), `cache.py` (best-effort Redis `Cache` +
> `cache_get_or_load` cache-aside helper — degrades to no-cache if Redis is down),
> `serialize.py` (row_to_dict), `schemas.py` (response models), and four routers
> (`GET /plans`, `GET /blocks`, `GET /tracks`, `GET /trains`) each with query filters.
> Every endpoint checks Redis first, reads the Read Store projection on a miss, and
> populates the cache with a TTL. `main.py` builds the `Cache` in the lifespan. The read
> path never touches Kafka (Section 6). Also aligned `.env.example` to `READ_STORE_URL`.
> See [docs/agent.md](./agent.md).

### Phase 8 — API Gateway ✅ DONE (2026-09-09)

_Depends on Phases 3, 7._

1. Scaffold the FastAPI gateway routing reads to the Query Service and writes to the
   Command Service (architecture Section 4).
2. Add a stub authentication middleware and correlation-ID header injection.

> Implemented in `/services/api-gateway/app/` (lightweight reverse proxy, Section 4):
> `config.py` (Settings), `middleware.py` (`CorrelationIdMiddleware` for
> `X-Correlation-Id` per items 85-86 + `StubAuthMiddleware` bearer check, real RBAC is
> backlog Section 27), `proxy.py` (`forward()` httpx helper — filters hop-by-hop headers,
> injects the correlation ID, streams the upstream response, 502 on upstream failure),
> and two routers — `reads.py` (`GET /plans`, `/blocks`, `/tracks`, `/trains` → Query
> Service) and `writes.py` (`POST /block-requests`, `PATCH /block-requests/{id}` → Command
> Service). `main.py` builds a shared `httpx.AsyncClient` in the lifespan and adds the
> middleware (correlation-ID outermost). The gateway holds no business logic. See
> [docs/agent.md](./agent.md).

### Phase 9 — Frontend

_Depends on Phase 8 for full integration; the UI shell can start earlier in parallel
with Phases 3–7 using mocked API responses._

Full brainstorm, stack rationale, page-by-page breakdown, component inventory, and the
"map" decision (React Flow schematic vs a geographic map — see rationale there) live in
[docs/frontend-plan.md](./frontend-plan.md). Phase 9 is split into three sub-phases so
it can be tracked incrementally like every other phase.

#### Phase 9A — Foundation & Shell

1. Install and configure Tailwind CSS + shadcn/ui, `next-themes`, `lucide-react`.
2. Set up the TanStack Query provider and the typed API client pointed at the API
   Gateway (`NEXT_PUBLIC_API_GATEWAY_URL`).
3. Build the app shell (root layout, sidebar + topbar layout) and a routing skeleton
   for every page in frontend-plan.md Section 3.
4. Build shared primitives: `StatusBadge`, `DataTable`, `FilterBar`, `EmptyState`,
   `ErrorState`, `KpiCard`, `CorrelationIdBadge`.
5. Wire the dark/light theme toggle.

#### Phase 9B — Core Read + Write Features

1. Implement API hooks for plans/blocks/tracks/trains/block-requests.
2. Build the dashboard (KPIs + recent activity tables).
3. Build the plans list + plan detail (metrics, blocks table, merge explainability
   panel, proposed-vs-active distinction).
4. Build the technical and operational block-request forms (architecture Section 3)
   with zod validation, plus the request list/detail with status timeline.
5. Build the trains list + detail.
6. Wire polling-based refetch intervals and optimistic submit states.

#### Phase 9C — Visualization & Polish

1. Build the track/section schematic network diagram (React Flow) — the track/train
   list and optimization status become visual, not just tabular.
2. Add a Gantt-style block schedule chart to the plan detail page.
3. Add a real-time freshness indicator (surfaces the Read Store's `synced_at`).
4. Build the alerts and settings stub pages (reserve UX slots for backlog features).
5. Accessibility and responsiveness pass; add component tests for the shared
   primitives and forms.

### Phase 10 — Real-Time Loop Wiring

_Depends on Phases 5, 7, 9._

1. Build a small "event injector" script/endpoint to simulate a train-delay or
   track-status event.
2. Verify the full loop: event → optimizer re-run → DB update → ETL → cache
   invalidation → frontend refresh (architecture Section 23).

### Phase 11 — Docker Compose Full Stack

_Depends on all services existing._

1. Compose file wiring Postgres, Kafka, Redis, all four backend services, and the
   frontend — a single `docker compose up` should run everything locally.

### Phase 12 — CI Pipeline

_Depends on Phase 11._

1. GitHub Actions workflow: lint + unit test each service, build Docker images.

### Phase 13 — Testing & Verification

_Can run in parallel with Phase 12; depends on the respective implementation phases._

1. Unit tests: Command Service validation, optimizer merge logic, Query Service
   cache-aside behavior.
2. One integration test for the write path, one for the read path, one for the
   real-time loop.

### Phase 14 — Documentation & Demo Prep

_Last phase._

1. Update the root README with run instructions.
2. Write a demo walkthrough script (for judges/reviewers) referencing this plan and
   the architecture/schema docs.

---

## 3. Backlog (Post-MVP / Extended Features)

Deferred from the MVP; see architecture Sections 27–32 for full detail:

- Organizational hierarchy (Zone/Division/Section/Station) and RBAC (users/roles).
- Approval workflow with multi-step sign-off and SLA escalation.
- Corridor block bundling.
- Emergency/fast-track block requests.
- What-if simulation engine.
- Notifications & alerts service.
- Weather & environmental risk integration.
- Post-block execution reporting / feedback loop.
- Audit trail & compliance logging.
- Full CDC (e.g. Debezium) replacing the polling ETL script.

---

## 4. Verification Checkpoints

1. **After Phase 11**: `docker compose up` brings up the whole stack without manual steps.
2. **After Phase 13**: CI is green on lint, unit, and integration tests.
3. **Manual end-to-end check**: submit a block request via the frontend → confirm it
   flows through the Command Service → Kafka → Optimization Service → Operational DB →
   Read Store → Query Service → frontend dashboard.

---

## 5. Open Considerations

1. **Kafka vs Redpanda** for local dev — Redpanda is lighter and faster to boot in
   Docker Compose; recommended unless Kafka-specific tooling is required.
2. **Frontend start time** — Phase 9 can start in parallel with backend phases using
   mocked API responses instead of waiting for Phase 8 (API Gateway) to be ready.
