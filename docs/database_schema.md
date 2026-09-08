# AI-Powered Automatic Block Planning System

## PostgreSQL Database Schema (Operational DB)

> This schema implements the entities and relationships described in
> [application_architecture_flow.md](./application_architecture_flow.md) (Sections 9–13,
> 17–20, 27–32). It represents the **Operational DB** — the authoritative source of truth.
> The Read Store (denormalized/materialized views) and Redis (cache) are not modeled here;
> they are derived from this schema via CDC/ETL.

---

## 1. Design Principles

- PostgreSQL is the primary engine. `TimescaleDB` extension is recommended for append-heavy,
  time-ordered tables: `events`, `optimization_results`, `audit_logs`, `weather_observations`.
- All primary keys use `UUID` (via `gen_random_uuid()`, requires `pgcrypto`) for safe
  distributed/event-driven ID generation.
- All tables include `created_at` / `updated_at` timestamps for auditability.
- State transitions use enum types instead of free-text strings.
- Foreign keys enforce referential integrity; cascading deletes are avoided in favor of
  restrict/soft-delete to preserve traceability ("never lose the original user request").
- JSONB is used sparingly for extensible/loosely-structured attributes, while core planning
  and query fields remain strongly typed columns.
- The schema is organized around the real-world **Zone → Division → Section → Station/Track**
  hierarchy so data, dashboards, and access control can be scoped correctly.
- Every state-changing table has a corresponding audit trail via the generic `audit_logs`
  table rather than per-table history tables, to keep the schema maintainable.

---

## 2. Extensions & Types

```sql
CREATE EXTENSION IF NOT EXISTS pgcrypto;    -- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS timescaledb; -- optional, for time-series tables

CREATE TYPE request_status AS ENUM (
    'draft', 'submitted', 'under_review', 'approved', 'rejected',
    'merged', 'scheduled', 'in_progress', 'completed', 'aborted', 'cancelled'
);

CREATE TYPE request_priority AS ENUM ('normal', 'high', 'emergency');

CREATE TYPE plan_status AS ENUM (
    'proposed', 'approved', 'active', 'completed', 'superseded', 'cancelled'
);

CREATE TYPE request_type AS ENUM ('technical', 'operational');

CREATE TYPE optimization_run_status AS ENUM ('pending', 'running', 'succeeded', 'failed');

CREATE TYPE constraint_severity AS ENUM ('hard', 'soft');

CREATE TYPE event_source AS ENUM ('internal', 'external');

CREATE TYPE approval_decision AS ENUM ('pending', 'approved', 'rejected', 'escalated');

CREATE TYPE notification_channel AS ENUM ('email', 'sms', 'push', 'in_app');

CREATE TYPE notification_status AS ENUM ('pending', 'sent', 'failed', 'read');

CREATE TYPE simulation_status AS ENUM ('pending', 'running', 'completed', 'failed', 'promoted');

CREATE TYPE weather_risk_level AS ENUM ('low', 'moderate', 'high', 'severe');
```

---

## 3. Organizational Hierarchy

Real railway networks are organized as Zone → Division → Section → Station, and Tracks
belong to Sections. This scopes requests, plans, dashboards, and RBAC correctly
(architecture Section 29.10).

### 3.1 `zones`

```sql
CREATE TABLE zones (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(150) NOT NULL UNIQUE,
    code        VARCHAR(20)  NOT NULL UNIQUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### 3.2 `divisions`

```sql
CREATE TABLE divisions (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    zone_id     UUID NOT NULL REFERENCES zones(id),
    name        VARCHAR(150) NOT NULL,
    code        VARCHAR(20)  NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT division_code_unique UNIQUE (zone_id, code)
);
```

### 3.3 `sections`

A "Section" here is the railway operating section (a stretch of line between two
control points), not a SQL section.

```sql
CREATE TABLE sections (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    division_id UUID NOT NULL REFERENCES divisions(id),
    name        VARCHAR(150) NOT NULL,
    code        VARCHAR(20)  NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT section_code_unique UNIQUE (division_id, code)
);
```

### 3.4 `stations`

```sql
CREATE TABLE stations (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    section_id  UUID NOT NULL REFERENCES sections(id),
    name        VARCHAR(150) NOT NULL,
    code        VARCHAR(20)  NOT NULL UNIQUE,
    latitude    NUMERIC(9,6),
    longitude   NUMERIC(9,6),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

---

## 4. Identity & Access Control

### 4.1 `departments`

```sql
CREATE TABLE departments (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(150) NOT NULL UNIQUE,
    code            VARCHAR(20)  NOT NULL UNIQUE,
    contact_email   VARCHAR(255),
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### 4.2 `roles`

Fixed set of platform roles (architecture Section 28): `requester`, `section_controller`,
`divisional_planner`, `safety_officer`, `field_supervisor`, `admin`.

```sql
CREATE TABLE roles (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(50) NOT NULL UNIQUE,
    description TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### 4.3 `users`

```sql
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_code   VARCHAR(50) UNIQUE,
    full_name       VARCHAR(150) NOT NULL,
    email           VARCHAR(255) NOT NULL UNIQUE,
    phone           VARCHAR(20),
    password_hash   TEXT NOT NULL,       -- store only a salted hash (e.g. bcrypt/argon2)
    department_id   UUID REFERENCES departments(id),
    division_id     UUID REFERENCES divisions(id),
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    last_login_at   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

> Security note: never store plaintext passwords; `password_hash` must use a strong,
> salted hashing algorithm. Session/JWT tokens are managed at the API Gateway, not in
> this table.

### 4.4 `user_roles`

Many-to-many; a user may hold multiple roles, optionally scoped to a section.

```sql
CREATE TABLE user_roles (
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id     UUID NOT NULL REFERENCES roles(id),
    section_id  UUID REFERENCES sections(id),   -- NULL = not section-scoped (e.g. admin)
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, role_id, section_id)
);
```

---

## 5. Track Network & Assets

### 5.1 `tracks`

```sql
CREATE TABLE tracks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    section_id      UUID NOT NULL REFERENCES sections(id),
    code            VARCHAR(50) NOT NULL UNIQUE,
    name            VARCHAR(150) NOT NULL,
    line            VARCHAR(100),
    direction       VARCHAR(20),          -- e.g. UP / DOWN / BIDIRECTIONAL
    segment_start   VARCHAR(100),
    segment_end     VARCHAR(100),
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    metadata        JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_tracks_section ON tracks (section_id);
```

### 5.2 `track_dependencies`

Network topology relationships used by Track Dependency Analysis / Shadow Finder
(architecture Sections 17, 19).

```sql
CREATE TABLE track_dependencies (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    track_id            UUID NOT NULL REFERENCES tracks(id),
    affected_track_id   UUID NOT NULL REFERENCES tracks(id),
    relationship_type   VARCHAR(50) NOT NULL, -- e.g. ADJACENT, CROSSING, SHARED_ASSET
    notes               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT track_dependency_not_self CHECK (track_id <> affected_track_id),
    CONSTRAINT track_dependency_unique UNIQUE (track_id, affected_track_id, relationship_type)
);
```

### 5.3 `assets`

```sql
CREATE TABLE assets (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    track_id        UUID REFERENCES tracks(id),
    name            VARCHAR(150) NOT NULL,
    asset_type      VARCHAR(50) NOT NULL,  -- e.g. BRIDGE, SIGNAL, OHE, CABLE, CROSSING
    status          VARCHAR(30) NOT NULL DEFAULT 'operational',
    metadata        JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### 5.4 `trains`

```sql
CREATE TABLE trains (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    train_number    VARCHAR(20) NOT NULL UNIQUE,
    train_type      VARCHAR(50),           -- e.g. EXPRESS, FREIGHT, LOCAL
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    metadata        JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### 5.5 `train_schedules`

```sql
CREATE TABLE train_schedules (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    train_id        UUID NOT NULL REFERENCES trains(id),
    track_id        UUID NOT NULL REFERENCES tracks(id),
    scheduled_start TIMESTAMPTZ NOT NULL,
    scheduled_end   TIMESTAMPTZ NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT train_schedule_time_check CHECK (scheduled_end > scheduled_start)
);

CREATE INDEX idx_train_schedules_track_time
    ON train_schedules (track_id, scheduled_start, scheduled_end);
```

### 5.6 `restrictions`

Speed and operational restrictions with validity intervals (architecture item 235).

```sql
CREATE TABLE restrictions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    track_id            UUID REFERENCES tracks(id),
    restriction_type    VARCHAR(50) NOT NULL,   -- e.g. SPEED, LOAD, CAUTION_ORDER
    description         TEXT,
    max_speed_kmph      INTEGER,
    valid_from          TIMESTAMPTZ NOT NULL,
    valid_to            TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT restriction_validity_check CHECK (valid_to IS NULL OR valid_to > valid_from)
);

CREATE INDEX idx_restrictions_track_validity
    ON restrictions (track_id, valid_from, valid_to);
```

### 5.7 `maintenance`

```sql
CREATE TABLE maintenance (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    track_id                    UUID REFERENCES tracks(id),
    asset_id                    UUID REFERENCES assets(id),
    department_id               UUID REFERENCES departments(id),
    description                 TEXT NOT NULL,
    required_duration_minutes   INTEGER,
    is_recurring                BOOLEAN NOT NULL DEFAULT FALSE,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

---

## 6. Block Requests

### 6.1 `block_requests`

```sql
CREATE TABLE block_requests (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    department_id       UUID NOT NULL REFERENCES departments(id),
    requested_by_user_id UUID NOT NULL REFERENCES users(id),
    request_type        request_type NOT NULL,
    priority            request_priority NOT NULL DEFAULT 'normal',
    track_id            UUID NOT NULL REFERENCES tracks(id),
    requested_start     TIMESTAMPTZ NOT NULL,
    requested_end       TIMESTAMPTZ NOT NULL,
    status              request_status NOT NULL DEFAULT 'draft',
    is_emergency        BOOLEAN NOT NULL DEFAULT FALSE,
    submitted_at        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT block_request_time_check CHECK (requested_end > requested_start)
);

CREATE INDEX idx_block_requests_track_time
    ON block_requests (track_id, requested_start, requested_end);
CREATE INDEX idx_block_requests_status ON block_requests (status);
CREATE INDEX idx_block_requests_priority ON block_requests (priority) WHERE is_emergency;
```

### 6.2 `block_request_affected_tracks`

```sql
CREATE TABLE block_request_affected_tracks (
    block_request_id   UUID NOT NULL REFERENCES block_requests(id) ON DELETE CASCADE,
    track_id            UUID NOT NULL REFERENCES tracks(id),
    reason              VARCHAR(255),
    PRIMARY KEY (block_request_id, track_id)
);
```

### 6.3 `technical_requests`

```sql
CREATE TABLE technical_requests (
    block_request_id           UUID PRIMARY KEY REFERENCES block_requests(id) ON DELETE CASCADE,
    train_stops                 TEXT,
    railway_line                 VARCHAR(100),
    direction                    VARCHAR(20),
    restriction_type             VARCHAR(50),
    train_type                   VARCHAR(50),
    finance_reference             VARCHAR(100),
    responsible_department_id     UUID REFERENCES departments(id),
    additional_parameters        JSONB,
    created_at                   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                    TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### 6.4 `operational_requests`

```sql
CREATE TABLE operational_requests (
    block_request_id           UUID PRIMARY KEY REFERENCES block_requests(id) ON DELETE CASCADE,
    reason                      VARCHAR(50) NOT NULL, -- BRIDGE, UNDERPASS, ROAD_CROSSING,
                                                        -- TREE_WORK, CABLE_MAINTENANCE,
                                                        -- TRACK_MAINTENANCE, OTHER
    reason_details               TEXT,
    expected_duration_minutes    INTEGER,
    safety_notes                 TEXT,
    additional_parameters        JSONB,
    created_at                   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                    TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### 6.5 `corridor_groups`

Groups multiple compatible block requests into a single bundled Corridor Block
(architecture Section 29.1).

```sql
CREATE TABLE corridor_groups (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    section_id      UUID NOT NULL REFERENCES sections(id),
    name            VARCHAR(150),
    created_by_optimization_run_id UUID REFERENCES optimization_runs(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE corridor_group_requests (
    corridor_group_id  UUID NOT NULL REFERENCES corridor_groups(id) ON DELETE CASCADE,
    block_request_id    UUID NOT NULL REFERENCES block_requests(id),
    PRIMARY KEY (corridor_group_id, block_request_id)
);
```

---

## 7. Approval Workflow

### 7.1 `approval_steps`

Defines the ordered chain of approvals required for a request (varies by request
type/risk level, architecture Section 29.3).

```sql
CREATE TABLE approval_steps (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    block_request_id     UUID NOT NULL REFERENCES block_requests(id) ON DELETE CASCADE,
    step_order           SMALLINT NOT NULL,
    required_role_id     UUID NOT NULL REFERENCES roles(id),
    decision             approval_decision NOT NULL DEFAULT 'pending',
    decided_by_user_id    UUID REFERENCES users(id),
    decided_at            TIMESTAMPTZ,
    comments              TEXT,
    sla_due_at            TIMESTAMPTZ,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT approval_step_order_unique UNIQUE (block_request_id, step_order)
);

CREATE INDEX idx_approval_steps_pending
    ON approval_steps (sla_due_at) WHERE decision = 'pending';
```

### 7.2 `escalations`

```sql
CREATE TABLE escalations (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    approval_step_id     UUID NOT NULL REFERENCES approval_steps(id) ON DELETE CASCADE,
    escalated_to_role_id  UUID NOT NULL REFERENCES roles(id),
    reason                VARCHAR(255) NOT NULL DEFAULT 'sla_breach',
    escalated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at           TIMESTAMPTZ
);
```

---

## 8. Plans & Blocks

### 8.1 `plans`

```sql
CREATE TABLE plans (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    section_id             UUID NOT NULL REFERENCES sections(id),
    status                 plan_status NOT NULL DEFAULT 'proposed',
    optimization_run_id     UUID REFERENCES optimization_runs(id),
    superseded_by_plan_id    UUID REFERENCES plans(id),
    approved_by_user_id      UUID REFERENCES users(id),
    approved_at              TIMESTAMPTZ,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

> Migration order note: `optimization_runs` (Section 10) must exist before `plans`, or
> add the FK via `ALTER TABLE` after both tables exist.

### 8.2 `blocks`

```sql
CREATE TABLE blocks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id         UUID NOT NULL REFERENCES plans(id) ON DELETE CASCADE,
    track_id        UUID NOT NULL REFERENCES tracks(id),
    corridor_group_id UUID REFERENCES corridor_groups(id),
    start_time      TIMESTAMPTZ NOT NULL,
    end_time        TIMESTAMPTZ NOT NULL,
    is_merged       BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT block_time_check CHECK (end_time > start_time)
);

CREATE INDEX idx_blocks_track_time ON blocks (track_id, start_time, end_time);
```

### 8.3 `plan_items`

```sql
CREATE TABLE plan_items (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id             UUID NOT NULL REFERENCES plans(id) ON DELETE CASCADE,
    block_id            UUID NOT NULL REFERENCES blocks(id) ON DELETE CASCADE,
    block_request_id     UUID NOT NULL REFERENCES block_requests(id),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT plan_item_unique UNIQUE (block_id, block_request_id)
);

CREATE INDEX idx_plan_items_plan ON plan_items (plan_id);
CREATE INDEX idx_plan_items_request ON plan_items (block_request_id);
```

### 8.4 `block_affected_tracks`

```sql
CREATE TABLE block_affected_tracks (
    block_id        UUID NOT NULL REFERENCES blocks(id) ON DELETE CASCADE,
    track_id        UUID NOT NULL REFERENCES tracks(id),
    impact_reason   VARCHAR(255),
    PRIMARY KEY (block_id, track_id)
);
```

### 8.5 `block_execution_reports`

Actual vs. planned execution outcome, recorded by field supervisors (architecture
Section 29.8). Feeds ML/duration-estimation improvements.

```sql
CREATE TABLE block_execution_reports (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    block_id                UUID NOT NULL REFERENCES blocks(id) ON DELETE CASCADE,
    reported_by_user_id      UUID NOT NULL REFERENCES users(id),
    actual_start             TIMESTAMPTZ,
    actual_end               TIMESTAMPTZ,
    work_completed           BOOLEAN NOT NULL DEFAULT FALSE,
    overrun_minutes          INTEGER,
    deviation_notes          TEXT,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_execution_reports_block ON block_execution_reports (block_id);
```

---

## 9. Constraints

```sql
CREATE TABLE constraints (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(150) NOT NULL,
    description     TEXT,
    severity        constraint_severity NOT NULL DEFAULT 'soft',
    penalty_weight  NUMERIC(10,4),          -- used only for soft constraints
    applies_to      VARCHAR(50),            -- e.g. TRACK, TRAIN, ASSET, GLOBAL
    definition      JSONB NOT NULL,         -- structured rule definition consumed by optimizer
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT constraint_penalty_check CHECK (
        (severity = 'hard' AND penalty_weight IS NULL) OR (severity = 'soft')
    )
);
```

---

## 10. Optimization

### 10.1 `optimization_runs`

```sql
CREATE TABLE optimization_runs (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    triggered_by_event_id    UUID,             -- FK added after `events` table exists
    status                   optimization_run_status NOT NULL DEFAULT 'pending',
    started_at               TIMESTAMPTZ,
    completed_at             TIMESTAMPTZ,
    input_summary            JSONB,   -- snapshot of requests/constraints considered
    error_message            TEXT,
    created_at               TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### 10.2 `optimization_results`

```sql
CREATE TABLE optimization_results (
    id                              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    optimization_run_id              UUID NOT NULL REFERENCES optimization_runs(id) ON DELETE CASCADE,
    plan_id                          UUID REFERENCES plans(id),
    total_block_duration_minutes     INTEGER,
    affected_trains_count             INTEGER,
    expected_delay_minutes            INTEGER,
    utilization_percent               NUMERIC(5,2),
    merged_requests_count             INTEGER,
    affected_tracks_count             INTEGER,
    objective_score                   NUMERIC(12,4),
    metrics                           JSONB,   -- full metrics payload for extensibility
    created_at                       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Optional (requires TimescaleDB):
-- SELECT create_hypertable('optimization_results', 'created_at');
```

### 10.3 `simulation_runs` / `simulation_results`

What-if simulations (architecture Section 29.4): the optimizer runs against a
hypothetical input without persisting a real `plans` row unless promoted.

```sql
CREATE TABLE simulation_runs (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    requested_by_user_id UUID NOT NULL REFERENCES users(id),
    section_id           UUID NOT NULL REFERENCES sections(id),
    status               simulation_status NOT NULL DEFAULT 'pending',
    input_snapshot       JSONB NOT NULL,  -- hypothetical requests/constraints
    promoted_plan_id      UUID REFERENCES plans(id), -- set if promoted to a real plan
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at         TIMESTAMPTZ
);

CREATE TABLE simulation_results (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    simulation_run_id    UUID NOT NULL REFERENCES simulation_runs(id) ON DELETE CASCADE,
    metrics              JSONB NOT NULL,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

Add the deferred FKs once both tables exist:

```sql
ALTER TABLE plans
    ADD CONSTRAINT fk_plans_optimization_run
    FOREIGN KEY (optimization_run_id) REFERENCES optimization_runs(id);

ALTER TABLE optimization_runs
    ADD CONSTRAINT fk_optimization_runs_event
    FOREIGN KEY (triggered_by_event_id) REFERENCES events(id);

ALTER TABLE corridor_groups
    ADD CONSTRAINT fk_corridor_groups_optimization_run
    FOREIGN KEY (created_by_optimization_run_id) REFERENCES optimization_runs(id);
```

---

## 11. Events

```sql
CREATE TABLE events (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type      VARCHAR(100) NOT NULL,   -- e.g. TRAIN_DELAY, TRACK_UNAVAILABLE
    event_version   INTEGER NOT NULL DEFAULT 1,
    source          event_source NOT NULL DEFAULT 'internal',
    entity_type     VARCHAR(50),             -- e.g. TRAIN, TRACK, ASSET, BLOCK_REQUEST
    entity_id       UUID,
    correlation_id  UUID,
    payload         JSONB NOT NULL,
    occurred_at     TIMESTAMPTZ NOT NULL,
    received_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_events_type_time ON events (event_type, occurred_at);
CREATE INDEX idx_events_entity ON events (entity_type, entity_id);
CREATE INDEX idx_events_correlation ON events (correlation_id);

-- Optional (requires TimescaleDB):
-- SELECT create_hypertable('events', 'occurred_at');
```

---

## 12. Notifications

```sql
CREATE TABLE notifications (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id        UUID REFERENCES events(id),
    title           VARCHAR(200) NOT NULL,
    body            TEXT,
    channel         notification_channel NOT NULL,
    status          notification_status NOT NULL DEFAULT 'pending',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    sent_at         TIMESTAMPTZ
);

CREATE TABLE notification_recipients (
    notification_id  UUID NOT NULL REFERENCES notifications(id) ON DELETE CASCADE,
    user_id          UUID NOT NULL REFERENCES users(id),
    read_at          TIMESTAMPTZ,
    PRIMARY KEY (notification_id, user_id)
);
```

---

## 13. Weather & Environmental Risk

```sql
CREATE TABLE weather_observations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    section_id      UUID NOT NULL REFERENCES sections(id),
    observed_at     TIMESTAMPTZ NOT NULL,
    condition       VARCHAR(50),   -- e.g. RAIN, FOG, STORM, CLEAR
    temperature_c   NUMERIC(5,2),
    wind_kmph       NUMERIC(5,2),
    raw_payload     JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE weather_risk_assessments (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    block_request_id     UUID NOT NULL REFERENCES block_requests(id) ON DELETE CASCADE,
    weather_observation_id UUID REFERENCES weather_observations(id),
    risk_level            weather_risk_level NOT NULL DEFAULT 'low',
    notes                  TEXT,
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Optional (requires TimescaleDB):
-- SELECT create_hypertable('weather_observations', 'observed_at');
```

---

## 14. Audit Trail

```sql
CREATE TABLE audit_logs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_user_id    UUID REFERENCES users(id),
    action           VARCHAR(100) NOT NULL,  -- e.g. CREATE, UPDATE, APPROVE, REJECT, CANCEL
    entity_type      VARCHAR(50) NOT NULL,
    entity_id        UUID NOT NULL,
    before_state      JSONB,
    after_state       JSONB,
    correlation_id    UUID,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_audit_logs_entity ON audit_logs (entity_type, entity_id);
CREATE INDEX idx_audit_logs_actor ON audit_logs (actor_user_id);

-- Optional (requires TimescaleDB):
-- SELECT create_hypertable('audit_logs', 'created_at');
```

---

## 15. Entity Relationship Overview

```text
zones ──< divisions ──< sections ──< stations
                             │
                             └──< tracks ──< track_dependencies >── tracks
                                     │
departments ──< users ──< user_roles >── roles
    │                          │
    └──< block_requests >── tracks                requested_by_user_id ──> users
              │
              ├─ technical_requests (1:1)
              ├─ operational_requests (1:1)
              ├─ block_request_affected_tracks >── tracks
              ├─ approval_steps >── roles/users ──< escalations
              ├─ weather_risk_assessments >── weather_observations
              └─ corridor_group_requests >── corridor_groups

block_requests ──< plan_items >── blocks ──< block_affected_tracks >── tracks
                         │             │            │
                         │             │            └── block_execution_reports
                         │             └── plans ── optimization_runs ── optimization_results
                         └── traceability: which requests formed which block

simulation_runs ── simulation_results
      └── promoted_plan_id ──> plans

events ──< notifications >── notification_recipients >── users
events ──> optimization_runs.triggered_by_event_id

audit_logs ── (generic, references any entity_type/entity_id)

tracks ──< restrictions
tracks ──< maintenance >── assets, departments
tracks ──< train_schedules >── trains

constraints (referenced by optimizer at runtime; not directly FK-linked to plans)
```

---

## 16. Notes on Traceability & Consistency

- `plan_items` preserves the mapping from merged `blocks` back to every originating
  `block_requests` row — satisfying the requirement that optimized plans stay traceable
  to source requests.
- `plans.status` (`proposed` vs `approved`/`active`) and `block_requests.status`
  distinguish proposed, approved, in-progress, and completed states end-to-end.
- `plans.superseded_by_plan_id` supports the real-time re-optimization loop: when
  conditions change, a new plan is created and the old one is marked `superseded`
  rather than deleted, preserving history.
- `approval_steps` + `escalations` implement the multi-role sign-off and SLA escalation
  workflow without hardcoding a fixed number of approval stages.
- `corridor_groups` / `corridor_group_requests` let multiple `block_requests` be bundled
  into one physical block while each request keeps its own row for reporting/traceability.
- `simulation_runs` are fully separate from `plans` until explicitly promoted, so
  what-if exploration never pollutes the authoritative planning history.
- `audit_logs` is intentionally generic (entity_type/entity_id + JSONB before/after) so
  new entities don't require new audit tables.
- The Read Store and Redis are intentionally **not** modeled here; they are downstream
  projections populated via CDC/ETL from this Operational DB.
