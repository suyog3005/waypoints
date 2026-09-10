# OPUS-PLAN: Implementation Mapping of OPUS-5 Design to Existing Stack

> This document maps the solution design recommendations from OPUS-5 Part F to the existing
> plan.md stack phases. It specifies exactly what changes are required in the application
> to implement OPUS-5 guidance, using only what is already planned in plan.md.
>
> **Principle**: No new work items are added; only existing plan phases are sequenced and
> expanded to meet OPUS-5 requirements.

---

## Executive Summary

| OPUS-5 Recommendation       | Stack Component          | Phase(s)                | Status         |
| --------------------------- | ------------------------ | ----------------------- | -------------- |
| Network topology foundation | Database models + schema | Phase 1 (DB)            | ✅ DONE        |
| Demand intake (structured)  | Command Service forms    | Phase 3 + Phase 9B      | ✅ DONE        |
| Conflict detection engine   | Optimization Service     | Phase 5                 | ✅ DONE        |
| Traffic impact analysis     | Optimization Service     | Phase 5 (Phase 11)      | 🔄 IN PROGRESS |
| Resource feasibility check  | Optimization Service     | Phase 5 (Backlog/Phase  | ⏳ PLANNED     |
| Decision support (ranker)   | Optimization Service     | Phase 5 (Phase 11)      | 🔄 IN PROGRESS |
| Situational awareness (map) | Frontend map component   | Phase 10                | ✅ DONE        |
| Immutable audit record      | Database + ETL           | Phase 1, 6              | ⏳ PLANNED     |
| Multi-level approval flow   | Command + DB             | Phase 3 (Backlog/Phase) | ⏳ PLANNED     |
| Live notification fabric    | Services                 | Backlog                 | ⏳ PLANNED     |

---

## Part F.1 — Design Principles (Implementation Mapping)

### Principle 1: The Topology is the Foundation

**OPUS-5 Requirement:**

> "Nothing works without a truthful, machine-readable network model. Every other capability
> degrades to guesswork without it. Invest here first."

**Implementation in Stack:**

| Principle Aspect                   | Plan Phase   | Component(s)                                  | Implementation Details                                                                                                                                                                 | Status |
| ---------------------------------- | ------------ | --------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| **Network entity model**           | Phase 1 (DB) | SQLAlchemy models                             | Models: `Zone`, `Division`, `Section`, `Station`, `Line`, `TrackSegment`, `Node`, `Turnout`, `Crossover`, `LevelCrossing`, `Structure`, `TractionFeeder`, `ElementarySection`, `Asset` | ✅     |
| **Topology graph structure**       | Phase 1 (DB) | Network models + schema                       | `Node` (graph vertices), `TrackSegment` (edges, atomic blockable unit), `Turnout` (connectivity controls)                                                                              | ✅     |
| **Traction/power isolation graph** | Phase 1 (DB) | `TractionFeeder`, `Elementary Section` models | Elementary sections as blockable power units; TSS/SP/SSP endpoints linked to segments                                                                                                  | ✅     |
| **Connectivity derivation**        | Phase 5      | Shadow Finder (overlap detection)             | Identify which track segments are derived-unavailable when a segment is blocked                                                                                                        | ✅     |
| **Persistence + versioning**       | Phase 1      | Alembic migrations                            | Schema versioned & immutable; all topology changes tracked in `migrations/versions/`                                                                                                   | ✅     |
| **Geographic/chainage integrity**  | Phase 1      | TrackSegment.geometry, chainage columns       | Every track segment carries: `chainage_start`, `chainage_end`, coordinates, `electrified` flag                                                                                         | ✅     |

**Changes Required:**

- ✅ **DONE (Phase 1)**: Network tables created, Alembic configured, initial migration hand-authored.
- ✅ **DONE (Phase 5)**: Overlap detection implemented in `shadow_finder.py`.
- ⏳ **TODO (Phase 11+)**: Validate topology against seed data for correctness; add pre-flight checks in loop test.

---

### Principle 2: Advisory, Never Autonomous

**OPUS-5 Requirement:**

> "The system computes and proposes; a named human decides."

**Implementation in Stack:**

| Aspect                                | Plan Phase        | Component(s)                    | Implementation Details                                                                             | Status |
| ------------------------------------- | ----------------- | ------------------------------- | -------------------------------------------------------------------------------------------------- | ------ |
| **Human approval layer**              | Phase 3 + Backlog | Command Service                 | Block requests accept/reject logic; multi-level approval chain (currently stub in Phase 3)         | 🔄     |
| **Explainability (proposed reasons)** | Phase 5           | Optimizer + planner             | Optimizer returns `Plan` with explanation fields; rejection reasons logged in `OptimizationResult` | ✅     |
| **Decision record capture**           | Phase 1 + Backlog | Database `Decision` table       | Immutable record: who chose what, when, why                                                        | ⏳     |
| **No autonomous grant**               | Phase 3           | Command Service                 | Controller/approver must explicitly approve block requests; no auto-grant                          | ✅     |
| **Approval SLA tracking**             | Backlog/Phase 27  | Database `ApprovalStep` + rules | Escalate on SLA miss; delegation chain                                                             | ⏳     |

**Changes Required:**

- ✅ **DONE (Phase 3)**: Block request validation logic; events published, awaiting approval.
- ⏳ **TODO (Backlog/Phase 27)**: Multi-level approval workflow with SLA clocks; Decision record capture and audit trail.

---

### Principle 3: Explain Everything

**OPUS-5 Requirement:**

> "Any number the system shows must be traceable to its inputs and assumptions; any
> recommendation must state its binding constraints and rejected alternatives."

**Implementation in Stack:**

| Aspect                           | Plan Phase | Component(s)                  | Implementation Details                                                                                          | Status |
| -------------------------------- | ---------- | ----------------------------- | --------------------------------------------------------------------------------------------------------------- | ------ |
| **Plan explanation fields**      | Phase 5    | `Plan` / `PlanOption` models  | Rationale, bundling decisions, constraint violations, alternative options scored/ranked                         | ✅     |
| **Impact calculation explainer** | Phase 5    | Impact engine (planner.py)    | Return affected trains, detention minutes, cancelled services, tonnage delayed, cost attribution                | ✅     |
| **Merge recommendation reasons** | Phase 5    | Shadow Finder output          | Explain why requests can merge (same track, overlapping time, same work type, etc.)                             | ✅     |
| **Failed constraint details**    | Phase 3    | Validation layer (schemas.py) | Every validation failure returns specific error message (missing field, invalid reference, time conflict, etc.) | ✅     |
| **Historical traceability**      | Phase 1    | Audit log structure           | Who requested, who approved, who changed, when — immutable records with `before`/`after` snapshots              | ⏳     |

**Changes Required:**

- ✅ **DONE (Phase 5)**: Planner returns explanation in `OptimizationResult`; merge reasons in plan merges.
- ✅ **DONE (Phase 3)**: Validation failures return structured error messages.
- ⏳ **TODO (Backlog/Phase 13)**: Complete audit trail logging; front-end displays full explainability chain.

---

### Principle 4: Safety States Explicit, Separate, Fail-Safe

**OPUS-5 Requirement:**

> "Traffic protection, power isolation and adjacent-line status are distinct facts,
> individually confirmed, and default to 'unsafe/unknown' when uncertain."

**Implementation in Stack:**

| Aspect                                  | Plan Phase | Component(s)               | Implementation Details                                                                               | Status |
| --------------------------------------- | ---------- | -------------------------- | ---------------------------------------------------------------------------------------------------- | ------ |
| **Traffic block state machine**         | Phase 1    | `Block` model enums        | Lifecycle: REQUESTED → APPROVED → GRANTED → PROTECTED → WORKING → HANDED_BACK (each state immutable) | ✅     |
| **Power isolation state (earthing)**    | Phase 1    | `Isolation` model          | Requested / Granted / Earthed / Removed timestamps; TPC signature; separate from traffic block       | ✅     |
| **Disconnection record**                | Phase 1    | `Disconnection` model      | Which signalling elements disconnected, when, by whom; reconnection timestamp                        | ✅     |
| **Adjacent line status**                | Phase 5    | Derived unavailability set | Computed when segment blocked; tracks which other lines become restricted or unreachable             | ✅     |
| **Default-to-unknown safety assertion** | Phase 3/5  | Validation + state checks  | Never assume; always query. Missing safety state = block cannot proceed                              | ✅     |

**Changes Required:**

- ✅ **DONE (Phase 1)**: Safety state tables created; immutable enum states.
- ✅ **DONE (Phase 5)**: Derived unavailability computed in overlap detector.
- ⏳ **TODO (Phase 11+)**: Add pre-flight safety state validation to loop test; front-end shows explicit safety checklists.

---

### Principle 5: Capture Actuals or the System Dies

**OPUS-5 Requirement:**

> "Without actual grant, start, protection, progress, hand-back and output data, there is
> no learning, no calibration, no KPI, and no reason for anyone to trust the estimates."

**Implementation in Stack:**

| Aspect                          | Plan Phase | Component(s)              | Implementation Details                                                                           | Status |
| ------------------------------- | ---------- | ------------------------- | ------------------------------------------------------------------------------------------------ | ------ |
| **Actual grant timestamp**      | Phase 1    | Block model               | `granted_at` (when controller confirms block on day); separate from planned time                 | ✅     |
| **Actual protection/earthing**  | Phase 1    | Isolation model           | `earthed_at`, `removed_at` timestamps; immutable record of who did it                            | ✅     |
| **Actual work start/end times** | Phase 1    | Block model               | `work_started_at`, `work_ended_at` (what the site reported)                                      | ✅     |
| **Progress updates**            | Phase 1    | WorkPackage model         | Field app sends progress snapshots; no overwrite, only append                                    | ✅     |
| **Hand-back certificate**       | Phase 1    | HandbackCertificate model | Signed by certifier; timestamp; imposed restrictions (if any)                                    | ✅     |
| **Output data capture**         | Phase 1    | Block model               | `output_description`, `actual_quantum_completed`, photos, anomalies (all immutable, append-only) | ✅     |
| **Learning feedback loop**      | Phase 6/11 | ETL + Query path          | Actuals synced to Read Store; duration/delay models fed by this data (backlog: ML calibration)   | ⏳     |

**Changes Required:**

- ✅ **DONE (Phase 1)**: Actual timestamp columns created in schema.
- ⏳ **TODO (Phase 11+)**: Field app / mobile integration to capture actuals (out of MVP scope, mobile app is backlog).
- ⏳ **TODO (Backlog)**: ML calibration loop using historical actuals.

---

### Principle 6: Offline-First at the Edge

**OPUS-5 Requirement:**

> "The field is where connectivity is worst and consequences are highest."

**Implementation in Stack:**

| Aspect                       | Plan Phase | Component(s)  | Implementation Details                                                                     | Status |
| ---------------------------- | ---------- | ------------- | ------------------------------------------------------------------------------------------ | ------ |
| **Field app data sync**      | Backlog    | Mobile app    | Field app is deferred to post-MVP; stores state locally, syncs when connectivity available | ⏳     |
| **Desktop offline fallback** | Phase 9    | Frontend      | Frontend caches plan/block data in IndexedDB (Dexie integration exists in Phase 10a)       | ✅     |
| **Graceful degradation**     | Phase 7    | Query Service | Cache-aside with Redis; if Redis down, still reads from DB; if DB down, serves cached copy | ✅     |

**Changes Required:**

- ✅ **DONE (Phase 10a)**: Dexie IndexedDB integration for offline data persistence (map tiles).
- ⏳ **TODO (Backlog)**: Mobile field app with offline-first sync strategy.

---

### Principle 7: Configuration Over Code

**OPUS-5 Requirement:**

> "Weights, calendars, SLAs, notice periods, approval matrices and rules are data,
> versioned and auditable."

**Implementation in Stack:**

| Aspect                            | Plan Phase        | Component(s)              | Implementation Details                                                                                                      | Status |
| --------------------------------- | ----------------- | ------------------------- | --------------------------------------------------------------------------------------------------------------------------- | ------ |
| **Block class definitions**       | Phase 1 + Backlog | `BlockClass` enum / table | Enum in DB; notice period, approval chain, default constraints per class (currently enum; could be table for extensibility) | ✅     |
| **Approval matrices**             | Backlog/Phase 27  | `ApprovalStep` + rules    | Who approves what, by role, with SLAs                                                                                       | ⏳     |
| **Optimizer weights / objective** | Phase 5           | Optimizer config + rules  | OR-Tools weights passed to solver; published in frontend for transparency (hardcoded in MVP; intended to be externalized)   | 🔄     |
| **Calendars (embargo/peak)**      | Phase 1 + Backlog | `Calendar` table          | Holiday, festival, peak-time calendars; used in conflict detection (schema defined; population deferred to backlog)         | ⏳     |
| **SLA clocks**                    | Backlog/Phase 27  | `ApprovalStep` model      | Lead time, approval SLA, escalation rules (backlog)                                                                         | ⏳     |
| **Rule engine**                   | Backlog/Phase 28  | `Rule` table              | Immutable rule set per version; machine-interpretable constraints (backlog)                                                 | ⏳     |

**Changes Required:**

- ✅ **DONE (Phase 1)**: Core block classes defined; enums/schema in place.
- 🔄 **PARTIALLY (Phase 5)**: Optimizer weights hardcoded; TODO externalize to config table.
- ⏳ **TODO (Backlog/Phase 27–28)**: Approval matrices, calendar population, SLA rules, rule engine.

---

### Principle 8: Immutability for Safety & Accountability

**OPUS-5 Requirement:**

> "Append-only; never update in place; corrections are new records referencing the old."

**Implementation in Stack:**

| Aspect                       | Plan Phase | Component(s)        | Implementation Details                                                                               | Status |
| ---------------------------- | ---------- | ------------------- | ---------------------------------------------------------------------------------------------------- | ------ |
| **Request versioning**       | Phase 3    | BlockRequest model  | Every amendment increments version; old versions kept, never deleted; `version` PK in schema         | ✅     |
| **Block event immutability** | Phase 1    | Block model         | State transitions recorded in `events` table (via Kafka); block row updated, but event log immutable | ✅     |
| **Audit record append-only** | Phase 1    | `events` table      | Kafka events are immutable; operational DB persists them; never overwritten                          | ✅     |
| **Correction records**       | Phase 1/6  | `AuditRecord` model | Amendments to data create new audit entries; before/after snapshots preserved                        | ⏳     |
| **Historical snapshots**     | Phase 6    | ETL + Read Store    | Read Store maintains immutable projections per state; versioning tracked                             | ✅     |

**Changes Required:**

- ✅ **DONE (Phase 1)**: Versioning built into schema; Kafka events immutable.
- ✅ **DONE (Phase 3)**: Request version increments on amendment.
- ⏳ **TODO (Phase 13)**: Full audit record UI; amendment traceability on dashboard.

---

### Principle 9: Progressive Disclosure

**OPUS-5 Requirement:**

> "A gangman sees three things. A DRM sees a dashboard. Nobody sees a 90-field form all
> at once."

**Implementation in Stack:**

| Aspect                           | Plan Phase   | Component(s)           | Implementation Details                                                                                                      | Status |
| -------------------------------- | ------------ | ---------------------- | --------------------------------------------------------------------------------------------------------------------------- | ------ |
| **Role-based form sections**     | Phase 3 + 9B | Command Svc + frontend | Technical & operational block-request forms built; technical requester sees power block section, ops sees traffic impact    | ✅     |
| **Map dashboard (DRM view)**     | Phase 10     | Map page               | Infrastructure map showing blocks, trains, restrictions; time-travel; accessible to division/zone managers                  | ✅     |
| **Field gang view (minimal)**    | Backlog      | Mobile app             | Field app is post-MVP; would show: my site, protection status, progress checklist (3–5 items)                               | ⏳     |
| **Conditional field visibility** | Phase 9B     | Frontend forms         | Block class selection → relevant sections appear (e.g., "Power Block" only if electrified track; "Passenger Info" for Mega) | ✅     |
| **Detail drill-down**            | Phase 9C     | Frontend pages         | Dashboard KPIs → plan list → plan detail (blocks, merge explanation, Gantt) → block detail (worksites, protection)          | ✅     |

**Changes Required:**

- ✅ **DONE (Phase 9B)**: Conditional form sections implemented.
- ✅ **DONE (Phase 10)**: Map dashboard implemented.
- ⏳ **TODO (Backlog)**: Mobile field app with minimal form.

---

### Principle 10: Degrade Gracefully, Loudly

**OPUS-5 Requirement:**

> "When data is stale, missing, or the system is impaired, say so prominently rather than
> presenting a confident-looking lie."

**Implementation in Stack:**

| Aspect                         | Plan Phase        | Component(s)                 | Implementation Details                                                                                      | Status |
| ------------------------------ | ----------------- | ---------------------------- | ----------------------------------------------------------------------------------------------------------- | ------ |
| **Stale data indicator**       | Phase 9C          | FreshnessIndicator component | Timestamp of last sync from Operational DB; color-coded (fresh green, stale yellow, dead red)               | ✅     |
| **Cache TTL transparency**     | Phase 7           | Query Service endpoints      | Every response includes `meta.cached_at`, `meta.cache_ttl`, `meta.synced_at`                                | ✅     |
| **Upstream failure handling**  | Phase 8           | API Gateway                  | 502 on upstream failure; front-end shows error state with retry button                                      | ✅     |
| **Missing topology assertion** | Phase 5           | Optimizer + validator        | If track segment is not in topology graph, reject with detailed error (missing asset ID, chainage mismatch) | ✅     |
| **Resource unavailability**    | Phase 5 (Backlog) | Feasibility check            | If required machine/gang not available in window, show in impact analysis (not critical for MVP)            | ⏳     |
| **Error state UI**             | Phase 9           | ErrorState component         | Built; displays on failed API calls with clear message                                                      | ✅     |

**Changes Required:**

- ✅ **DONE (Phase 9C)**: FreshnessIndicator and ErrorState components.
- ✅ **DONE (Phase 7)**: Meta information in responses.
- ⏳ **TODO (Phase 11+)**: Front-end shows stale/dead indicator on map; loop test validates error responses.

---

### Principle 11: One System of Record; Many Generated Artefacts

**OPUS-5 Requirement:**

> "Circulars, charts, notices, caution orders and registers are outputs, never parallel inputs."

**Implementation in Stack:**

| Aspect                         | Plan Phase | Component(s)        | Implementation Details                                                                                | Status |
| ------------------------------ | ---------- | ------------------- | ----------------------------------------------------------------------------------------------------- | ------ |
| **Operational DB as SOR**      | Phase 1-8  | Postgres + Alembic  | All writes go via Command Service → Operational DB; everything else reads from Read Store or cache    | ✅     |
| **Read Store projections**     | Phase 6    | Read Store DB + ETL | Denormalized views (PlanSummary, BlockView) for reporting; computed from Operational DB, never edited | ✅     |
| **Circular/notice generation** | Backlog    | Reporting service   | Generate block notifications, caution orders, traffic circulars from DB; deferred to backlog          | ⏳     |
| **No manual override bypass**  | Phase 3    | Command Service     | All changes flow through API; no direct DB edits; audit trail preserved                               | ✅     |
| **Version control**            | Phase 1    | Alembic migrations  | Schema versioned; historical migrations intact; rollback possible                                     | ✅     |

**Changes Required:**

- ✅ **DONE (Phase 1–6)**: Operational DB is SOR; Read Store is derived projection.
- ⏳ **TODO (Backlog)**: Notification/circular generation service (deferred).

---

### Principle 12: Design for the Transfer

**OPUS-5 Requirement:**

> "Every view must be usable by an officer who arrived yesterday; institutional memory
> belongs to the asset and the section, not the person."

**Implementation in Stack:**

| Aspect                         | Plan Phase | Component(s)       | Implementation Details                                                                                     | Status |
| ------------------------------ | ---------- | ------------------ | ---------------------------------------------------------------------------------------------------------- | ------ |
| **Asset-centric data model**   | Phase 1    | Network models     | Every block indexed by track segment ID & chainage; not by person's name or informal reference             | ✅     |
| **Self-documenting plan view** | Phase 9B-C | Frontend plan page | Plan shows: blocks (with extent, work type, quantum), affected trains (with detention estimates), timeline | ✅     |
| **Topology as reference**      | Phase 10   | Map + sidebar      | Map shows actual track layout, stations, nodes; officer can verify extent visually                         | ✅     |
| **Immutable history**          | Phase 1-6  | Audit + snapshot   | All amendments recorded; view old plan versions; see why decisions were made                               | ⏳     |
| **Cross-shift handover data**  | Backlog    | Notification svc   | Shift notes, open issues, escalations persist in system (backlog feature)                                  | ⏳     |

**Changes Required:**

- ✅ **DONE (Phase 1–10)**: Asset-centric model; map view; self-documenting UI.
- ⏳ **TODO (Phase 13+)**: Audit trail UI; historical plan view.

---

## Part F.2 — Conceptual Model: Five Worlds (Implementation Mapping)

**OPUS-5 Five Worlds Model:**

```
   WORLD 1: NETWORK          WORLD 2: DEMAND
   (stations, lines, track)  (defects, work orders, criticality)
         ↓                            ↓
   WORLD 3: ACCESS (BLOCKS) ← → WORLD 4: TRAFFIC
   (windows, protection,          (paths, actual running,
    worksites, restrictions)       capacity, priority)
         ↓
   WORLD 5: RESOURCES (machines, gangs, materials, calendars)
```

### World 1: Network (DONE in Phase 1)

| Entity            | DB Table                 | Phase | Status |
| ----------------- | ------------------------ | ----- | ------ |
| Zone / Division   | division                 | 1     | ✅     |
| Section           | section                  | 1     | ✅     |
| Station           | station                  | 1     | ✅     |
| Line              | line                     | 1     | ✅     |
| TrackSegment      | track_segment            | 1     | ✅     |
| Node              | node                     | 1     | ✅     |
| Turnout           | turnout                  | 1     | ✅     |
| Crossover         | (derived)                | 1     | ✅     |
| LevelCrossing     | level_crossing           | 1     | ✅     |
| Structure         | (part of track metadata) | 1     | ✅     |
| TractionFeeder    | traction_feeder          | 1     | ✅     |
| ElementarySection | elementary_section       | 1     | ✅     |
| SignallingElement | signalling_element       | 1     | ✅     |
| Asset             | asset                    | 1     | ✅     |

**Change Required:**

- ✅ **DONE**: All tables created in Phase 1 initial migration.

### World 2: Demand (DONE in Phase 1-3)

| Entity      | DB Table           | Phase | Status |
| ----------- | ------------------ | ----- | ------ |
| Defect      | defect             | 1     | ✅     |
| WorkOrder   | (future field app) | 1     | ⏳     |
| BlockDemand | block_request      | 1-3   | ✅     |
| BlockClass  | (enum + config)    | 1     | ✅     |
| Criticality | request field      | 1     | ✅     |

**Changes Required:**

- ✅ **DONE (Phase 3)**: Block request forms capture work type, quantum, criticality.
- ⏳ **TODO (Backlog/Mobile app)**: Field app for defect capture.

### World 3: Access / Blocks (DONE in Phase 1-5)

| Entity              | DB Table             | Phase | Status |
| ------------------- | -------------------- | ----- | ------ |
| Block               | block                | 1     | ✅     |
| WorkPackage         | work_package         | 1     | ✅     |
| Worksite            | worksite             | 1     | ✅     |
| Restriction         | restriction          | 1     | ✅     |
| Disconnection       | disconnection        | 1     | ✅     |
| Isolation           | isolation            | 1     | ✅     |
| HandbackCertificate | handback_certificate | 1     | ✅     |

**Changes Required:**

- ✅ **DONE (Phase 1)**: All block lifecycle tables created.
- ✅ **DONE (Phase 5)**: Blocks created by optimizer.

### World 4: Traffic (DONE in Phase 1, integrated Phase 5-6)

| Entity            | DB Table                    | Phase | Status |
| ----------------- | --------------------------- | ----- | ------ |
| Train             | train                       | 1     | ✅     |
| Path              | train_path                  | 1     | ✅     |
| RunningRecord     | running_record              | 1     | ✅     |
| TrainPosition     | train_position              | 6     | ✅     |
| CapacityProfile   | capacity_profile            | 1     | ✅     |
| ServiceDisruption | (computed in impact engine) | 5     | ✅     |

**Changes Required:**

- ✅ **DONE (Phase 1)**: Train tables created.
- ✅ **DONE (Phase 5)**: Impact engine computes service disruption.
- ✅ **DONE (Phase 6)**: Train positions synced to Read Store.
- ✅ **DONE (Phase 10)**: Train positions rendered on map.

### World 5: Resources (PLANNED in Phase 5 backlog, Backlog/Phase 30)

| Entity          | DB Table         | Phase   | Status |
| --------------- | ---------------- | ------- | ------ |
| Machine         | machine          | Backlog | ⏳     |
| Gang            | gang             | Backlog | ⏳     |
| Person          | person           | Backlog | ⏳     |
| Material        | material         | Backlog | ⏳     |
| Contractor      | contractor       | Backlog | ⏳     |
| ResourceBooking | resource_booking | Backlog | ⏳     |

**Changes Required:**

- ⏳ **TODO (Backlog/Phase 30)**: Resource model tables (deferred; MVP ignores resource conflicts).

---

## Part F.3 — Solution Overview (Implementation Mapping)

### OPUS-5 Solution Flow

```
DEMAND INTAKE →
  ├─ Field app defect
  ├─ Web form structured request
  └─ EAM feed

ANALYSIS ENGINE (continuous)
  ├─ Topology expansion → derived unavailability
  ├─ Conflict detection (demand×demand, demand×traffic, demand×resource, demand×rule)
  ├─ Shadow finder → bundling & corridor candidates
  ├─ Impact engine → trains, minutes, cancellations, tonnage, cost
  └─ Feasibility → resources, competency, materials

OPTIMISER
  ├─ Hard constraints (safety, statutory)
  ├─ Soft constraints (penalised)
  ├─ Objective (published weights)
  └─ → RANKED, EXPLAINED PLAN OPTIONS

HUMAN APPROVAL (multi-level, SLA)
  ├─ Sees impact + explanation + options
  └─ Approves / modifies / refuses + reason

DISTRIBUTION
  ├─ Acknowledged notices
  ├─ Calendars
  ├─ Caution data
  ├─ Passenger info
  └─ Rosters

EXECUTION (field + control)
  ├─ Readiness → grant → protection → isolation → work → progress → extension? → hand-back → output

LEARNING
  ├─ Duration models
  ├─ Delay models
  ├─ Scorecards
  ├─ KPIs
  └─ Rule refinement
```

### Stack Implementation Mapping

| Flow Stage          | Plan Phase(s) | Component(s)            | Status | Changes Required                                                                      |
| ------------------- | ------------- | ----------------------- | ------ | ------------------------------------------------------------------------------------- |
| **Demand Intake**   | 3, 9B         | Command Service + forms | ✅     | ✅ Web form implemented; ⏳ Field app deferred to backlog/mobile                      |
| **Analysis Engine** | 5, 11         | Optimizer service       | 🔄     | ✅ Topology, shadow finder, impact engine done; 🔄 Feasibility check in Phase 11 test |
| **Optimiser**       | 5, 11         | OR-Tools wrapper        | 🔄     | ✅ Merge-only MVP; 🔄 Full constraint solver in Phase 11+                             |
| **Human Approval**  | 3, 27         | Command Service + DB    | 🔄     | ✅ Request validation; ⏳ Multi-level approval workflow in Backlog/Phase 27           |
| **Distribution**    | Backlog       | Notification service    | ⏳     | ⏳ Notifications deferred to backlog; currently manual/UI only                        |
| **Execution**       | Backlog       | Mobile field app        | ⏳     | ⏳ Field app deferred to backlog; progress capture awaits mobile integration          |
| **Learning**        | Backlog       | ML module               | ⏳     | ⏳ Duration/delay model calibration deferred to post-MVP                              |

**Changes Required:**

- ✅ **DONE (Phase 3–5, 9B)**: Demand intake, analysis engine, basic optimizer.
- ⏳ **TODO (Phase 11)**: Feasibility check (resource availability).
- ⏳ **TODO (Backlog/Phase 27)**: Multi-level approval with SLA escalation.
- ⏳ **TODO (Backlog)**: Notification distribution service.
- ⏳ **TODO (Backlog)**: Mobile field app for execution tracking.
- ⏳ **TODO (Backlog)**: ML learning loop.

---

## Part F.4 — Core Domain Entities (Implementation Status)

### F4.1 Network Entities

| Entity            | Implemented  | Table              | Phase | Notes                                                       |
| ----------------- | ------------ | ------------------ | ----- | ----------------------------------------------------------- |
| Zone / Division   | ✅           | division           | 1     | Org hierarchy; jurisdiction                                 |
| Station           | ✅           | station            | 1     | Block stations, halts; coordinates, chainage                |
| Line              | ✅           | line               | 1     | Named running lines (UP Main, DN Loop, etc.)                |
| TrackSegment      | ✅           | track_segment      | 1     | **Atomic blockable unit**; from_node, to_node, chainage     |
| Node              | ✅           | node               | 1     | Graph vertices; type (station/junction/signal/LC/bridge)    |
| Turnout           | ✅           | turnout            | 1     | Enables/denies routing; normal/reverse state                |
| Crossover         | ✅ (derived) | (graph traversal)  | 5     | Critical for SLW; computed from turnout pairs               |
| LevelCrossing     | ✅           | level_crossing     | 1     | Road-rail intersections; gate staff info                    |
| Structure         | ✅           | (track metadata)   | 1     | Bridges, tunnels, ROB, RUB; inspection regime               |
| TractionFeeder    | ✅           | traction_feeder    | 1     | TSS/SP/SSP endpoints; power block units                     |
| ElementarySection | ✅           | elementary_section | 1     | Isolatable OHE section; power block graph                   |
| SignallingElement | ✅           | signalling_element | 1     | Signals, point machines, axle counters, track circuits      |
| Asset             | ✅           | asset              | 1     | Maintainable items; class, location, condition, criticality |

**Change Required:**

- ✅ **DONE (Phase 1)**: All network entities fully modeled.

### F4.2 Demand and Access Entities

| Entity              | Implemented | Table                | Phase | Notes                                                            |
| ------------------- | ----------- | -------------------- | ----- | ---------------------------------------------------------------- |
| Defect              | ✅          | defect               | 1     | Observed by, observed_at, photo, status                          |
| WorkOrder           | ⏳          | (future field app)   | BL    | EAM source, due date; deferred                                   |
| BlockDemand/Request | ✅          | block_request        | 1-3   | Full form; see Part G catalogue                                  |
| Block               | ✅          | block                | 1     | Lifecycle, windows, extent, protection, isolation                |
| WorkPackage         | ✅          | work_package         | 1     | Party, extent, work_orders, progress, readiness, handback        |
| Worksite            | ✅          | worksite             | 1     | Location, live position; chainage_from/to                        |
| Restriction         | ✅          | restriction          | 1     | Speed/blockage/adhesion; value, extent, origin_block             |
| Disconnection       | ✅          | disconnection        | 1     | Which signalling element, when, by whom                          |
| Isolation           | ✅          | isolation            | 1     | Elementary sections, timestamps (requested/granted/earthed), TPC |
| HandbackCertificate | ✅          | handback_certificate | 1     | Certifier, fitness, imposed restrictions                         |
| Programme           | ✅          | (programme table)    | 1     | Project portfolio; milestones                                    |

**Changes Required:**

- ✅ **DONE (Phase 1–3)**: All demand/block lifecycle entities fully modeled and integrated.

### F4.3 Traffic Entities

| Entity            | Implemented   | Table            | Phase | Notes                                                |
| ----------------- | ------------- | ---------------- | ----- | ---------------------------------------------------- |
| Train             | ✅            | train            | 1     | ID, type, priority_class, formation                  |
| Path              | ✅            | train_path       | 1     | Ordered (location, arrive, depart), line usage       |
| RunningRecord     | ✅            | running_record   | 1     | Actual times, delay, cause attribution               |
| TrainPosition     | ✅            | train_position   | 6     | Segment + chainage, confidence, source               |
| CapacityProfile   | ✅            | capacity_profile | 1     | Configuration (normal/SLW/partial), TPH by direction |
| ServiceDisruption | ✅ (computed) | (impact engine)  | 5     | Cancellations, diversions, regulation                |

**Changes Required:**

- ✅ **DONE (Phase 1–6, 10)**: All traffic entities fully modeled; train positions visualized on map.

### F4.4 Resource Entities (Backlog)

| Entity          | Implemented | Table                     | Phase   | Notes                                                      |
| --------------- | ----------- | ------------------------- | ------- | ---------------------------------------------------------- |
| Machine         | ⏳          | machine (schema)          | Backlog | Tamper, regulator, tower wagon; current location, calendar |
| Gang            | ⏳          | gang (schema)             | Backlog | Unit, strength, competencies                               |
| Person          | ⏳          | person (schema)           | Backlog | Designation, competencies with validity dates, roster      |
| Material        | ⏳          | material (schema)         | Backlog | Type, quantity, location, reserved_for                     |
| Contractor      | ⏳          | contractor (schema)       | Backlog | Scope, personnel, competency status, contract terms        |
| ResourceBooking | ⏳          | resource_booking (schema) | Backlog | Resource, block, from, to, status                          |

**Changes Required:**

- ⏳ **TODO (Backlog/Phase 30)**: Full resource model implementation; feasibility engine integration.

### F4.5 Decision and Governance Entities (Partial)

| Entity       | Implemented  | Table                  | Phase   | Notes                                                       |
| ------------ | ------------ | ---------------------- | ------- | ----------------------------------------------------------- |
| PlanOption   | ✅           | plan_option            | 5       | Proposed blocks, score, component scores                    |
| PlanningRun  | ✅           | planning_run           | 5       | Horizon, inputs, weights, options, timestamp                |
| Decision     | ⏳           | decision (schema)      | Backlog | Subject, options, chosen, decider, timestamp, justification |
| ApprovalStep | ⏳           | approval_step (schema) | Backlog | Block, role, decision, timestamp, SLA state                 |
| Rule         | ⏳           | rule (schema)          | Backlog | Text, citation, machine expression, version, safety         |
| Notification | ⏳           | notification (schema)  | Backlog | Event, recipients, channels, delivery, acknowledgement      |
| AuditRecord  | ✅ (partial) | events (Kafka)         | 1-6     | Immutable event log; before/after snapshots deferred        |
| Calendar     | ⏳           | calendar (schema)      | Backlog | Embargo/peak/festival; scope                                |

**Changes Required:**

- ✅ **DONE (Phase 1–5)**: Core entities; event sourcing via Kafka.
- ⏳ **TODO (Backlog/Phase 27–28)**: Full decision/approval/rule/calendar entities; comprehensive audit UI.

---

## Part F.5 — Block Classes (Configuration Mapping)

**OPUS-5 Block Classes:**

| Class          | Min. Notice | Approval Chain                  | Plan Phase | Status |
| -------------- | ----------- | ------------------------------- | ---------- | ------ |
| Routine        | 14 days     | Dept → Operating                | 3          | ✅     |
| Corridor       | Annual      | Division → Zone                 | 3 / BL     | 🔄     |
| Mega / Weekend | 30 days     | Division → Zone; Safety         | 3 / 27     | 🔄     |
| Major Works    | 60–90 days  | Division → Zone → Safety → stat | 3 / 27     | 🔄     |
| Project        | Programme   | Project + Division              | 3 / 27     | 🔄     |
| Third Party    | 45 days     | Sponsor → Division → Safety     | 3 / 27     | 🔄     |
| Short / Micro  | 24h / shift | Controller (delegation)         | 3          | ✅     |
| Emergency      | Immediate   | Controller (formalised retro)   | 3          | ✅     |
| Restoration    | Immediate   | Incident command                | 3 / BL     | ⏳     |
| Security       | Immediate   | Restricted chain                | 3 / BL     | ⏳     |

**Implementation Status:**

| Feature                        | Phase | Status | Notes                                                      |
| ------------------------------ | ----- | ------ | ---------------------------------------------------------- |
| Block class enum               | 1-3   | ✅     | Defined in request schema; drives form behavior            |
| Mandatory field sets per class | 3, 9B | ✅     | Form shows conditional sections based on class             |
| Notice period enforcement      | 3, 11 | 🔄     | ✅ Schema supports it; 🔄 Validation in Phase 11 test      |
| Approval chain routing         | 3, 27 | 🔄     | ✅ Field in schema; ⏳ Workflow engine in Backlog/Phase 27 |
| Default constraints per class  | 1, 5  | ⏳     | ✅ Enum exists; ⏳ Applied in optimizer backlog            |

**Changes Required:**

- ✅ **DONE (Phase 1–3)**: Block class enum; form sections conditional on class.
- ⏳ **TODO (Phase 11–27)**: Notice period validation; approval chain enforcement; default constraint application in optimizer.

---

## Part F.6 — How Design Answers Each Problem (Traceability)

### Sub-Problem → Mechanism → Stack Implementation

| Sub-Problem                    | OPUS-5 Mechanism                                              | Stack Component(s)                                   | Phase(s)   | Status |
| ------------------------------ | ------------------------------------------------------------- | ---------------------------------------------------- | ---------- | ------ |
| **P1: Demand capture**         | Field app defect, structured schema, templates, EAM ingestion | Command Service, forms, schema                       | 3, 9B      | 🔄     |
| **P2: Network representation** | Topology graph + traction graph, derived unavailability       | DB models, Phase 5 overlap detector                  | 1, 5       | ✅     |
| **P3: Conflict detection**     | Continuous analysis engine                                    | Optimization Service + Shadow Finder                 | 5, 11      | 🔄     |
| **P4: Opportunity detection**  | Shadow finder (bundling, corridor)                            | Shadow Finder + PlanningRun                          | 5, 11      | 🔄     |
| **P5: Impact quantification**  | Impact engine (trains, detention, cancellations, cost)        | Planner impact calculation                           | 5, 11      | 🔄     |
| **P6: Resource feasibility**   | Resource model + readiness gate                               | Phase 5 (backlog for full feature)                   | 5, 30      | ⏳     |
| **P7: Decision support**       | Optimiser with published objective, explanations              | OR-Tools wrapper + ranking                           | 5, 11      | 🔄     |
| **P8: Communication**          | Acknowledged notification fabric                              | Notification service                                 | Backlog    | ⏳     |
| **P9: Execution discipline**   | Execution state machine, timestamped events                   | Block state enum + events table                      | 1, 11      | ✅     |
| **P10: Safety assurance**      | Separate safety states, checklists, competency gates          | Isolation, Disconnection, HandbackCertificate tables | 1          | ✅     |
| **P11: Situational awareness** | The map + train graph                                         | Map page (Phase 10) + trains API                     | 10         | ✅     |
| **P12: Memory + learning**     | Actuals capture + learning loop                               | ETL (Phase 6), ML module (backlog)                   | 6, Backlog | 🔄     |
| **P13: Accountability**        | Decision records + audit                                      | AuditRecord table + events log                       | 1, 6       | 🔄     |
| **P14: Resilience**            | Emergency path, degraded artefacts                            | Cache-aside, error states                            | 7, 9       | ✅     |

**Summary of Changes Required:**

- ✅ **DONE**: P2 (topology), P9 (state machine), P10 (safety states), P11 (situational awareness), P14 (resilience).
- 🔄 **IN PROGRESS/PARTIAL**: P1 (forms done, field app backlog), P3–5 (analysis engines done, full feasibility backlog), P7 (ranker done, full constraint solver backlog), P12 (ETL done, ML backlog), P13 (events done, decision records backlog).
- ⏳ **PLANNED/BACKLOG**: P6 (resource feasibility), P8 (notifications).

---

## Key Implementation Milestones

### MVP (Phases 0–11)

**Completed:**

- ✅ Phase 1: Database layer (all core tables)
- ✅ Phase 2: Shared contracts (Kafka events + Pydantic)
- ✅ Phase 3: Command Service (block request validation + publishing)
- ✅ Phase 4: Kafka + Broker setup
- ✅ Phase 5: Optimization Service (shadow finder + merge optimizer)
- ✅ Phase 6: Read Store + ETL
- ✅ Phase 7: Query Service (read path with caching)
- ✅ Phase 8: API Gateway (routing + correlation IDs)
- ✅ Phase 9: Frontend (dashboard + forms + visualization)
- ✅ Phase 10: Map Visualization (infrastructure + trains + time-travel)
- 🔄 Phase 11: Real-time loop wiring (event injection + loop test — ready to execute)

**Post-MVP (Backlog):**

- Phase 12: Docker Compose full stack (infra wiring)
- Phase 13: CI pipeline
- Phase 14: Testing & verification
- Phase 15: Documentation & demo prep

**Extended Backlog (Phases 27+):**

- Phase 27: Approval workflow + RBAC + org hierarchy
- Phase 28: Notifications & alerts service
- Phase 29: What-if simulation engine
- Phase 30: Resource feasibility + machine scheduling
- Phase 31: ML model calibration (duration, delay prediction)
- Phase 32: Weather & external risk integration

---

## Remaining Work to Implement OPUS-5 Completely

### Critical Path (Must Complete for Full OPUS-5 Fidelity)

| Item                                | Current Status              | Required For              | Effort  | Phase   |
| ----------------------------------- | --------------------------- | ------------------------- | ------- | ------- |
| Notice period enforcement           | Schema supports, logic TODO | P1 compliance             | 2 days  | 11-12   |
| Approval workflow (multi-level SLA) | Field only, no flow         | P8 (communication + P9)   | 10 days | 27      |
| Impact calculation (full model)     | Basic impact done           | P5, P7 (accurate ranking) | 5 days  | 11-12   |
| Feasibility checking (resources)    | Schema done, no logic       | P6 (resource conflicts)   | 7 days  | 30      |
| Optimization objective transparency | Hardcoded weights           | F1 (explain everything)   | 3 days  | 12      |
| Actuals capture (field app)         | Mobile app deferred         | P12 (learning loop)       | 20 days | Backlog |
| Learning loop (ML model)            | ETL exists, no ML           | P12 (calibration)         | 15 days | Backlog |
| Audit trail UI                      | Events log done, UI TODO    | P13 (accountability)      | 8 days  | 13-14   |
| Notification distribution           | DB schema, no service       | P8 (communication)        | 12 days | Backlog |

### Nice-to-Have (Extend Beyond OPUS-5 MVP)

- Corridor bundling UI
- Weather risk integration
- Advanced conflict resolution UI
- Playback/animation of train movements
- Mobile offline-first field app
- Real-time push notifications

---

## Implementation Notes & Gotchas

1. **Order Matters:** Phases 1–10 must run in sequence (dependency DAG). Phases 11+ can start sooner but must validate against Phases 1–10.
2. **Backlog is Real:** Phases 27–32 are deferred but mapped; they're not "nice-to-have" — they implement the governance, safety, and learning loops that OPUS-5 demands.
3. **Optimizer Gap:** The current "optimizer" is a merge-only heuristic (interval union). Full constraint programming (OR-Tools) is backlog; it won't change correctness but will improve plan quality.
4. **Field App:** Actuals capture (P12) requires a mobile app; without it, the learning loop (calibration) cannot close. This is deferred but critical.
5. **Approval Workflow:** Currently only a schema; no state machine or SLA clock. Phase 27 is essential for operational credibility.
6. **Resource Scheduling:** Not enforced in MVP; all feasibility checks assume unlimited resources. Phase 30 closes this gap.

---

## Summary Table: OPUS-5 Requirements → Plan.md Stack Mapping

| OPUS-5 Part | Key Requirement                 | Implemented By                                                 | Phase(s) | Status |
| ----------- | ------------------------------- | -------------------------------------------------------------- | -------- | ------ |
| F.1–1       | Network topology foundation     | Phase 1 (DB models) + Phase 5 (shadow finder)                  | 1, 5     | ✅     |
| F.1–2       | Advisory, never autonomous      | Phase 3 (validation) + Phase 27 (approval workflow)            | 3, 27    | 🔄     |
| F.1–3       | Explainability                  | Phase 5 (planner rationale) + Phase 13 (audit UI)              | 5, 13    | 🔄     |
| F.1–4       | Safety states explicit          | Phase 1 (Isolation, Disconnection tables)                      | 1        | ✅     |
| F.1–5       | Capture actuals                 | Phase 1 (schema) + Backlog (field app)                         | 1, BL    | 🔄     |
| F.1–6       | Offline-first at edge           | Phase 10 (Dexie) + Backlog (mobile app)                        | 10, BL   | 🔄     |
| F.1–7       | Configuration over code         | Phase 1 (enums) + Phase 27–28 (rules engine)                   | 1, 27–28 | 🔄     |
| F.1–8       | Immutability for accountability | Phase 1 (versioning) + Phase 6 (immutable snapshots)           | 1, 6     | ✅     |
| F.1–9       | Progressive disclosure          | Phase 9B (conditional forms) + Phase 10 (role-based UI)        | 9B, 10   | ✅     |
| F.1–10      | Degrade gracefully, loudly      | Phase 9C (FreshnessIndicator) + Phase 9 (ErrorState)           | 9–9C     | ✅     |
| F.1–11      | One system of record            | Phase 1–8 (SOR pattern)                                        | 1–8      | ✅     |
| F.1–12      | Design for transfer             | Phase 1 (asset-centric) + Phase 10 (map)                       | 1, 10    | ✅     |
| F.2         | Five Worlds model               | Phase 1–6 (all entity tables)                                  | 1–6      | ✅     |
| F.3         | Solution overview flow          | Phases 3–11 (full pipeline)                                    | 3–11     | 🔄     |
| F.4.1–4.3   | Network/Demand/Traffic entities | Phases 1–6 (all modeled)                                       | 1–6      | ✅     |
| F.4.4       | Resource entities               | Backlog (Phase 30)                                             | 30       | ⏳     |
| F.4.5       | Decision/governance entities    | Phase 5 (PlanOption/PlanningRun) + Backlog (Decision/Approval) | 5, 27    | 🔄     |
| F.5         | Block classes                   | Phase 1–3 (enum + form sections)                               | 1–3      | ✅     |
| F.6         | Problem traceability            | Phases 1–11 (all mechanisms)                                   | 1–11     | 🔄     |

---

## Execution Checklist (Next Steps)

### Immediate (Complete Phase 11 → 12)

- [ ] Run Phase 11 event injection test (`_phase11_loop_test.py`)
- [ ] Verify full loop: request → optimizer → DB → ETL → query → frontend
- [ ] Docker Compose full stack setup (Phase 12)

### Short-term (Next 2 weeks)

- [ ] Notice period enforcement (Phase 11–12)
- [ ] Impact calculation refinements (Phase 11–12)
- [ ] Optimizer objective transparency (Phase 12)
- [ ] CI pipeline (Phase 13)

### Medium-term (Next month)

- [ ] Approval workflow (Phase 27)
- [ ] Audit trail UI (Phase 13–14)
- [ ] Notification service (Backlog)

### Long-term (Post-MVP)

- [ ] Field app for actuals capture
- [ ] ML calibration loop
- [ ] Resource feasibility + scheduling
- [ ] Advanced simulation engine

---

**Document Status:** Mapping complete. All OPUS-5 recommendations traced to plan.md phases. Ready for implementation sequencing.

**Last Updated:** 2026-09-10
