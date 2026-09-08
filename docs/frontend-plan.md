# Frontend Plan — AI-Powered Automatic Block Planning System

> This document is the brainstorm + design reference for the frontend (architecture
> Section 3). It exists so any agent/developer picking up Phase 9 has a single place to
> check for UI/UX decisions, component inventory, and task breakdown — the same role
> [plan.md](./plan.md) plays for the backend. Update this file whenever a frontend
> decision changes; log the change in [agent.md](./agent.md) per the mandatory rule.
>
> Scope: architecture Sections 1–26 (core MVP) only. Sections 27–32 (RBAC login UI,
> approval workflows, corridor bundling, notifications, weather, simulation, audit) are
> backlog — see Section 12 below for how the UI should leave room for them without
> building them now.

---

## 1. Stack Decisions

| Concern                                 | Choice                                                                                       | Why                                                                                                                                                                                                                                                                                                                                                |
| --------------------------------------- | -------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Framework                               | **Next.js 14, App Router**                                                                   | Already scaffolded; server components reduce client bundle for a data-heavy dashboard.                                                                                                                                                                                                                                                             |
| Language                                | **TypeScript**                                                                               | Already scaffolded; catches API contract drift early.                                                                                                                                                                                                                                                                                              |
| Styling                                 | **Tailwind CSS**                                                                             | Utility-first, fast to iterate, pairs with shadcn/ui out of the box.                                                                                                                                                                                                                                                                               |
| Component primitives                    | **shadcn/ui** (Radix UI + Tailwind, copy-in components)                                      | Accessible by default, unstyled-until-themed, no runtime CSS-in-JS cost, we own the code (no black-box dependency).                                                                                                                                                                                                                                |
| Icons                                   | **lucide-react**                                                                             | Ships with shadcn/ui conventions, tree-shakeable.                                                                                                                                                                                                                                                                                                  |
| Data fetching / caching                 | **TanStack Query (React Query)**                                                             | Gives us client-side cache-aside on top of the gateway's own Redis cache-aside (Section 6) — request de-dup, background refetch, retry, and polling with minimal code. This is the client-side mirror of the backend's read path.                                                                                                                  |
| Forms                                   | **react-hook-form + zod**                                                                    | Matches the backend's Pydantic validation style (schema-first); zod schemas can mirror `contracts.events.schemas` field-for-field.                                                                                                                                                                                                                 |
| Tables                                  | **TanStack Table** (headless) + shadcn `<Table>` styling                                     | Sorting/filtering/pagination for the plans/blocks/trains lists without pulling in a heavy grid library.                                                                                                                                                                                                                                            |
| Charts / KPIs                           | **Recharts**                                                                                 | Simple, composable, good enough for utilization/duration/merge-count metrics (Section 20).                                                                                                                                                                                                                                                         |
| Track/network visualization ("the map") | **@xyflow/react (React Flow)** for a _schematic_ track diagram                               | See Section 8 — this is **not** a geographic map. Stations/GIS coordinates are backlog (architecture Section 29.6), so a literal Leaflet/Mapbox map has no real geo data to plot yet. React Flow renders tracks as nodes/edges with block overlays, which matches what the Operational DB actually has (`tracks`, `track_dependencies`, `blocks`). |
| Geographic map (stretch, backlog-gated) | **react-leaflet** (OpenStreetMap tiles)                                                      | Only becomes viable once `stations` (lat/long) ships — documented here so the choice is made in advance and not re-litigated later.                                                                                                                                                                                                                |
| Toasts / notifications                  | **sonner** (shadcn's recommended toast)                                                      | Lightweight, accessible, used for optimistic-write feedback and polling-driven "plan updated" nudges.                                                                                                                                                                                                                                              |
| Client state (non-server)               | **React state + URL search params**; Zustand only if cross-page client state is truly needed | Avoid over-engineering — most state here is server state (React Query's job).                                                                                                                                                                                                                                                                      |
| Dates/times                             | **date-fns** + a fixed IST-aware formatter helper                                            | Railway operations are timezone-sensitive; centralize formatting in one util.                                                                                                                                                                                                                                                                      |
| Package manager                         | Whatever the repo already uses (npm, per `package.json`)                                     | No reason to switch.                                                                                                                                                                                                                                                                                                                               |

New dependencies to add to `frontend/package.json` when Phase 9 starts:
`@tanstack/react-query`, `@tanstack/react-table`, `react-hook-form`, `zod`,
`@hookform/resolvers`, `@xyflow/react`, `recharts`, `sonner`, `date-fns`,
`lucide-react`, `class-variance-authority`, `clsx`, `tailwind-merge`,
`tailwindcss-animate` (shadcn deps), plus `tailwindcss`/`postcss`/`autoprefixer` and the
shadcn CLI (`npx shadcn@latest init`) to scaffold `components/ui/*`.

---

## 2. Design System

- **Theme**: light + dark mode via `next-themes` (shadcn convention), CSS variables for
  color tokens (`--background`, `--foreground`, `--primary`, etc.) so status colors stay
  consistent across components.
- **Status color convention** (used everywhere: badges, table rows, timeline bars):
  - `proposed` → amber/yellow
  - `approved` → blue
  - `active` → green
  - `completed` → slate/gray
  - `superseded` / `cancelled` → red/muted-red
  - Optimization run: `pending`/`running` → blue pulse, `succeeded` → green, `failed` → red
- **Typography**: Tailwind default scale (Inter or system font stack); dense
  numeric/table content uses `tabular-nums`.
- **Density**: this is an operations dashboard, not a marketing site — prefer compact
  spacing (`text-sm`, tight table rows) over generous whitespace.
- **Layout shell**: fixed left sidebar (nav) + top bar (breadcrumb, correlation-id/debug
  toggle in dev, user/department stub) + scrollable content area. Responsive: sidebar
  collapses to a drawer under `md`.

---

## 3. Information Architecture / Routes (Next.js App Router)

```text
/                          -> redirect to /dashboard
/dashboard                 -> overview: KPIs, active plans, alerts, recent activity
/requests                  -> list of block requests (own department by default)
/requests/new              -> new block request wizard (technical | operational)
/requests/[id]             -> request detail + status timeline
/plans                     -> list of plans (filter: status, section)
/plans/[id]                -> plan detail: blocks, source requests, metrics, schematic
/network                   -> track network schematic (React Flow), section-scoped
/network/[sectionId]       -> zoomed-in section view
/trains                    -> train list + schedules
/trains/[id]               -> train detail (schedules, delay history if available)
/alerts                    -> (stub until Section 27+ notifications ship) simple event feed
/settings                  -> stub: department/user context switcher (no real auth yet)
```

Route grouping: `app/(shell)/...` for everything behind the sidebar layout, `app/login`
reserved but not built (stub auth only — real RBAC is backlog).

---

## 4. Page-by-Page Breakdown

### 4.1 Dashboard (`/dashboard`)

- KPI cards: active plans count, total block-hours this week, requests pending
  optimization, average merge ratio (Section 20 metrics).
- "Active & proposed plans" table (top N, link to `/plans`).
- "Recent block requests" table (top N, link to `/requests`).
- Simple activity feed: last N `optimization.result` / `block_request.*` events (polled).

### 4.2 Block Request Forms (`/requests/new`)

- Step 1: choose request kind — **Technical** vs **Operational** (architecture Sections
  11/12) — two distinct forms, not one giant conditional form.
- Technical form fields: track, requested window (start/end), train stops, railway
  line, direction, restriction type, train type, finance reference, responsible
  department, additional parameters (key/value list), affected tracks (multi-select).
- Operational form fields: track, requested window, reason (enum: BRIDGE, UNDERPASS,
  ROAD_CROSSING, TREE_WORK, CABLE_MAINTENANCE, TRACK_MAINTENANCE, OTHER), reason
  details, expected duration, safety notes, affected tracks.
- Common: priority (normal/high/emergency), is_emergency toggle (visually distinct,
  confirmation dialog since it likely bypasses normal review later — backlog-aware).
- Client-side zod validation mirrors `contracts.events.schemas` (end > start, required
  fields per request_type) — a fast fail before hitting the Command Service.
- Submit → `POST /block-requests` via the gateway → optimistic "submitted" state →
  toast + redirect to `/requests/[id]`.

### 4.3 Request Detail (`/requests/[id]`)

- Read-only summary of submitted fields.
- **Status timeline**: draft → submitted → scheduled/merged → (plan link once
  available). Backed by `request_status` enum.
- Edit button only when status is DRAFT/SUBMITTED (matches Command Service's
  `UPDATABLE_STATUSES` — mirror backend rules in the UI so it never offers an action the
  API will reject).
- "Part of Plan #\_\_\_" link once a `PlanItem` exists for it (via `/blocks?...` lookup or
  a small enrichment endpoint down the line).

### 4.4 Plans List (`/plans`)

- Table (TanStack Table): status, section, block count, request count, total block
  duration, created date. Filters: status, section — mirrors Query Service's
  `GET /plans?status=&section_id=`.
- Status badge uses the shared color convention.

### 4.5 Plan Detail (`/plans/[id]`)

- Header: status, section, org hierarchy breadcrumb (zone/division/section).
- Metrics cards: total block duration, affected tracks, merged requests count
  (`OptimizationResult` fields).
- Blocks table: track, start/end, is_merged badge, contributing request count.
- **Merged block explainability** (architecture Section 17/18 "traceability"): expand a
  block row to show the source `block_request` IDs/summaries that were merged into it —
  this is the single most "AI decision-support" visible feature; do not skip it.
- Mini schematic (React Flow) scoped to just this plan's tracks/blocks.
- "Proposed vs Active" distinction: a visually distinct banner when `status=proposed`
  ("This plan has not been approved yet") vs `active`.

### 4.6 Track Network Schematic (`/network`, `/network/[sectionId]`)

- See Section 8 for the visualization approach in depth.
- Section selector → renders tracks as a node graph with `track_dependencies` as edges.
- Each track node shows: code/name, active/inactive, and a small colored bar for any
  block currently overlapping "now" (green=clear, amber=upcoming block, red=blocked now).
- Click a track node → side panel with that track's blocks (from `/blocks?track_id=`).

### 4.7 Trains (`/trains`, `/trains/[id]`)

- List: train number, type, active flag, schedule count. Filter: active_only.
- Detail: schedule list (track, window) — read-only for MVP (no train-delay UI input
  yet; that is the real-time-loop demo script in Phase 10, likely a dev-only trigger
  button rather than a full form).

### 4.8 Alerts (`/alerts`) — minimal stub

- Just a polled list of recent events (optimization results, track status changes) via
  whatever the Query Service exposes by then. Full notification system is backlog
  (Section 29.4) — this page exists so the nav item + layout slot are reserved.

### 4.9 Settings (`/settings`) — minimal stub

- A department/user picker (plain dropdown, stored in a cookie or localStorage) used to
  populate `requested_by_user_id`/`department_id` on new requests, since there is no
  real login yet. Clearly labeled as a placeholder.

---

## 5. Component Inventory (basic → advanced)

**Basic (shadcn primitives, mostly used as-is):**
`Button`, `Input`, `Textarea`, `Select`, `Checkbox`, `Switch`, `Badge`, `Card`,
`Dialog`, `Sheet` (side panel), `Tabs`, `Tooltip`, `Separator`, `Skeleton` (loading),
`Toast`/`Sonner`, `DropdownMenu`, `Breadcrumb`, `Table`.

**Composite (built on top, app-specific):**

- `StatusBadge` — maps `RequestStatus` / `PlanStatus` / `OptimizationRunStatus` to a
  colored `Badge` (one source of truth for the color convention in Section 2).
- `DataTable` — thin TanStack Table wrapper (sorting, pagination, empty/loading states)
  reused by requests/plans/tracks/trains lists.
- `FilterBar` — URL-search-param-backed filter controls (status/section/etc.), so
  filters are shareable/bookmarkable links, and map 1:1 to Query Service query params.
- `KpiCard` — icon + label + big number + optional trend, used on the dashboard.
- `TimelineStatus` — horizontal step indicator for request/plan lifecycle.
- `BlockRequestForm` (technical) / `OperationalRequestForm` — react-hook-form + zod,
  built from a shared `<RequestFormShell>` (common fields + submit handling) so the two
  forms don't duplicate submit/error logic.
- `MergeExplainability` — expandable panel listing source requests behind a merged
  block (Section 4.5).
- `EmptyState` — consistent "no data" panel with an optional CTA (e.g., "No requests
  yet — create one").
- `ErrorState` — consistent failed-fetch panel with retry button (wraps React Query's
  `refetch`).
- `CorrelationIdBadge` — small dev-only chip showing the `X-Correlation-Id` of the last
  API response (huge help when debugging the write→Kafka→optimizer→read loop).

**Advanced:**

- `TrackNetworkGraph` — React Flow wrapper: custom node type (`TrackNode`) + custom
  edge styling for `track_dependencies.relationship_type`; layout via `dagre` or
  React Flow's built-in auto-layout (evaluate at build time — dagre gives more
  predictable schematic layout for a linear/branching rail network).
- `PlanScheduleChart` — Recharts/Gantt-style horizontal bar chart of blocks over time
  per track (a lightweight custom Gantt is fine; avoid a heavy Gantt library for MVP).
- `RealtimeIndicator` — shows "live" polling status + last-synced time (surfaces the
  Read Store's `synced_at` freshness stamp from Section 6 of the backend plan — this is
  a direct UI hook into a field we already added for exactly this purpose).
- `WhatIfDrawer` (stretch, Phase 10/backlog-adjacent) — placeholder side panel wired
  but not implemented; reserves the UX slot architecture Section 3 item 60 asks for
  ("what-if planning controls") without committing to the full simulation engine
  (Section 29.7, backlog).

---

## 6. Data Fetching & Caching Strategy

- One typed API client module (`lib/api/client.ts`) wrapping `fetch`, base URL =
  `NEXT_PUBLIC_API_GATEWAY_URL`, injects nothing else (the gateway generates the
  correlation ID; the client just reads it back from the response header for the dev
  `CorrelationIdBadge`).
- One hook per resource, e.g. `usePlans(filters)`, `usePlan(id)`, `useBlocks(filters)`,
  `useTracks(filters)`, `useTrains(filters)`, `useCreateBlockRequest()`,
  `useUpdateBlockRequest()` — thin wrappers over `useQuery`/`useMutation`.
- Query keys mirror the gateway path + filters (`["plans", {status, section_id}]`) so
  invalidation is precise.
- Polling: list/detail views most likely to change (plans, requests, network) poll on
  a modest interval (e.g. 15–30s via `refetchInterval`) rather than adding WebSockets —
  matches the backend's polling-ETL philosophy (Section 6 backend plan) and needs no new
  infra. This can be swapped for a push mechanism later without changing the UI's data
  layer (React Query hooks stay the same either way).
- Mutations (`POST`/`PATCH /block-requests`) invalidate the relevant list queries and
  show the write as immediately "submitted" (optimistic), while the plan/blocks views
  will naturally pick up the optimizer's result on their next poll — the UI should be
  explicit that this step is asynchronous (Section 21 backend: "write path is
  asynchronous after Kafka publication").

---

## 7. Forms & Validation Strategy

- zod schemas colocated under `lib/schemas/` named to mirror the backend contracts
  (`blockRequestTechnicalSchema`, `blockRequestOperationalSchema`) — field names should
  match `contracts.events.schemas` exactly so there's no translation layer to keep in
  sync manually (a comment at the top of each zod file should point back to the
  corresponding Python schema file).
- Server errors (422 from Command Service, proxied verbatim by the gateway) are mapped
  back onto the relevant form field where possible; anything unmapped surfaces as a
  toast + a generic form-level error banner.
- The emergency/high-priority toggle requires an inline confirmation ("This will be
  flagged as high priority") — no hidden destructive-feeling actions.

---

## 8. Track/Network Visualization — the "map" (key decision, explained)

The architecture talks about visualizing tracks/dependencies/affected-resources
(Section 19, items 416–418: "The frontend can visualize affected tracks... makes the
optimization result easier to understand"), but the **Operational DB has no geographic
coordinates** for the MVP — `stations` (which would carry lat/long) is explicitly
backlog (architecture Section 29.6 / database_schema.md). Building a literal Leaflet/
Mapbox map for the MVP would mean plotting fake coordinates, which is misleading for an
operations tool.

**Decision:** build a **schematic network diagram**, not a geographic map, using
**React Flow (`@xyflow/react`)**:

- Nodes = tracks (`Track` model: code, name, line, direction, is_active).
- Edges = `track_dependencies` (`relationship_type` drives edge style/label).
- Layout computed with `dagre` (or React Flow's `elk` layout adapter) for a readable
  left-to-right or top-to-bottom schematic — this is exactly how real railway control
  panels represent a section, and matches what operators (Section Controllers, per
  architecture Section 28) already expect to read.
- Blocks overlapping "now" or "soon" render as colored overlays/badges on the relevant
  track node (pulls from `/blocks?track_id=`).
- This approach requires zero new backend fields and works entirely off data the Phase
  1/6/7 backend already exposes.

**Documented stretch/backlog path:** once `stations` ships (lat/long), add a second,
optional geographic view using `react-leaflet` + OpenStreetMap tiles (no API key
needed, unlike Mapbox/Google) as a toggle next to the schematic view — do not build this
until the data exists to back it.

---

## 9. Loading / Error / Empty States

- Every list/detail page: `Skeleton` while loading, `ErrorState` (with retry) on
  failure, `EmptyState` (with CTA where relevant) when the array is empty — no bare
  blank screens.
- Global fetch failures (gateway unreachable) show a top-level banner rather than
  breaking every widget independently.
- Distinguish "cache-stale but shown" from "loading" where the Read Store's
  `synced_at` is old (see `RealtimeIndicator`) — this is a deliberate UX signal that the
  data is real but may be a few seconds behind, consistent with the backend's
  eventual-consistency design (Section 7: "stale data must not be used where safety or
  operational correctness is critical" — this indicator is exactly how we surface that).

---

## 10. Accessibility & Responsiveness

- shadcn/Radix primitives give keyboard nav + ARIA roles for free — don't bypass them
  with custom divs where a primitive exists.
- Color is never the only status signal — every `StatusBadge` also carries text.
- Layout: sidebar + content is desktop-first (this is an ops dashboard used at desks/
  control rooms), but must not break down to a usable single-column layout at tablet
  width for field supervisors (architecture Section 28, persona: Field Supervisor on
  mobile app — full mobile app is out of scope for Phase 9, but the web UI shouldn't be
  unusable on a tablet).

---

## 11. Testing Strategy (ties into Phase 13)

- Component tests (Vitest + React Testing Library) for `StatusBadge`, `DataTable`,
  `BlockRequestForm` validation rules.
- One Playwright/Cypress e2e happy-path: submit a technical block request → see it in
  `/requests` → (after backend optimization) see it appear inside a plan on `/plans`.
- Mock the API Gateway with MSW (Mock Service Worker) for component-level tests so the
  frontend test suite doesn't require the full backend running.

---

## 12. Backlog-Awareness (build so these slot in later, don't build them now)

- Real auth/RBAC (Section 27): `/settings` department picker is the deliberate
  stand-in; swapping in real login later should only touch the auth provider, not every
  page (route guards should already be centralized in the `(shell)` layout).
- Approval workflow (Section 27.2): plan detail page already has a status banner slot;
  an "Approve/Reject" action bar can be added there without restructuring the page.
- Notifications (Section 29.4): `/alerts` page + `RealtimeIndicator` are the reserved
  UX surface.
- What-if simulation (Section 29.7): `WhatIfDrawer` placeholder reserves the slot.
- Corridor bundling (Section 29.1): plan detail's block table is already grouped by
  track, which is the natural place to later show corridor groupings.

---

## 13. Folder Structure (proposed)

```text
/frontend
  app/
    (shell)/
      layout.tsx              - sidebar + topbar shell
      dashboard/page.tsx
      requests/page.tsx
      requests/new/page.tsx
      requests/[id]/page.tsx
      plans/page.tsx
      plans/[id]/page.tsx
      network/page.tsx
      network/[sectionId]/page.tsx
      trains/page.tsx
      trains/[id]/page.tsx
      alerts/page.tsx
      settings/page.tsx
    layout.tsx                 - root layout (theme provider, react-query provider)
    page.tsx                   - redirect to /dashboard
  components/
    ui/                        - shadcn generated primitives (do not hand-edit heavily)
    status-badge.tsx
    data-table.tsx
    filter-bar.tsx
    kpi-card.tsx
    timeline-status.tsx
    empty-state.tsx
    error-state.tsx
    correlation-id-badge.tsx
    forms/
      request-form-shell.tsx
      technical-request-form.tsx
      operational-request-form.tsx
    network/
      track-network-graph.tsx
      track-node.tsx
    charts/
      plan-schedule-chart.tsx
  lib/
    api/
      client.ts
      plans.ts
      blocks.ts
      tracks.ts
      trains.ts
      block-requests.ts
    schemas/
      block-request-technical.ts
      block-request-operational.ts
    hooks/
      use-plans.ts
      use-blocks.ts
      use-tracks.ts
      use-trains.ts
      use-block-requests.ts
    format.ts                  - date/time/duration formatting helpers
  styles/globals.css
```

---

## 14. Sub-Phase Breakdown (replaces the single Phase 9 in plan.md)

Phase 9 is split into three sub-phases so it can be picked up incrementally, same as
every backend phase. See [plan.md](./plan.md) Phase 9 for the authoritative status of
each.

### Phase 9A — Foundation & Shell

1. Install and configure Tailwind, shadcn/ui (`init` + base primitives listed in
   Section 5 "Basic"), `next-themes`, `lucide-react`.
2. Set up TanStack Query provider, the typed API client (`lib/api/client.ts`), and the
   `.env.example` var already present (`NEXT_PUBLIC_API_GATEWAY_URL`).
3. Build the app shell: root layout, `(shell)` layout with sidebar + topbar, routing
   skeleton for every page in Section 3 (can be empty/stub pages at this point).
4. Build shared primitives: `StatusBadge`, `DataTable`, `FilterBar`, `EmptyState`,
   `ErrorState`, `KpiCard`, `CorrelationIdBadge`.
5. Wire dark/light theme toggle.

### Phase 9B — Core Read + Write Features

1. Implement API hooks (`lib/hooks/*`) for plans/blocks/tracks/trains/block-requests.
2. Build `/dashboard` (KPIs + recent tables).
3. Build `/plans` list + `/plans/[id]` detail (metrics, blocks table, merge
   explainability panel, proposed-vs-active banner) — **without** the schematic yet.
4. Build `/requests` list + `/requests/[id]` detail (status timeline) + `/requests/new`
   (technical + operational forms with zod validation, submit via `useCreateBlockRequest`).
5. Build `/trains` list + detail.
6. Wire polling refetch intervals + optimistic submit states.

### Phase 9C — Visualization & Polish

1. Add `@xyflow/react` + `dagre`; build `TrackNetworkGraph` + `TrackNode`; build
   `/network` and `/network/[sectionId]`.
2. Add `PlanScheduleChart` (Recharts Gantt-style) to `/plans/[id]`.
3. Add `RealtimeIndicator` (surfaces Read Store `synced_at`) across list/detail pages.
4. Build `/alerts` stub and `/settings` department-picker stub.
5. Accessibility pass (keyboard nav, color-independent status, tablet breakpoint check).
6. Component tests for `StatusBadge`/`DataTable`/forms; MSW mocks for the API client.

---

## 15. Open Questions (resolve before/at Phase 9A kickoff if still unanswered)

1. Should the department/user picker in `/settings` (stub auth) persist via cookie
   (SSR-visible) or `localStorage` (client-only)? Leaning cookie so server components
   can read it too.
2. Confirm `dagre` vs React Flow's built-in layout once real `track_dependencies`
   sample data exists (seed data) — pick whichever produces a more readable layout for
   the actual seeded network shape.
3. Confirm polling interval (15s vs 30s) once real backend latency is observed under
   Docker Compose (Phase 11) — this doc's default is a starting point, not final.
