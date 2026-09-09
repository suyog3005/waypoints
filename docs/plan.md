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

### Phase 9 — Frontend ✅ DONE (Phase 9A: 2026-09-09)

_Depends on Phase 8 for full integration; the UI shell can start earlier in parallel
with Phases 3–7 using mocked API responses._

Full brainstorm, stack rationale, page-by-page breakdown, component inventory, and the
"map" decision (React Flow schematic vs a geographic map — see rationale there) live in
[docs/frontend-plan.md](./frontend-plan.md). Phase 9 is split into three sub-phases so
it can be tracked incrementally like every other phase.

#### Phase 9A — Foundation & Shell ✅ DONE

1. ✅ Installed and configured Tailwind CSS + shadcn/ui, `next-themes`, `lucide-react`.
2. ✅ Set up the TanStack Query provider and the typed API client pointed at the API
   Gateway (`NEXT_PUBLIC_API_GATEWAY_URL`).
3. ✅ Built the app shell (root layout, sidebar + topbar layout) and a routing
   catch-all (`app/[...slug]/page.tsx`) for unbuilt pages.
4. ✅ Built shared primitives: `StatusBadge`, `DataTable`, `FilterBar`, `EmptyState`,
   `ErrorState`, `KpiCard`, `CorrelationIdBadge`.
5. ✅ Wired the dark/light theme toggle.
6. ✅ Built the dashboard page (KPI cards + skeleton tables awaiting Phase 9B APIs).
7. ✅ Created shadcn/ui primitives (button, badge, card, input, table, skeleton, separator, sonner).
8. ✅ Built all lib utilities (utils.ts, api/client.ts, format.ts).
9. ✅ Set up the styling system (globals.css with CSS variables for light/dark + status colors).
10. ✅ Verified full build with `npm run build` (87.3 kB First Load JS, 5 static pages).

#### Phase 9B — Core Read + Write Features ✅ DONE (2026-09-09)

1. ✅ Implement API hooks for plans/blocks/tracks/trains/block-requests.
2. ✅ Build the dashboard (KPIs + recent activity tables).
3. ✅ Build the plans list + plan detail (metrics, blocks table, merge explainability
   panel, proposed-vs-active distinction).
4. ✅ Build the technical and operational block-request forms (architecture Section 3)
   with zod validation, plus the request list/detail with status timeline.
5. ✅ Build the trains list + detail.
6. ⏳ Wire polling-based refetch intervals and optimistic submit states (deferred to Phase 9C).

#### Phase 9C — Visualization & Polish ✅ DONE (2026-09-09)

1. ✅ Install Recharts dependency for data visualization.
2. ✅ Build the Gantt-style block schedule chart (`BlockGantt` component) on the plan detail page.
3. ✅ Add a real-time freshness indicator (`FreshnessIndicator` component) showing synced_at with color coding.
4. ✅ Build the alerts stub page (event feed layout).
5. ✅ Build the settings stub page (theme toggle + preferences).
6. ✅ Build the network page (simplified schematic — React Flow unavailable due to package version).
7. ✅ Verify full Phase 9C build (14 routes, 0 errors, dev server running).

**Note:** React Flow package version unavailable; network page uses tabular/card-based schematic instead of interactive diagram. Upgrade to full React Flow visualization deferred to Phase 10b+ if needed.

### Phase 10 — Map Visualization & 3D Tiling (Infrastructure/Train Positions)

_Depends on Phases 5, 6 (Read Store), 9 (frontend tooling). This is a major new frontend feature building on the architectural patterns documented in [docs/MAP_VISUALIZATION_ARCHITECTURE.md](./MAP_VISUALIZATION_ARCHITECTURE.md)._

**Rationale:** While Phase 9 provides a solid dashboard with CRUD pages, a production railway block-planning tool requires a map-based visualization showing:

- Track network infrastructure (nodes, edges).
- Real-time train positions on that network.
- Blocks (track segments) occupied by trains.
- Restrictions/maintenance overlays.
- Time-travel capability (view historical or forecast train positions).
- 3D data tiling (X, Y, Time) to avoid transferring all trains for every viewport update.

This is based on patterns proven in [RIVM INFRA](https://gitlab.local.hacon.de/tps/live/nextgen/rivm/rivm-infra) (production railway visualization system).

#### Phase 10a — Core Map Visualization (MVP)

_Estimated 11 days (2 weeks). Detailed breakdown in [PHASE_10A_IMPLEMENTATION.md](../PHASE_10A_IMPLEMENTATION.md)._

**Status: PHASE 10a.4 COMPLETE** (API hooks + tile utilities)

- ✅ Phase 9C completion verified (all 7 tasks done)
- ✅ Dependencies installed: maplibre-gl@5.24.0, zustand@4.5.7, dexie@4.4.2
- ✅ Directory structure created: /stores, /components/map, /app/infrastructure/map
- ✅ Map page created: /app/infrastructure/map/page.tsx
- ✅ Zustand stores created: map.store.ts, tile.store.ts, time.store.ts with TS interfaces
- ✅ localStorage persistence added (map + time stores)
- ✅ Sidebar navigation updated with Map link
- ✅ 5 core map components built (MapContainer, TrainLayer, BlockLayer, TimeControls, MapSidebar)
- ✅ API hooks built (useBaseGraph, useTrainPositions) + tile-management + train-positioning utilities
- ✅ Build verified: 15 routes, 0 errors (map page 287 kB with Maplibre GL)
- 🔄 Next: 10a.5 (map events + polling coordinator)

**10a Frontend Tasks** (8–9 days)

1. **✓ 10a.1 Dependencies & Map Setup** (1 day) — ✅ COMPLETE
   - [x] Install: `maplibre-gl@^5.24.0` ✅
   - [x] Install: `zustand@^4.5.7` ✅
   - [x] Install: `dexie@^4.4.2` ✅
   - [x] Create `/frontend/app/infrastructure/map/page.tsx` ✅
   - [x] Create `/frontend/components/map/` directory ✅
   - [x] Create `/frontend/stores/` directory with 3 stores ✅
   - [x] Verify build passes (15 routes, 0 errors) ✅

2. **✓ 10a.2 State Management** (1 day) — ✅ COMPLETE
   - [x] `stores/map.store.ts` — viewport + layersVisible persisted to localStorage
   - [x] `stores/tile.store.ts` — visible tiles, version cache, loading (no persistence — session state)
   - [x] `stores/time.store.ts` — timeOffset + customTimeEnabled persisted to localStorage
   - [x] Sidebar navigation updated with Map link (/infrastructure/map)
   - [x] Build verified: 15 routes, 0 errors

3. **✓ 10a.3 Core Components** (2 days) — ✅ COMPLETE
   - [x] **`MapContainer.tsx`**: Maplibre GL wrapper, renders nodes + edges from base graph, handles map events (zoom, pan, click)
   - [x] **`TrainLayer.ts`**: Train position GeoJSON builders + time filtering (clustering wired in 10a.6)
   - [x] **`BlockLayer.ts`**: Block occupancy segment derivation + GeoJSON builder
   - [x] **`TimeControls.tsx`**: Slider (−10 to +50 min, 5 s step), display time, reset-to-now button
   - [x] **`MapSidebar.tsx`**: Layer visibility toggles + train list (from useTrains)

4. **✓ 10a.4 API Hooks & Utilities** (1.5 days) — ✅ COMPLETE
   - [x] **`hooks/useBaseGraph()`**: GET /basegraph, staleTime=1h, gcTime=6h
   - [x] **`hooks/useTrainPositions(tiles)`**: POST /trainpositions with tile versioning, refetch every 2 sec
   - [x] **`lib/tile-management.ts`**: `roundToInterval`, `positionToTile`, `getVisibleTiles`, `calculateTileBoundaries`, `parseTileId`
   - [x] **`lib/train-positioning.ts`**: `filterPositionsByTime`, `deriveBlocksFromPositions`, `interpolatePosition`
   - [x] Hooks index updated with new exports

5. **10a.5 Map Events & Polling** (1.5 days)
   - Maplibre move/zoom event handlers → update viewport → trigger tile recalculation
   - Implement polling coordinator: every 2 sec, compute visible tiles → fetch with versions → merge into store
   - Handle cache hits (version unchanged) → skip tile in response
   - Update train/block layers reactively from TanStack Query response

6. **10a.6 Map Layers & Rendering** (1 day)
   - Base graph layer: render nodes as circles (#333, radius 3), edges as lines (#666, width 2)
   - Station labels (minZoom: 12)
   - Platform labels (minZoom: 14)
   - Train layer (clustered by default, uncluster on zoom)
   - Block occupancy overlay (colored segments)
   - Layer visibility toggles → update Maplibre `setLayout({ visibility })`

7. **10a.7 Map Integration into App** (0.5 days)
   - Add `/infrastructure/map` route to app router
   - Update sidebar navigation to include map link
   - Ensure map page uses (shell) layout (sidebar + topbar)
   - Verify responsive layout (map takes full remaining width/height)

**10a Backend Tasks** (2 days)

8. **10a.8 `POST /trainpositions` Endpoint** (1 day)
   - Add to Query Service (`query-service/app/routers/train_positions.py`)
   - Accept `tiles: List[DataTile]` where `DataTile = {id: str, version?: UUID}`
   - Return only positions where tile version has changed (delta transfer)
   - Include `meta.dataTileVersions: Dict[tileId, newVersion]` in response
   - Cache positive responses in Redis (TTL: 10 sec)

9. **10a.9 Tile Version Tracking** (1 day)
   - Create `data_tile` table in Read Store schema (id, version, last_updated, train_count)
   - Update `db/readstore/etl.py` to bump tile version UUIDs when train positions change
   - Implement efficient tile boundary calculation (given train position (x,y), which tiles does it belong to?)

**10a Verification & Testing** (0.5 days)

10. **10a.10 Integration Testing**
    - E2E: Open map → verify base graph renders → verify tiles compute → verify polling loop starts
    - Time-travel: Adjust slider → verify tiles update → verify train positions change appropriately
    - Layer toggles: Toggle trains on/off → verify layer visibility toggles
    - Build verification: `npm run build` passes, no errors

**Output:** Functional map with real-time train visualization, time-travel, and tile-based delta transfer.

#### Phase 10b — Advanced Visualization Features

_Estimated 10 days (future phase)._

1. WebSocket upgrade: replace HTTP polling with `/stream/trainpositions?tiles=[...]` for lower latency (1–2 sec).
2. Restriction overlays: render colored poly-lines on affected track segments (speed, blockage, adhesion).
3. Collision-avoiding train label placement (prevents overlapping labels when trains cluster).
4. Playback controls: animate train movement through a time window (scrub forward/backward with live rendering).
5. Block occupancy visualization: color-code block segments by occupancy status (occupied → orange, planned → yellow, available → gray).
6. Improved popover/tooltip system: hover train → show delay, ETA, platform track; hover restriction → show details.

**Output:** Polished, high-performance map suitable for real-time dispatch workflows.

#### Phase 10c — Optimization & Polish

_Estimated 5+ days (future phase)._

1. Worker thread for tile computation (offload geometric calculations from main thread).
2. Tile pre-fetching: load adjacent tiles as user pans for smoother experience.
3. Mobile responsiveness: sidebar → drawer, touch interactions, small viewport optimization.
4. Accessibility: keyboard navigation (arrow keys to pan, +/– to zoom), screen reader support for train positions.
5. Performance audit: measure map render time, tile transfer time, identify bottlenecks.

### Phase 11 — Real-Time Loop Wiring & Event Injection

_Depends on Phases 5, 7, 10._

1. Build a small "event injector" script/endpoint to simulate a train-delay or track-status event.
2. Verify the full loop: event → optimizer re-run → DB update → ETL → cache invalidation → frontend refresh (architecture Section 23).
3. Run the loop 5+ times to confirm deterministic behavior under repeated optimizations.

### Phase 12 — Docker Compose Full Stack

_Depends on all services existing._

1. Compose file wiring Postgres, Kafka, Redis, all four backend services, and the
   frontend — a single `docker compose up` should run everything locally.

### Phase 13 — CI Pipeline

_Depends on Phase 12._

1. GitHub Actions workflow: lint + unit test each service, build Docker images.

### Phase 14 — Testing & Verification

_Can run in parallel with Phase 13; depends on the respective implementation phases._

1. Unit tests: Command Service validation, optimizer merge logic, Query Service
   cache-aside behavior.
2. One integration test for the write path, one for the read path, one for the
   real-time loop.

### Phase 15 — Documentation & Demo Prep

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
