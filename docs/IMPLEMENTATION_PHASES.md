# Implementation Phases — OPUS-5 Complete Rollout

> This document specifies all phases required to fully implement OPUS-5 recommendations in the existing stack.
> Phases 0-11 are documented in plan.md (MVP complete/in-progress).
> This document covers Phases 12-32 (post-MVP, backlog, and extended features).

---

## Overview: Phase Timeline

```
PHASE 0-11 (MVP) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ COMPLETE/IN-PROGRESS
             ↓
PHASE 12-15 (Post-MVP Foundation) ━━━━━━━━━━━━━━ IMMEDIATE (1-2 weeks)
             ↓
PHASE 16-26 (Advanced Features) ━━━━━━━━━━━━━━━━ SHORT-TERM (2-6 weeks)
             ↓
PHASE 27-32 (Governance + Learning Loop) ━━━━━━ MEDIUM-TERM (6-12 weeks)
             ↓
PHASE 33+ (Post-Launch Optimization) ━━━━━━━━━ LONG-TERM (3-6 months)
```

---

## Phase 12: Docker Compose Full Stack & Local Orchestration

**Timeline:** 3 days
**Dependencies:** Phases 0–11 complete
**Objective:** Enable `docker compose up` to bring entire system online with one command

### Tasks

1. **Docker Compose Orchestration (1 day)**
   - [ ] Verify `infra/docker-compose.yml` defines all services (postgres, redpanda, redis, api-gateway, command-service, query-service, optimization-service, frontend)
   - [ ] Validate service dependencies (healthchecks, port mappings, network)
   - [ ] Test local startup: `docker compose -f infra/docker-compose.yml up -d`
   - [ ] Verify all services healthy within 60 seconds
   - [ ] Document startup time and resource requirements

2. **Kafka Topic Bootstrap (0.5 days)**
   - [ ] Update `infra/bootstrap_topics.py` to idempotently create all topics from `contracts.events.topics`
   - [ ] Test topic creation: `python infra/bootstrap_topics.py`
   - [ ] Verify topics list: `docker compose exec redpanda rpk topic list`

3. **Database Seed & ETL Initial Run (0.5 days)**
   - [ ] Run Alembic migrations on container startup: `docker exec postgres alembic upgrade head`
   - [ ] Run seed script: `python db/seed.py`
   - [ ] Verify seed data in Operational DB: stations, trains, sample requests
   - [ ] Run Read Store ETL sync: `python db/readstore/etl.py --loop --interval 5`

4. **Local Dev Documentation (1 day)**
   - [ ] Write `README.md` section: "Quick Start with Docker Compose"
   - [ ] Include:
     - Prerequisites (Docker, Docker Compose)
     - Single-command startup
     - Service URLs and health check endpoints
     - Common troubleshooting (port conflicts, volume cleanup)
     - Frontend access instructions (http://localhost:3004)

### Deliverables

- Single-command local development environment
- All services verified running and healthy
- Documented setup instructions

---

## Phase 13: CI/CD Pipeline & Automated Testing

**Timeline:** 5 days
**Dependencies:** Phase 12
**Objective:** GitHub Actions CI with lint, unit test, integration test, Docker build

### Tasks

1. **Lint & Format Checks (1.5 days)**
   - [ ] Create `.github/workflows/lint.yml` with:
     - Python: `ruff check`, `black --check` per service
     - Frontend: `eslint`, `prettier --check`
     - Runs on every push + PR
   - [ ] Add pre-commit hook script: `.githooks/pre-commit` (optional local)
   - [ ] Document in README

2. **Unit Tests (1.5 days)**
   - [ ] Create `.github/workflows/test-backend.yml`:
     - Command Service: validation logic unit tests
     - Optimization Service: shadow finder + merge logic tests
     - Query Service: cache-aside pattern tests
     - Run: `pytest` per service directory
   - [ ] Create `.github/workflows/test-frontend.yml`:
     - Frontend: component + hook tests (Jest)
     - Run: `npm run test`

3. **Integration Tests (1.5 days)**
   - [ ] Create `.github/workflows/integration.yml`:
     - Spin up `docker compose` in CI
     - Run `_phase11_loop_test.py` (5 iterations)
     - Verify end-to-end: request → optimizer → query → frontend
     - Timeout: 5 min per iteration
   - [ ] Report: pass/fail per iteration

4. **Docker Build & Push (0.5 days)**
   - [ ] Create `.github/workflows/docker.yml`:
     - Build images for all services (conditional: on main branch only)
     - Push to registry (Docker Hub or GitHub Container Registry)
     - Tag: `latest`, git commit SHA

### Deliverables

- GitHub Actions workflows (4 files)
- Green CI on all pushes
- Automated Docker image builds

---

## Phase 14: Testing & Verification Framework

**Timeline:** 4 days
**Dependencies:** Phase 13
**Objective:** Comprehensive test suite covering all critical paths

### Tasks

1. **Unit Test Suite (1.5 days)**
   - [ ] **Command Service** (`services/command-service/tests/`):
     - `test_validation.py`: technical/operational request validation
     - `test_schemas.py`: Pydantic schema edge cases
     - Target: 80% code coverage
   - [ ] **Optimization Service** (`services/optimization-service/tests/`):
     - `test_shadow_finder.py`: overlap detection, merging
     - `test_planner.py`: block creation, impact calculation
     - `test_impact_engine.py`: detention, cancellation computation
     - Target: 80% code coverage
   - [ ] **Query Service** (`services/query-service/tests/`):
     - `test_cache.py`: cache-aside behavior (hit/miss/TTL)
     - `test_serialize.py`: row→dict conversion
     - Target: 75% code coverage

2. **Integration Test Suite (1.5 days)**
   - [ ] **Write Path** (`tests/integration/test_write_path.py`):
     - Submit block request via API Gateway → Command Service
     - Verify persisted in Operational DB
     - Verify Kafka event published
   - [ ] **Read Path** (`tests/integration/test_read_path.py`):
     - Query Read Store via Query Service
     - Verify Redis cache behavior
     - Verify cache invalidation on ETL sync
   - [ ] **Real-Time Loop** (enhanced `_phase11_loop_test.py`):
     - Inject 10 events (train delay, block request, optimization trigger)
     - Verify each flows through system
     - Measure latency: request → plan visible in frontend
     - Assert deterministic behavior (same input → same output)

3. **Test Data & Fixtures (1 day)**
   - [ ] Create `tests/fixtures/`:
     - `sample_network.sql`: Base graph (20 stations, 30 segments)
     - `sample_trains.sql`: 10 train paths
     - `sample_requests.sql`: 5 block requests (various classes)
   - [ ] Seed script for local testing
   - [ ] Documented fixture usage

### Deliverables

- 80%+ code coverage across backend services
- Green integration tests
- Reproducible test environment

---

## Phase 15: Documentation & Demo Preparation

**Timeline:** 3 days
**Dependencies:** Phase 14
**Objective:** Complete documentation for handover and demo readiness

### Tasks

1. **Architecture Documentation (1 day)**
   - [ ] Create `docs/ARCHITECTURE_COMPLETE.md`:
     - Sections 1–26 (MVP) referenced back to code
     - Call stacks for critical paths (request → optimizer → frontend)
     - Service interaction diagrams (Mermaid)
   - [ ] Create `docs/API_SPEC.md`:
     - OpenAPI/Swagger for all endpoints
     - Example requests/responses per endpoint
     - Auth header requirements

2. **Operational Documentation (1 day)**
   - [ ] Create `docs/OPERATIONS.md`:
     - Service startup checklist
     - Healthcheck endpoints
     - Common failure modes + recovery
     - Log inspection guide
     - Kafka topic monitoring
   - [ ] Create `docs/TROUBLESHOOTING.md`:
     - "Frontend not loading" → check API Gateway health
     - "Blocks not appearing" → verify ETL running
     - "Map blank" → check Read Store connectivity
   - [ ] Create `docs/RUNBOOK.md` for on-call operations

3. **Demo Walkthrough Script (1 day)**
   - [ ] Create `docs/DEMO_WALKTHROUGH.md`:
     - Step-by-step demo (5–10 min)
     - Starting point: `http://localhost:3004` dashboard
     - Actions: submit request → see plan → view map
     - Expected outputs at each step
   - [ ] Create demo video script (optional)
   - [ ] Test walkthrough on fresh machine

### Deliverables

- Complete architecture documentation
- API specification
- Operational runbook
- Demo walkthrough + script

---

## Phase 16: Monitoring & Observability

**Timeline:** 4 days
**Dependencies:** Phase 12 (Docker Compose)
**Objective:** Add metrics, logs, and alerting for production readiness

### Tasks

1. **Prometheus Metrics (1.5 days)**
   - [ ] Add to each Python service:
     - `prometheus_client` library
     - HTTP request latency histogram
     - Request counter (by endpoint/status)
     - DB connection pool gauges
     - Kafka producer/consumer lag
   - [ ] Add to frontend:
     - Custom metrics (map render time, API latency)
   - [ ] Create `infra/prometheus.yml` config
   - [ ] Add Prometheus container to docker-compose

2. **Centralized Logging (1.5 days)**
   - [ ] Add Python logging:
     - Structured JSON logs (python-json-logger)
     - Each log includes: timestamp, service, level, correlation-id, message
   - [ ] Add frontend logging:
     - Console + error tracking (Sentry optional)
   - [ ] Create `infra/loki/loki-config.yml` (optional: Grafana Loki)
   - [ ] View logs: `docker compose logs -f service-name`

3. **Health & Readiness Endpoints (1 day)**
   - [ ] Add `/health` endpoint to each service:
     - DB connectivity check
     - Cache (Redis) connectivity check
     - Kafka connectivity check (for optimization service)
     - Returns: 200 if healthy, 503 if degraded
   - [ ] Add `/ready` endpoint (startup complete, accepting traffic)
   - [ ] Update docker-compose healthchecks to use `/health`

### Deliverables

- Metrics collection (Prometheus)
- Structured logging
- Health/readiness endpoints

---

## Phase 17: Performance Tuning & Optimization

**Timeline:** 3 days
**Dependencies:** Phase 16 (metrics available)
**Objective:** Identify and resolve bottlenecks before scale testing

### Tasks

1. **Database Query Optimization (1 day)**
   - [ ] Profile slow queries using PostgreSQL `EXPLAIN ANALYZE`
   - [ ] Add indexes:
     - `block_request.created_at` (for time-range queries)
     - `plan.created_at` (for recent plan retrieval)
     - `train_position.timestamp` (for time-travel queries)
   - [ ] Test query times: target <100ms for single-entity queries

2. **Cache Optimization (1 day)**
   - [ ] Measure Redis hit rate per endpoint
   - [ ] Adjust TTLs:
     - `/plans`: 30s (frequent updates)
     - `/basegraph`: 1h (rarely changes)
     - `/trainpositions`: 10s (high volume)
   - [ ] Implement cache warming (preload on startup)

3. **API Gateway Throughput (1 day)**
   - [ ] Load test with `locust` or `k6`:
     - 100 concurrent requests/sec
     - Measure latency (p50, p95, p99)
     - Identify bottleneck (gateway or upstream services)
   - [ ] Optimize connection pooling
   - [ ] Document results

### Deliverables

- Query performance <100ms
- Cache hit rate >80%
- API throughput benchmark (baseline for scale testing)

---

## Phase 18: Map Visualization Advanced Features

**Timeline:** 5 days
**Dependencies:** Phase 10a complete
**Objective:** Enhanced map features (WebSocket, playback, collision avoidance)

### Tasks

1. **WebSocket Upgrade (2 days)**
   - [ ] Add WebSocket endpoint to Query Service: `/ws/trainpositions?tiles=[...]`
   - [ ] Frontend subscribes on map open
   - [ ] Server pushes position updates when tile version changes
   - [ ] Fallback to HTTP polling if WebSocket fails
   - [ ] Latency improvement target: 1–2 sec (vs 5 sec with 2s poll)

2. **Playback Controls (2 days)**
   - [ ] Add to TimeControls component:
     - Play/pause button
     - Speed slider (1x, 2x, 4x, etc.)
     - Scrubber bar (shows timeline with blocks)
   - [ ] Frontend animates trains through time window
   - [ ] Trains move continuously; blocks appear/disappear at their times

3. **Collision-Avoiding Labels (1 day)**
   - [ ] Implement label placement algorithm (maplibre-gl plugins)
   - [ ] Prevent overlapping train names on screen
   - [ ] Show abbreviated label on zoom out; full name on zoom in

### Deliverables

- WebSocket real-time data stream
- Playback animation
- Smart label placement

---

## Phase 19: What-If Simulation Engine

**Timeline:** 6 days
**Dependencies:** Phase 5 (optimizer) complete
**Objective:** "What if I defer this block 2 hours?" or "Can I merge these?"

### Tasks

1. **Simulation API (3 days)**
   - [ ] New Command Service endpoint: `POST /simulate`
   - [ ] Accept: request modifications, hypothetical delays, new conflicts
   - [ ] Return: proposed plans without persisting to DB
   - [ ] Example: `POST /simulate` with same request but moved 2 hours → show impact
   - [ ] Schema: `SimulationRequest` with delta from current state

2. **Frontend UI (2 days)**
   - [ ] Add "What-If" button on plan detail page
   - [ ] Modal: adjust request fields (time, duration, extent)
   - [ ] Submit → show simulated impacts (trains affected, detention, cost)
   - [ ] Option: "Apply this change" → saves as new plan version

3. **Backend Integration (1 day)**
   - [ ] Reuse impact engine + optimizer logic
   - [ ] Cache simulation results in Redis (TTL 1h)
   - [ ] No impact on Operational DB

### Deliverables

- Simulation API endpoint
- Frontend what-if UI
- Impact preview before committing

---

## Phase 20: Approval Workflow — Multi-Level SLA

**Timeline:** 8 days
**Dependencies:** Phase 1 (DB schema ready), Phase 3 (request validation)
**Objective:** Implement OPUS-5 approval chain with SLA tracking and escalation

### Tasks

1. **Approval State Machine (2 days)**
   - [ ] Update `block_request` state enum:
     - SUBMITTED → AWAITING_APPROVAL → APPROVED → REJECTED
     - Add `approval_level` field (enum: CONTROLLER, SECTION_OFFICER, DIVISION_MANAGER, ZONE_MANAGER)
   - [ ] Create `ApprovalStep` table:
     - request_id, level, approver_role, decision, timestamp, justification, sla_deadline, escalated_at
   - [ ] Add migration for new fields

2. **Approval Chain Logic (2 days)**
   - [ ] Create `services/approval-service/` module (or add to command-service):
     - `routing.py`: Determine approval chain based on block class + extent
     - `sla.py`: Check SLA timers; generate escalations
     - Example: Routine block → SECTION_OFFICER (24h SLA)
   - [ ] Endpoint: `POST /block-requests/{id}/approve` (with decision + justification)
   - [ ] Endpoint: `POST /block-requests/{id}/escalate` (on SLA breach)

3. **SLA Tracking & Alerts (2 days)**
   - [ ] Background job (every 5 min):
     - Query all AWAITING_APPROVAL requests
     - Check deadline vs now
     - If within 1h of deadline: mark escalation-pending
     - If past deadline: escalate to next level
   - [ ] Add to Query Service: `GET /approvals/pending` (SLA breakdown)
   - [ ] Frontend dashboard: shows pending approvals, SLA countdown

4. **Audit Trail for Approvals (2 days)**
   - [ ] Log every approval action:
     - `ApprovalAuditRecord`: request, approver, decision, timestamp, notes
     - Immutable; never updated
   - [ ] Add to frontend: "Approval History" section on plan detail
   - [ ] Shows who approved, when, with what justification

### Deliverables

- Multi-level approval state machine
- SLA tracking with escalation
- Approval audit trail
- Frontend approval dashboard

---

## Phase 21: Notifications & Alerts Service

**Timeline:** 6 days
**Dependencies:** Phase 3 (requests created), Phase 20 (approvals)
**Objective:** Push notifications, email alerts, SMS (optional)

### Tasks

1. **Notification Service Core (2 days)**
   - [ ] New service: `services/notification-service/`
   - [ ] Consumes events from Kafka topics:
     - `plan.created` → notify approvers
     - `block.approved` → notify requesters
     - `approval.escalated` → notify zone manager
   - [ ] Template system (with Jinja2):
     - Approval-pending template (block details + SLA countdown)
     - Block-approved template (plan link + start date)
     - SLA-breach template (escalation notice)

2. **Email Integration (2 days)**
   - [ ] Add email provider (SendGrid or local SMTP)
   - [ ] For each notification type, generate email + send
   - [ ] Track delivery status (delivered, bounced, opened)
   - [ ] Retry on failure (exponential backoff)

3. **Frontend Notifications Bell (1 day)**
   - [ ] Add "Notifications" page: `app/notifications/page.tsx`
   - [ ] Real-time badge on bell icon (unread count)
   - [ ] WebSocket or polling: `GET /notifications` (recent unread)
   - [ ] Mark as read: `PATCH /notifications/{id}`

4. **Optional: SMS Alerts (1 day)**
   - [ ] Twilio integration (optional)
   - [ ] For critical escalations: send SMS to zone manager
   - [ ] Deferred to backlog if not needed

### Deliverables

- Notification service (Kafka → template → email)
- Email templates
- Frontend notification UI

---

## Phase 22: Organizational Hierarchy & RBAC

**Timeline:** 7 days
**Dependencies:** Phase 1 (DB schema ready), Phase 3 (users in context)
**Objective:** Zone/Division/Section organizational model with role-based access

### Tasks

1. **Organization Model (2 days)**
   - [ ] Create tables:
     - `organization_unit` (Zone, Division, Section, Station)
     - `user` (name, email, phone, designation)
     - `user_assignment` (user → unit + role)
     - `role` (enum: CONTROLLER, SECTION_OFFICER, PWI, SSE_OHE, SSE_ST, DOM, DRM)
   - [ ] Add to seed script: sample org hierarchy
   - [ ] Alembic migration

2. **RBAC Middleware (2 days)**
   - [ ] Update API Gateway `StubAuthMiddleware`:
     - Extract user + role from JWT token (currently stub)
     - Inject into request context
   - [ ] Create `@require_role("DRM")` decorator in backend services
   - [ ] Validate: user can only access/approve blocks in their division
   - [ ] Example: Section Controller can grant blocks in their section; DOM approves multi-section

3. **Access Control Rules (2 days)**
   - [ ] Create `db/rules.py`:
     - `can_request_block(user, block_class, extent)` → checks user's unit jurisdiction
     - `can_approve_block(user, approval_level)` → checks user's role
     - `can_view_plan(user, plan)` → checks cross-division visibility
   - [ ] Endpoint middleware: apply rule before handler
   - [ ] Error: 403 Forbidden with reason

4. **Organizational Dashboard (1 day)**
   - [ ] Add to frontend: Org hierarchy view (tree)
   - [ ] Zone manager sees all divisions; division manager sees their sections
   - [ ] Filter blocks/plans by org unit

### Deliverables

- Organization and user models
- RBAC middleware and decorators
- Access control rules
- Org hierarchy dashboard

---

## Phase 23: Corridor Block Bundling

**Timeline:** 5 days
**Dependencies:** Phase 5 (optimizer), Phase 20 (approval workflow)
**Objective:** Pre-declared corridor windows; departments "bid" for bundled slots

### Tasks

1. **Corridor Model (1.5 days)**
   - [ ] Create tables:
     - `corridor` (name, track segments, recurring schedule, bidding_deadline)
     - `corridor_slot` (corridor, date_range, published_at, status: OPEN/CLOSED/FULL)
     - `corridor_bid` (user, corridor_slot, requested_extent, work_type, accepted?)
   - [ ] Alembic migration

2. **Corridor Planner (2 days)**
   - [ ] New endpoint: `GET /corridors` (upcoming open slots)
   - [ ] Endpoint: `POST /corridors/{id}/bid` (submit request to corridor)
   - [ ] Endpoint: `GET /corridor/{id}/bids` (zone manager views all bids)
   - [ ] Planner logic:
     - Merge all accepted bids into single corridor block
     - Compute merged impact (all work together)
     - Return as single plan option

3. **Frontend UI (1.5 days)**
   - [ ] Corridor browser: upcoming slots with "Bid" button
   - [ ] Bid form: select corridor + enter work details
   - [ ] Corridor detail: bids list, merge preview, acceptance status

### Deliverables

- Corridor model and database
- Corridor bidding API
- Frontend corridor browser + bidding UI

---

## Phase 24: Weather & Environmental Risk Integration

**Timeline:** 4 days
**Dependencies:** Phase 5 (optimizer), Phase 20 (approval workflow)
**Objective:** Weather forecast data feeds impact on block feasibility

### Tasks

1. **Weather Data Integration (2 days)**
   - [ ] New service: `services/weather-service/` (or add to optimization-service)
   - [ ] Consume weather API (OpenWeatherMap or national meteorological dept)
   - [ ] Fetch forecast for block date/location
   - [ ] Cache forecast data (Redis, TTL 6h)
   - [ ] Enrich block request with weather info

2. **Risk Scoring (1 day)**
   - [ ] Add risk model: high wind/heavy rain reduce work feasibility
   - [ ] Optimizer constraint: if weather risk > threshold, flag in plan options
   - [ ] Example: "Heavy rain forecasted; block may exceed duration estimate"

3. **Frontend Alert (1 day)**
   - [ ] Plan detail page: show weather forecast on map
   - [ ] Red warning if weather risk high
   - [ ] Option to defer block to safer date

### Deliverables

- Weather forecast integration
- Risk scoring model
- Frontend weather alerts

---

## Phase 25: Post-Block Execution Reporting

**Timeline:** 4 days
**Dependencies:** Phase 1 (DB schema ready), Phase 10 (map/visualization)
**Objective:** Capture actual outcomes; feedback for learning loop

### Tasks

1. **Actuals Capture Form (2 days)**
   - [ ] New frontend page: `app/blocks/[id]/handback/page.tsx`
   - [ ] Form fields (progressive disclosure based on block class):
     - Actual work start/end times
     - Quantum completed (e.g., "35 of 40 rails replaced")
     - Anomalies/issues encountered (free text + photo upload)
     - Actual train delays (if different from plan)
   - [ ] Mobile-friendly (field teams access via phone)

2. **Handback Workflow (1 day)**
   - [ ] Add `handback_status` to block:
     - WORKING → HANDED_BACK_PENDING → HANDED_BACK → CLOSED
   - [ ] Site-in-charge fills handback form
   - [ ] Certifier signs off (digital signature or PIN)
   - [ ] Block closed; actuals recorded

3. **Learning Feedback (1 day)**
   - [ ] ETL loads actuals into Read Store
   - [ ] Compute metrics:
     - Actual vs planned duration (delta %)
     - Work completion rate
     - Delay attribution accuracy
   - [ ] Store in `execution_metrics` table for ML model feeding

### Deliverables

- Handback form UI
- Actuals database records
- Learning feedback pipeline

---

## Phase 26: Audit Trail & Compliance Dashboard

**Timeline:** 4 days
**Dependencies:** Phase 1 (audit schema), Phase 22 (RBAC)
**Objective:** Immutable audit log; compliance reporting

### Tasks

1. **Audit Log Middleware (1.5 days)**
   - [ ] Add to each service: middleware that logs all mutations
   - [ ] Log structure:
     - timestamp, actor (user_id), action (CREATE/UPDATE/APPROVE/REJECT), entity (request/plan/block), entity_id, before, after
     - Include correlation-id (from gateway)
   - [ ] Store in `audit_log` table (append-only)
   - [ ] Test: verify every change is logged

2. **Audit Query API (1 day)**
   - [ ] Endpoint: `GET /audit?entity=block&entity_id=X&from=date&to=date`
   - [ ] Returns: all changes to block X in date range with actor
   - [ ] Example: "2026-09-10 14:30 - User xyz approved block ABC (justification: ...)"

3. **Compliance Dashboard (1.5 days)**
   - [ ] New frontend page: `app/compliance/audit-trail/[id]/page.tsx`
   - [ ] Shows full history of a block request/plan
   - [ ] Timeline view: who touched it, when, what changed
   - [ ] Export to PDF (for regulatory audit)

### Deliverables

- Audit log middleware and schema
- Audit query API
- Compliance audit trail dashboard

---

## Phase 27: ML Model — Duration & Delay Prediction

**Timeline:** 8 days
**Dependencies:** Phase 25 (actuals collected), Phase 6 (ETL pipeline)
**Objective:** Calibrate duration estimates using historical actuals

### Tasks

1. **Data Pipeline for ML (2 days)**
   - [ ] Extract features:
     - Work type, quantum, track condition, weather, season, day-of-week
     - Historical actual_duration for similar work
   - [ ] Create training dataset: `db/ml/training_data.py`
     - Query past completed blocks with actuals
     - Feature engineering (normalize, encode categoricals)
   - [ ] Split: 80% train, 20% test

2. **Duration Prediction Model (3 days)**
   - [ ] Use scikit-learn: Random Forest or Gradient Boosting
   - [ ] Train on historical data:
     - Input: work_type, quantum, track_condition, weather
     - Output: estimated_duration (with confidence interval)
   - [ ] Save model: `services/optimization-service/ml/duration_model.pkl`
   - [ ] Evaluate: RMSE, MAE, R² on test set
   - [ ] Baseline: mean actual duration for work type

3. **Delay Prediction Model (2 days)**
   - [ ] Predict likelihood of delay given:
     - Weather forecast
     - Resource availability
     - Current traffic load
   - [ ] Output: delay_risk (low/medium/high) + estimated delay minutes
   - [ ] Use in optimizer: penalize high-risk blocks in objective

4. **Model Serving (1 day)**
   - [ ] Load model on optimization-service startup
   - [ ] Endpoint: `POST /predict/duration` (internal, not exposed)
   - [ ] Use in request handler: suggest duration based on model

### Deliverables

- ML training pipeline
- Duration prediction model (trained)
- Delay risk classifier
- Model serving in optimizer

---

## Phase 28: Emergency Block Fast-Track Path

**Timeline:** 3 days
**Dependencies:** Phase 20 (approval workflow), Phase 5 (optimizer)
**Objective:** Expedited approval for safety-critical emergency blocks

### Tasks

1. **Emergency Request Schema (1 day)**
   - [ ] Minimal fields (5-7 fields only):
     - Block class: EMERGENCY
     - Reason (fracture/failure/threat)
     - Location (segment)
     - Duration estimate (field entry)
     - Contact number
   - [ ] Validation: reject non-emergency blocks sent to emergency path
   - [ ] No advanced planning required; immediate processing

2. **Emergency Approval Flow (1 day)**
   - [ ] Route: Controller can grant immediately (within shift delegation)
   - [ ] No multi-level approval (formalised retrospectively)
   - [ ] Create block immediately upon controller approval
   - [ ] Notify: DOM, zone manager, safety after the fact

3. **Emergency Override in Optimizer (1 day)**
   - [ ] Emergency blocks are hard constraints in optimizer
   - [ ] Rearrange surrounding blocks to accommodate
   - [ ] If optimizer cannot find feasible plan: alert operations
   - [ ] Return "emergency block fits; plan adjusted" or "cannot fit; proceed with unplanned block at risk"

### Deliverables

- Emergency request fast-track form
- Emergency approval bypass logic
- Emergency block optimizer integration

---

## Phase 29: Field App for Actuals Capture (Mobile)

**Timeline:** 12 days
**Dependencies:** Phase 10 (map), Phase 25 (actuals schema)
**Objective:** React Native / Flutter app for field teams to capture progress

### Tasks

1. **Field App Scaffolding (2 days)**
   - [ ] Create `mobile/` directory (React Native or Flutter)
   - [ ] Minimal UI:
     - Login (offline fallback: cached credentials)
     - My Work (list assigned blocks)
     - Block detail (map, checklist, camera)
     - Sync status indicator

2. **Core Field Workflows (4 days)**
   - [ ] Workflow 1: Readiness checklist (pre-work)
     - "Equipment arrived?" "Caution orders issued?" "Gangs in place?"
     - Submit readiness status → notify controller
   - [ ] Workflow 2: Progress updates
     - Start work, log duration + quantum done, log issues + photos
     - Offline: store locally; sync when connectivity available
   - [ ] Workflow 3: Handback
     - Final checklist, actual duration, handback signature (PIN)
     - Submit → marks block HANDED_BACK

3. **Offline Data Sync (3 days)**
   - [ ] Detect connectivity: offline mode if no network
   - [ ] Local database: SQLite or Realm (React Native)
   - [ ] Sync on reconnect: queue all pending changes, replay against backend
   - [ ] Conflict resolution: server version wins (with user notification)

4. **Map & Photo Capture (3 days)**
   - [ ] Show block extent on map (use same base graph)
   - [ ] Photo capture: embedded camera
     - Geotag photos with GPS
     - Attach to block progress record
   - [ ] Offline map tiles: pre-download for poor connectivity areas

### Deliverables

- Mobile field app (React Native or Flutter)
- Offline data persistence + sync
- Photo capture + geolocation
- Field workflows (readiness, progress, handback)

---

## Phase 30: Resource Scheduling & Feasibility Checking

**Timeline:** 8 days
**Dependencies:** Phase 1 (resource schema), Phase 5 (optimizer), Phase 20 (approval)
**Objective:** Check machine/gang availability; prevent double-booking

### Tasks

1. **Resource Master Data (1.5 days)**
   - [ ] Populate resource tables (hand-authored or seed):
     - Machines: 20 tampers, 10 tower wagons, 5 BCMs (with home bases, maintenance calendars)
     - Gangs: 30 permanent gangs (with competencies: rail/OHE/S&T/general)
     - Materials: inventory locations, quantities
   - [ ] Resource calendar: maintenance windows, roster dates

2. **Feasibility Engine (3 days)**
   - [ ] Module: `services/optimization-service/feasibility.py`
   - [ ] For each requested block, check:
     - Required machine type available in requested window?
     - Required gang count available?
     - Materials in stock?
   - [ ] Return: FEASIBLE / PARTIALLY_FEASIBLE (missing resource, but workaround available) / INFEASIBLE
   - [ ] Integrate into planner: blocks marked FEASIBLE in PlanOption

3. **Resource Conflict Detection (2 days)**
   - [ ] Shadow finder: detect when two blocks require same machine
   - [ ] Output: "Both blocks need tamper; only 1 available. Suggest merging or rescheduling."
   - [ ] Optimizer: soft constraint—penalize conflicts, but allow if no alternative

4. **Resource Booking API (1.5 days)**
   - [ ] When block approved: `POST /block/{id}/book-resources`
   - [ ] Tentatively reserve machine/gang for block duration
   - [ ] Check for conflicts; show to approver
   - [ ] On block start: confirm booking (or auto-confirm if no conflict)

### Deliverables

- Resource master data (machines, gangs, materials)
- Feasibility checking engine
- Resource conflict detection
- Resource booking API

---

## Phase 31: Advanced Conflict Resolution & What-If UI

**Timeline:** 5 days
**Dependencies:** Phase 20 (approvals), Phase 23 (corridor bundling), Phase 30 (resources)
**Objective:** Interactive conflict resolution (suggest merges, rescheduling, resource swaps)

### Tasks

1. **Conflict Resolution Engine (2 days)**
   - [ ] Module: `services/optimization-service/conflict_resolution.py`
   - [ ] Given a conflict (demand×demand, demand×traffic, demand×resource):
     - Suggest 3 resolution options:
       1. Merge blocks (if compatible)
       2. Reschedule one block (+/- 1–7 days)
       3. Use alternative resource (if available)
     - Rank by impact (lowest detention, least resource change)

2. **Interactive Resolution UI (2 days)**
   - [ ] New page: `app/plans/conflicts/page.tsx`
   - [ ] Show unresolved conflicts (demand×demand list)
   - [ ] For each: show suggested resolutions with impact preview
   - [ ] Buttons: "Accept", "Modify", "Reject"
   - [ ] Accept → updates plan, approvers notified

3. **Advanced What-If (1 day)**
   - [ ] Extend Phase 19 what-if UI:
     - "Suggest alternatives" button → shows resolution options above
     - Can simulate multiple changes together: defer block A, merge B+C, then re-optimize

### Deliverables

- Conflict resolution suggestion engine
- Interactive conflict UI
- Advanced what-if simulation

---

## Phase 32: Simulation Engine & Scenario Planning

**Timeline:** 6 days
**Dependencies:** Phase 19 (simulation), Phase 27 (ML models), Phase 30 (resources)
**Objective:** Full-fidelity simulation for strategic planning (annual block calendar)

### Tasks

1. **Simulation Core (2 days)**
   - [ ] Module: `services/simulation-service/` (new service or add to optimization)
   - [ ] Accept: list of hypothetical blocks, time horizon (e.g., "next 3 months")
   - [ ] Simulate: run optimizer over full horizon
   - [ ] Output: all feasible plans ranked, total detention, resource utilization heatmap
   - [ ] Deterministic: same input always produces same output

2. **Scenario Comparison (2 days)**
   - [ ] Frontend: scenario builder
     - Scenario A: "All planned blocks + emergency capacity (20% margin)"
     - Scenario B: "Deferred non-critical work; margin 10%"
     - Compare: side-by-side KPIs (total detention, cancellations, resource conflicts)

3. **Strategic Planning Dashboard (2 days)**
   - [ ] New frontend page: `app/strategic-planning/page.tsx`
   - [ ] Tools:
     - Calendar heatmap (detention by day)
     - Resource utilization graph
     - Scenario comparison table
     - Export: annual plan PDF

### Deliverables

- Full-fidelity scenario simulation engine
- Scenario comparison UI
- Strategic planning dashboard

---

## Phase 33+: Continuous Improvement & Post-Launch

**Timeline:** Ongoing
**Objective:** Monitor, calibrate, and optimize post-MVP

### Tasks (Recurring)

1. **Model Recalibration (monthly)**
   - [ ] Retrain ML models with new actuals
   - [ ] Evaluate: has model accuracy drifted?
   - [ ] Recalibrate if RMSE increases >10%

2. **Performance Monitoring**
   - [ ] Dashboard: latency trends, error rates, cache hit rates
   - [ ] Alert: if API response time > 500ms or error rate > 1%
   - [ ] Analyze and fix

3. **User Feedback Loop**
   - [ ] Monthly surveys: approvers, requesters, field teams
   - [ ] Capture: what's hard? What's missing?
   - [ ] Backlog items based on feedback

4. **Rule Refinement**
   - [ ] Monitor approval SLA breaches
   - [ ] Adjust notice periods, approval chains if pattern emerges
   - [ ] Update configuration (not code)

5. **Extended Features Backlog**
   - [ ] Based on operational feedback, implement:
     - Advanced conflict visualization
     - Predictive maintenance (suggest work before defect becomes critical)
     - Passenger-facing cancellation alerts
     - Freight impact dashboards

---

## Dependency Graph

```
Phase 0-11 (MVP) ✅ COMPLETE
    ↓
Phase 12 (Docker) → Phase 13 (CI) → Phase 14 (Testing) → Phase 15 (Docs)
    ↓
Phase 16 (Observability) → Phase 17 (Performance)
    ↓
Phase 18 (Map Advanced) | Phase 19 (What-If) | Phase 20 (Approval) | Phase 21 (Notifications)
    ↓
Phase 22 (RBAC) | Phase 23 (Corridor) | Phase 24 (Weather) | Phase 25 (Reporting)
    ↓
Phase 26 (Audit) → Phase 27 (ML) → Phase 28 (Emergency)
    ↓
Phase 29 (Mobile App) → Phase 30 (Resources) → Phase 31 (Conflict UI) → Phase 32 (Simulation)
    ↓
Phase 33+ (Continuous Improvement)
```

---

## Timeline Summary

| Phase Group         | Phases | Duration | When                         |
| ------------------- | ------ | -------- | ---------------------------- |
| MVP (Plan.md)       | 0–11   | 2 weeks  | ✅ COMPLETE / 🔄 IN-PROGRESS |
| Post-MVP Foundation | 12–15  | 2 weeks  | IMMEDIATE                    |
| Advanced Features   | 16–26  | 6 weeks  | MONTH 1                      |
| Governance Loop     | 27–32  | 8 weeks  | MONTH 2–3                    |
| Operations/Optimize | 33+    | Ongoing  | MONTH 4+                     |

**Total to Full OPUS-5 Fidelity: ~4 months**

---

## Success Criteria per Phase

| Phase | Success Criteria                                                         |
| ----- | ------------------------------------------------------------------------ |
| 12    | `docker compose up` brings full stack online; healthchecks pass          |
| 13    | All CI workflows green on every commit                                   |
| 14    | 80%+ test coverage; all integration tests pass                           |
| 15    | Architecture & operations docs complete; demo walkthrough works          |
| 16    | Prometheus metrics visible; Loki logs searchable                         |
| 17    | Query latency <100ms; cache hit rate >80%; load test baseline set        |
| 18    | WebSocket endpoint live; playback animation smooth; labels don't overlap |
| 19    | What-If API returns impact in <2 sec; frontend UI responsive             |
| 20    | Multi-level approval chain enforced; SLA escalation working              |
| 21    | Notifications delivered; email templates sent; frontend bell working     |
| 22    | RBAC rules applied; access correctly restricted; org hierarchy visible   |
| 23    | Corridor slots created; bidding mechanism works; merge preview accurate  |
| 24    | Weather forecast integrated; risk scoring calculated; alerts shown       |
| 25    | Actuals form captures data; handback workflow records outcomes           |
| 26    | Audit log immutable; compliance dashboard shows full history             |
| 27    | ML models trained; duration estimates <15% error; deployed to optimizer  |
| 28    | Emergency fast-track works; controller can grant within 30 sec           |
| 29    | Mobile app functional; offline sync works; field teams can submit        |
| 30    | Resource conflicts detected; feasibility checking prevents double-book   |
| 31    | Conflict resolution suggests 3+ options; UI updates plan reactively      |
| 32    | Scenario simulation runs 3-month horizon in <5 min; comparison UI works  |
| 33+   | Model accuracy maintained; performance <500ms p99; <1% error rate        |

---

## Next Step: Phase 12 Kickoff

**Action Items:**

1. Verify `infra/docker-compose.yml` is complete (all services defined)
2. Test: `docker compose -f infra/docker-compose.yml up -d`
3. Run: `python infra/bootstrap_topics.py`
4. Verify: `http://localhost:3004` loads; dashboard shows data
5. Document findings in `docs/README.md`

**Estimated time:** 3 days (Phase 12)

---

**Document Status:** Implementation phases complete. Ready to assign and execute.

**Last Updated:** 2026-09-10
