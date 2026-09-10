# Map Visualization Architecture — 3D Tiling Strategy for Team-Waypoints

> **Purpose**: Document the advanced map visualization requirements for Phase 10+ based on analysis of RIVM INFRA (a production railway visualization system).
>
> **Scope**: Complete reference architecture for rendering train positions on a geographical/schematic network map with time-travel support, real-time updates, and 3D data tiling.
>
> **Status**: Design phase (not yet built; guides future phases).

---

## Table of Contents

1. [Overview & Vision](#1--overview--vision)
2. [Comparison: RIVM INFRA vs Team-Waypoints](#2--comparison-rivm-infra-vs-team-waypoints)
3. [Recommended Architecture](#3--recommended-architecture)
4. [Component Breakdown](#4--component-breakdown)
5. [Data Tiling Strategy (3D: X, Y, Time)](#5--data-tiling-strategy-3d-xyz-time)
6. [Real-Time Update Flow](#6--real-time-update-flow)
7. [Map Layer Composition](#7--map-layer-composition)
8. [Frontend State Management](#8--frontend-state-management)
9. [Backend Services](#9--backend-services)
10. [Caching & Optimization](#10--caching--optimization)
11. [Phase 10 Implementation Plan](#11--phase-10-implementation-plan)
12. [Brainstorm: Next-Generation Map Enhancements](#12--brainstorm-next-generation-map-enhancements-post-phase-10a)
    - [12.1 Bigger, organically-random network topology](#121-bigger-organically-random-network-topology)
    - [12.1a Procedural curved track geometry](#121a-procedural-curved-track-geometry--organic-waypoint-interpolation)
    - [12.2 "Live add blocks on map"](#122-live-add-blocks-on-map--interactive-block-creation)
    - [12.3 Scaling data further](#123-scaling-data-further)
    - [12.4 Test-case coverage brainstorm](#124-test-case-coverage-brainstorm)
    - [12.5 Known environment caveat](#125-known-environment-caveat-documented-for-future-contributors)

---

# 1 — OVERVIEW & VISION

## 1.1 What the user sees

A dispatcher or planner opens the application to a **full-screen map**. The map shows:

1. **Static infrastructure** (base map):
   - Track network: lines representing rail segments, nodes at junctions/stations.
   - Station labels and platform identifiers (zoom-level gated).
   - Coordinate system: either geographical (latitude/longitude) or schematic (Cartesian X/Y).

2. **Train positions** (dynamic, real-time or historical):
   - Small train icons placed at their (X, Y, Time) location.
   - Color-coded by train type or line affiliation.
   - Clustering when zoomed out (prevents label collision).
   - Hover popovers showing train number, delay, departure/arrival times.

3. **Blocks/Occupancy** (derived from train positions):
   - Segments of track highlighted/colored to show which block each train occupies.
   - Derived from the train's current position and track geometry.

4. **Restrictions/Maintenance windows** (overlay):
   - Colored poly-lines on affected track segments.
   - Severity badges or icons (speed restriction, blockage, reduced adhesion).
   - Hover/click to view details.

5. **Time controls**:
   - Current time stamp (business clock or custom wallclock).
   - Time-offset slider (± minutes from now).
   - Date/time picker to jump to a past or future moment.
   - Playback controls (future: animate train movement over time).

6. **Sidebar panels**:
   - Train list (sortable table, click to highlight on map, double-click to open edit panel).
   - Restriction list (toggle active/inactive).
   - Alerts/events feed.
   - Filters (layer visibility toggles).

---

## 1.2 User workflows

| #     | Workflow                | Example                                                                                                        |
| ----- | ----------------------- | -------------------------------------------------------------------------------------------------------------- |
| **A** | **Browse real-time**    | Dispatcher opens app at 09:15 and sees all trains as they are now, updating every 2 sec.                       |
| **B** | **Look backwards**      | Adjust time slider to 08:30 to see what happened 45 minutes ago.                                               |
| **C** | **Look forward**        | Pick a future date/time (tomorrow 14:00) to see the predicted train positions.                                 |
| **D** | **Inspect a train**     | Double-click or search for train #2843; panel opens showing stops, delay, platform track, edit capability.     |
| **E** | **Apply a restriction** | Select a time window and track segment, then toggle a restriction (blockage, speed reduction) active/inactive. |
| **F** | **Layering**            | Toggle trains on/off, restrictions on/off, labels on/off to declutter the map.                                 |

---

# 2 — COMPARISON: RIVM INFRA vs TEAM-WAYPOINTS

## 2.1 RIVM INFRA architecture

| Component             | Technology                                   | Purpose                                                                                                        |
| --------------------- | -------------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| **Map engine**        | OpenLayers 10                                | Renders nodes, edges, trains, restrictions; handles clustering, collision-avoiding labels.                     |
| **Coordinate system** | Cartesian (X, Y) or geographical             | Infrastructure graph with microscopically accurate node placement.                                             |
| **State management**  | NgRx (classic) + NgRx Signal Stores          | Business clock, base graph, tile state, train positions, restrictions, panel state.                            |
| **Time system**       | Business clock (REALTIME / CONTROLLED)       | Synced from server, can be offset locally.                                                                     |
| **Real-time data**    | RabbitMQ (inbound) + HTTP polling (frontend) | ETLs consume upstream events, write to MongoDB; frontend polls `/trainpositions` per visible tile every 2 sec. |
| **Data transfer**     | 3D tile versioning (`{id, version}`)         | Tiles have a UUID version; unchanged tiles return empty page (delta transfer).                                 |
| **Caching**           | IndexedDB (Dexie) + localStorage             | Base graph, map config, location-track coordinates cached locally; filter state to localStorage.               |
| **Database**          | MongoDB only                                 | Operational and read stores both in Mongo.                                                                     |
| **Latency**           | ~200 ms per HTTP polling cycle               | Acceptable for dispatcher workflow.                                                                            |
| **Scale**             | Handles ~1000s of trains per tile            | Clustering + renderer optimization.                                                                            |

## 2.2 Team-Waypoints current state (Phase 9C)

| Component            | Technology                                             | Status                                                    |
| -------------------- | ------------------------------------------------------ | --------------------------------------------------------- |
| **Map engine**       | None yet                                               | Dashboard shows KPI cards only.                           |
| **Frontend**         | Next.js 14 + React 18 + Tailwind CSS                   | Production-ready for CRUD pages.                          |
| **State management** | TanStack Query (data fetching) + React hooks           | No global store; local component state.                   |
| **Real-time data**   | Not implemented                                        | Backend is Python FastAPI; no Kafka consumer in frontend. |
| **Database**         | PostgreSQL (Operational) + SQLite (Read Store)         | OLTP-optimized, no time-series data.                      |
| **API contracts**    | REST only (`GET /plans`, `POST /block-requests`, etc.) | No streaming or WebSocket.                                |
| **Time system**      | Static timestamps in data                              | No business clock, no time-travel UI.                     |
| **Caching**          | TanStack Query (10s staleness)                         | No IndexedDB, no local persistence.                       |

## 2.3 Key differences

| Aspect               | RIVM INFRA                                   | Team-Waypoints                                          |
| -------------------- | -------------------------------------------- | ------------------------------------------------------- |
| **Purpose**          | Real-time operational dispatch               | Block planning / optimization                           |
| **Update frequency** | Every 2 sec (trains move)                    | Every 5–10 min (blocks don't move as often)             |
| **Viewport focus**   | Tracks + current/forecast trains             | Tracks + blocks (derived from trains)                   |
| **Geographic scope** | Entire railway network                       | One corridor or division                                |
| **Complexity**       | Microscopically accurate (millions of nodes) | Simplified schematic or Cartesian (hundreds of nodes)   |
| **Backend write**    | RabbitMQ events (upstream RIDS system)       | Kafka events (internal: command service → optimization) |
| **Read consistency** | Eventually consistent (tiles versioned)      | Strongly consistent (no cache beyond 10s)               |

---

# 3 — RECOMMENDED ARCHITECTURE

## 3.1 High-level stack for Team-Waypoints Phase 10+

```
┌─────────────────────────────────────────────────────────────┐
│ FRONTEND (Next.js 14 + React 18 + TypeScript)              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────┐       ┌──────────────────────┐   │
│  │  Map Visualization   │       │  Time Controls       │   │
│  │  (Map.tsx)           │       │  (Clock.tsx)         │   │
│  │                      │       │                      │   │
│  │ • Maplibre GL or     │       │ • Business clock     │   │
│  │   Leaflet.js         │       │   display            │   │
│  │ • Vector layer:      │       │ • Time offset slider │   │
│  │   tracks, trains,    │       │ • Date/time picker   │   │
│  │   restrictions       │       │ • Playback controls  │   │
│  │ • Clustering +       │       │   (future)           │   │
│  │   tooltips           │       └──────────────────────┘   │
│  │                      │                                    │
│  │ • 3D tile viewport   │       ┌──────────────────────┐   │
│  │   calculation        │       │  Sidebar Panels      │   │
│  │ • Pan/zoom events    │       │  (Sidebar.tsx)       │   │
│  └──────────────────────┘       │                      │   │
│                                 │ • Train list         │   │
│                                 │ • Restriction list   │   │
│                                 │ • Alerts/events      │   │
│                                 │ • Filters            │   │
│                                 └──────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  State Management (TanStack Query + Zustand)         │   │
│  │  • mapStore: viewport, zoom, center, layers visible  │   │
│  │  • trainPositionsStore: live positions per tile      │   │
│  │  • blocksStore: occupied blocks (derived)            │   │
│  │  • restrictionsStore: active restrictions            │   │
│  │  • businessClockStore: current/custom time           │   │
│  │  • filterStore: layer visibility, search filters     │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  API Calls (TanStack Query hooks)                    │   │
│  │  • useBaseGraph() — GET /basegraph                    │   │
│  │  • useTrainPositions(tiles) — POST /trainpositions   │   │
│  │  • useBlocks(filters) — GET /blocks                  │   │
│  │  • useRestrictions(time) — GET /restrictions         │   │
│  │  • useBusinessClock() — GET /business-clock          │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
            ▲                          ▲                ▲
            │ REST (GET/POST)          │ WebSocket?     │ IndexedDB
            │ (+ correlation ID)       │ (future)       │ (Dexie)
            │                          │                │
┌───────────┴──────────────────────────┴────────────────┴─────┐
│ BACKEND MICROSERVICES (Python FastAPI)                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Query Service (Port 8002)                         │    │
│  │  • GET /basegraph  → Base graph (tracks + nodes)   │    │
│  │  • POST /trainpositions(tiles)                     │    │
│  │    → Train positions per tile (with versioning)    │    │
│  │  • GET /blocks → Derived from train positions      │    │
│  │  • GET /restrictions → Active restrictions         │    │
│  │  • GET /business-clock → Current business time     │    │
│  │                                                     │    │
│  │  Redis Cache-Aside:                                │    │
│  │  • base_graph (TTL: 1 hour)                        │    │
│  │  • train_positions:tile_id (TTL: 10 sec)           │    │
│  │  • restrictions:time (TTL: 30 sec)                 │    │
│  └────────────────────────────────────────────────────┘    │
│                    ▲                                         │
│                    │ Read Store tables                      │
│                    │ (denormalized)                         │
│      ┌─────────────┴──────────────┐                        │
│      │                            │                        │
│  ┌───▼──────────────┐    ┌────────▼────────────┐            │
│  │ Tile Versioning  │    │ Projection/ETL      │            │
│  │ Service (future) │    │ (polling every 5min)│            │
│  │                  │    │                     │            │
│  │ Manages tile     │    │ Syncs Operational   │            │
│  │ UUIDs, detects   │    │ DB → Read Store     │            │
│  │ changed tiles    │    │ (PlanSummary,       │            │
│  │                  │    │  BlockView, etc.)   │            │
│  └──────────────────┘    └─────────────────────┘            │
│                                                              │
└─────────────────────────────────────────────────────────────┘
            ▲                          ▲
            │ SQL queries              │ Kafka consume
            │                          │
      ┌─────┴───────────────┐   ┌─────┴─────────────────┐
      │                     │   │                       │
  ┌───▼──────────┐   ┌──────▼────────┐   ┌──────────────▼──────┐
  │ Read Store   │   │ Operational   │   │ Kafka Topics        │
  │ (PostgreSQL) │   │ DB (PostgreSQL)   │ (Redpanda)          │
  │              │   │              │   │                      │
  │ Projections: │   │ • Blocks     │   │ • plan.commands     │
  │ • PlanSummary│   │ • Trains     │   │ • optimization.*    │
  │ • BlockView  │   │ • Tracks     │   │ • track.status_*    │
  │ • TrackView  │   │ • Plans      │   │ • train.delay       │
  │ • TrainView  │   │ • Requests   │   └─────────────────────┘
  │              │   │              │
  └──────────────┘   └──────────────┘
```

## 3.2 Key technology choices

### **Map Engine: Maplibre GL JS**

- **Why not OpenLayers?**
  - RIVM uses OpenLayers (very mature, GIS-focused).
  - Team-waypoints is simpler (schematic rather than microscopically accurate).
  - OpenLayers has a steeper learning curve and larger bundle size (~500 KB gzipped).
  - Maplibre is lighter (~200 KB gzipped), has better TypeScript support, and integrates well with React.

- **Why Maplibre over Leaflet?**
  - Leaflet is vector/raster only; Maplibre has vector tiles + style engine (Mapbox GL compatible).
  - Maplibre clusters, labels, and collision avoidance are built-in and better than Leaflet plugins.
  - Maplibre works with schematic/Cartesian coordinates (not just lat/lng).

### **State Management: TanStack Query + Zustand**

- **TanStack Query**: Already in use for API data fetching; continues for train positions, blocks, restrictions.
- **Zustand**: Lightweight global store for UI state (map viewport, selected train, panel state, filters).
- **Alternative considered**: NgRx Signal Stores (as used in RIVM). Too heavy for Next.js + React; Zustand is simpler and better-suited.

### **Caching & Persistence: IndexedDB (via Dexie.js) + localStorage**

- Same as RIVM.
- IndexedDB: base graph, map config, location-track coordinates (persists across sessions).
- localStorage: layer visibility toggles, filter state, custom clock settings.

### **Real-time Updates: HTTP Polling (initial) + WebSocket (future)**

- **Phase 10a**: Use HTTP polling (simpler, matches current backend readiness).
- **Phase 10b+**: Upgrade to WebSocket for train position streaming (lower latency, 1-2 sec).

---

# 4 — COMPONENT BREAKDOWN

## 4.1 Frontend React Components

### **1. `MapContainer.tsx`** (root map component)

```typescript
interface MapContainerProps {
  baseGraphData: BaseGraph;
  trainPositions: TrainPosition[];
  blocks: Block[];
  restrictions: Restriction[];
  businessTime: Date;
  zoom: number;
  center: { x: number; y: number }; // or [lng, lat]
  onViewportChange: (zoom, center, extent) => void;
  onTrainClick: (trainId) => void;
  onTrainDoubleClick: (trainId) => void;
  onRestrictionClick: (restrictionId) => void;
}
```

**Responsibilities:**

- Initialize Maplibre GL instance with a Cartesian or geographical style.
- Render base map layers (base, tracks, stations).
- Dynamically add/remove train position features (refresh on every POST /trainpositions response).
- Dynamically add/remove block overlay features (derived from train positions).
- Dynamically add/remove restriction overlays.
- Emit `onViewportChange` when map is panned/zoomed → triggers tile recalculation + new polling.
- Emit train selection events → open side panel.

---

### **2. `TimeControls.tsx`** (header clock and sliders)

```typescript
interface TimeControlsProps {
  businessClock: BusinessClock;
  timeOffset: number; // minutes
  onTimeOffsetChange: (offset) => void;
  onDateTimePickerChange: (date, time) => void;
  onResetToNow: () => void;
}
```

**Responsibilities:**

- Display current business time (mode: REALTIME or CONTROLLED).
- Offset slider (±10 to +50 minutes, step 5 sec).
- Date/time picker modal (jump to arbitrary past/future moment).
- Reset button (return to now).
- On change → update map viewport tiles + re-trigger polling with new timestamp.

---

### **3. `TrainListPanel.tsx`** (left sidebar)

```typescript
interface TrainListPanelProps {
  trains: TrainView[];
  selectedTrainId?: string;
  onSelectTrain: (id) => void;
  onEditTrain: (id) => void;
}
```

**Responsibilities:**

- Table of current trains (from `useTrainPositions` hook).
- Sortable columns: train #, line, status, current platform, ETA, delay.
- Click row → highlight on map; double-click → open edit panel.
- Filter + search textbox.

---

### **4. `RestrictionListPanel.tsx`** (left sidebar)

```typescript
interface RestrictionListPanelProps {
  restrictions: Restriction[];
  selectedRestrictionId?: string;
  onSelectRestriction: (id) => void;
  onToggleActive: (id, newState: "ACTIVE" | "INACTIVE") => void;
}
```

**Responsibilities:**

- Table of restrictions (track, type, start time, end time, severity).
- Toggle buttons (Activate / Deactivate).
- Click row → highlight segment on map.

---

### **5. `TrainDetailPanel.tsx` / `TrainEditPanel.tsx`** (right sidebar)

Similar to current Phase 9B implementation, plus:

- Display train's current position and block occupancy on map.
- Edit arrival/departure times → re-calculate blocks → live update on map.

---

## 4.2 Frontend Stores (Zustand)

```typescript
// map.store.ts
type MapStore = {
  zoom: number;
  center: { x: number; y: number };
  extent: { minX; maxX; minY; maxY };
  layersVisible: { trains: bool; restrictions: bool; labels: bool };
  selectedTrainId?: string;
  selectedRestrictionId?: string;
  setZoom: (z) => void;
  setCenter: (c) => void;
  setExtent: (e) => void;
  // ...
};

// businessClock.store.ts
type BusinessClockStore = {
  clock: BusinessClock;
  timeOffset: number; // minutes
  customTime?: Date;
  customTimeEnabled: bool;
  setTimeOffset: (offset) => void;
  setCustomTime: (date, time) => void;
  // ...
};

// filter.store.ts
type FilterStore = {
  showTrains: bool;
  showRestrictions: bool;
  showLabels: bool;
  searchText: string;
  // ... persisted to localStorage
};
```

---

# 5 — DATA TILING STRATEGY (3D: X, Y, TIME)

## 5.1 The tile concept

**Goal**: Avoid sending all train positions for the entire network every polling cycle. Instead, send only the data that is currently visible (or will become visible soon).

A **tile** is a bounding box in (X, Y) space plus a time window. Example:

```
Tile ID: "125000_-10000_2026-08-31T09:15"
  X range:    [125000, 135000)
  Y range:    [-10000, 0)
  Time range: [2026-08-31T09:15, 2026-08-31T09:30)
```

Each tile has a **version UUID**. When the frontend polls, it sends:

```json
[
  { "id": "125000_-10000_2026-08-31T09:15", "version": "8f1c...uuid" },
  { "id": "130000_-10000_2026-08-31T09:15", "version": "a2d3...uuid" }
]
```

The backend compares the sent `version` against the stored version. If they match, the tile hasn't changed → return `null` or empty page. If they differ → return all train positions in that tile.

## 5.2 Tile computation on the frontend

```typescript
// Given:
// - `nodes`: all infrastructure nodes (from base graph)
// - `mapExtent`: current viewport [minX, maxX, minY, maxY]
// - `trainsLayer.tileSize`: { width: 10000, height: 10000, timeSpanSecs: 900 }
// - `businessTime`: current or custom wallclock

// Step 1: Compute global tile grid
const tileWidth = trainsLayer.tileSize.width; // 10000
const tileHeight = trainsLayer.tileSize.height; // 10000
const tileTimeSpan = trainsLayer.tileSize.timeSpanSecs / 60; // 15 minutes

const minX = Math.min(...nodes.map((n) => n.x));
const maxX = Math.max(...nodes.map((n) => n.x));
const minY = Math.min(...nodes.map((n) => n.y));
const maxY = Math.max(...nodes.map((n) => n.y));

const gridMinX = Math.floor(minX / tileWidth) * tileWidth;
const gridMaxX = Math.ceil(maxX / tileWidth) * tileWidth;
const gridMinY = Math.floor(minY / tileHeight) * tileHeight;
const gridMaxY = Math.ceil(maxY / tileHeight) * tileHeight;

// Step 2: Compute visible tiles in the current viewport
const visibleTiles = [];
for (
  let x = Math.max(
    gridMinX,
    Math.floor(mapExtent.minX / tileWidth) * tileWidth,
  );
  x < Math.min(gridMaxX, Math.ceil(mapExtent.maxX / tileWidth) * tileWidth);
  x += tileWidth
) {
  for (
    let y = Math.max(
      gridMinY,
      Math.floor(mapExtent.minY / tileHeight) * tileHeight,
    );
    y < Math.min(gridMaxY, Math.ceil(mapExtent.maxY / tileHeight) * tileHeight);
    y += tileHeight
  ) {
    const tileId = `${x}_${y}_${roundToInterval(businessTime, tileTimeSpan)}`;
    visibleTiles.push(tileId);
  }
}

// Step 3: Compare against stored version UUIDs
const tilesWithVersions = visibleTiles.map((id) => ({
  id,
  version: tileVersionCache.get(id), // undefined on first request
}));

// Step 4: POST to backend
const response = await POST("/trainpositions", { tiles: tilesWithVersions });
// Response: { data: TrainPosition[], meta: { dataTileVersions: { "125000_-10000_2026-08-31T09:15": "abc...uuid" } } }

// Step 5: Update version cache
if (response.meta?.dataTileVersions) {
  for (const [tileId, version] of Object.entries(
    response.meta.dataTileVersions,
  )) {
    tileVersionCache.set(tileId, version);
  }
}
```

## 5.3 Backend tile storage

Tile versioning is implemented via a `data_tile` table in the **Read Store**:

```sql
CREATE TABLE data_tile (
  id TEXT PRIMARY KEY,           -- e.g. "125000_-10000_2026-08-31T09:15"
  version UUID NOT NULL,         -- changes when data in tile changes
  last_updated TIMESTAMPTZ,      -- when this version was generated
  train_count INT,               -- hint for load shedding
  CONSTRAINT unique_tile UNIQUE (id, version)
);
```

When a train position is written or updated, the ETL bumps the tile's `version` UUID.

---

# 6 — REAL-TIME UPDATE FLOW

## 6.1 Polling loop (HTTP, every 2 seconds)

```
1. MapContainer observes: zoom, center, extent
2. On zoom/pan/time-change:
   a. Compute visible tile IDs + retrieve cached versions
   b. POST /trainpositions(tiles) with versions
   c. If response.data is empty → no change, skip step 3
   d. Merge response into trainPositionsStore
   e. Trigger MapContainer re-render
3. Update train features on map:
   a. Call MapService.updateTrainFeatures(trainPositions)
   b. Maplibre refreshes the trains vector layer
4. Derive blocks from train positions:
   a. For each train position, resolve which block segment it occupies
   b. Store in blocksStore
   c. Render blocks layer (colored overlay)
5. Schedule next poll (interval: 2 sec)
```

**Rationale for polling vs. WebSocket:**

- Simpler to implement without a full WebSocket infrastructure.
- Acceptable latency for a planning tool (trains don't move as fast as real dispatch).
- Redis cache ensures the backend doesn't re-query Postgres on every poll.

**Future upgrade (Phase 10b):**

```
POST /trainpositions → WebSocket /stream/trainpositions?tiles=[...]
  Server pushes only changed trains every ~1 sec
  Client receives delta updates, no full tile re-poll
  Latency: ~500 ms instead of 2 sec
```

---

# 7 — MAP LAYER COMPOSITION

All layers rendered in Maplibre GL, using the **Cartesian style engine**:

## 7.1 Base layers (from GET /basegraph)

```
┌─────────────────────────────────────────────────────┐
│ Layer: "nodes" (z-index 1)                          │
│  ├─ Type: circle                                     │
│  ├─ Features: InfraNode[]                            │
│  └─ Style: radius 3, color #333, z-index 1          │
├─────────────────────────────────────────────────────┤
│ Layer: "edges" (z-index 2)                          │
│  ├─ Type: line                                       │
│  ├─ Features: InfraEdge[] (line segments)            │
│  └─ Style: width 2, color #666, dashed if blocked   │
├─────────────────────────────────────────────────────┤
│ Layer: "station-labels" (z-index 3)                 │
│  ├─ Type: symbol                                     │
│  ├─ minZoom: 12                                      │
│  ├─ Features: Station.name at centroid              │
│  └─ Style: font 12px, color #000                    │
├─────────────────────────────────────────────────────┤
│ Layer: "platform-labels" (z-index 4)                │
│  ├─ Type: symbol                                     │
│  ├─ minZoom: 14                                      │
│  ├─ Features: TrackLabel.name                        │
│  └─ Style: font 10px, color #555                    │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ Layer: "blocks-occupied" (z-index 10)               │
│  ├─ Type: line                                       │
│  ├─ Features: Block (derived from trains)            │
│  ├─ Filter: occupation_status == 'occupied'         │
│  └─ Style: width 6, color #ff6600, opacity 0.7      │
├─────────────────────────────────────────────────────┤
│ Layer: "blocks-planned" (z-index 9)                 │
│  ├─ Type: line                                       │
│  ├─ Features: Block                                  │
│  ├─ Filter: occupation_status == 'planned'          │
│  └─ Style: width 4, color #ffcc00, opacity 0.5      │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ Layer: "restrictions" (z-index 20)                  │
│  ├─ Type: line (poly-lines on affected segments)    │
│  ├─ Features: Restriction[]                         │
│  ├─ Filter: active == true                          │
│  ├─ Color codes: blockage=#ff0000, speed=#ffcc00,   │
│  │              adhesion=#ff6600                     │
│  ├─ Style: width 5, dashed, full opacity            │
│  └─ Hover: highlighted with halo, tooltip appears   │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ Layer: "trains" (z-index 30)                        │
│  ├─ Type: symbol (clustered)                        │
│  ├─ Features: TrainPosition[]                       │
│  ├─ ClusterMaxZoom: 15 (cluster only below this)    │
│  ├─ ClusterRadius: 50 px                            │
│  ├─ Icon: small train SVG, color by line/type       │
│  ├─ Label: train # (when not clustered)             │
│  └─ Cluster label: "5+" count badge                 │
│     (donut shape, animated on click to zoom in)     │
└─────────────────────────────────────────────────────┘
```

## 7.2 Layer visibility (filter state)

```typescript
mapStore.layersVisible = {
  trains: true,
  restrictions: true,
  stationLabels: true,
  platformLabels: false, // gated by zoom
  blocks: true,
};

// Maplibre: layer.setLayout({ visibility: isVisible ? 'visible' : 'none' })
```

Persisted to `localStorage` so preferences survive reload.

---

# 8 — FRONTEND STATE MANAGEMENT

Combine **TanStack Query** (data fetching) + **Zustand** (UI state) + **localStorage**:

```typescript
// stores/map.store.ts
import { create } from "zustand";
import { persist } from "zustand/middleware";

interface MapState {
  zoom: number;
  center: { x: number; y: number };
  extent: { minX: number; maxX: number; minY: number; maxY: number };
  layersVisible: Record<string, boolean>;
  selectedTrainId?: string;
  selectedRestrictionId?: string;

  setZoom: (z: number) => void;
  setCenter: (c: { x: number; y: number }) => void;
  setExtent: (e: typeof MapState.extent) => void;
  setLayerVisible: (layer: string, visible: boolean) => void;
  selectTrain: (id?: string) => void;
  selectRestriction: (id?: string) => void;
}

export const useMapStore = create<MapState>()(
  persist(
    (set) => ({
      zoom: 12,
      center: { x: 0, y: 0 },
      extent: { minX: 0, maxX: 10000, minY: 0, maxY: 10000 },
      layersVisible: { trains: true, restrictions: true, labels: true },
      selectedTrainId: undefined,
      selectedRestrictionId: undefined,
      setZoom: (z) => set({ zoom: z }),
      setCenter: (c) => set({ center: c }),
      setExtent: (e) => set({ extent: e }),
      setLayerVisible: (layer, visible) =>
        set((state) => ({
          layersVisible: { ...state.layersVisible, [layer]: visible },
        })),
      selectTrain: (id) => set({ selectedTrainId: id }),
      selectRestriction: (id) => set({ selectedRestrictionId: id }),
    }),
    {
      name: "infra-map-store",
      partialize: (state) => ({ layersVisible: state.layersVisible }),
    },
  ),
);

// hooks/useTrainPositions.ts
export function useTrainPositions(tiles: string[], businessTime: Date) {
  return useQuery({
    queryKey: ["trainpositions", tiles, businessTime.toISOString()],
    queryFn: async () => {
      const tilesWithVersions = tiles.map((id) => ({
        id,
        version: tileVersionCache.get(id),
      }));
      const res = await apiFetch("/trainpositions", {
        method: "POST",
        body: tilesWithVersions,
      });
      // Update version cache from response
      if (res.meta?.dataTileVersions) {
        Object.entries(res.meta.dataTileVersions).forEach(([id, v]) => {
          tileVersionCache.set(id, v);
        });
      }
      return res.data;
    },
    staleTime: 0, // Always re-fetch
    refetchInterval: 2000, // 2 sec polling
  });
}
```

---

# 9 — BACKEND SERVICES

## 9.1 Endpoints (Query Service, Port 8002)

### `GET /basegraph`

Returns the static infrastructure graph (paginated).

**Response:**

```json
{
  "data": [
    {
      "id": "bg-001",
      "nodes": [
        { "id": "n1", "x": 0, "y": 0, "name": "Station A" },
        { "id": "n2", "x": 10000, "y": 0, "name": "Junction 1" }
      ],
      "edges": [
        {
          "id": "e1",
          "fromNodeId": "n1",
          "toNodeId": "n2",
          "distance": 10000,
          "speed": 100
        }
      ]
    }
  ],
  "meta": { "page": { "pageNumber": 0, "totalPages": 1 } }
}
```

### `POST /trainpositions`

> Sections 10–11 (Caching & Optimization, Phase 10 Implementation Plan) are tracked
> separately in [plan.md](./plan.md) and [agent.md](./agent.md). The remainder of this
> document is a living brainstorm added after the Phase 10a live-browser review — see
> Section 12 below.

---

# 12 — BRAINSTORM: NEXT-GENERATION MAP ENHANCEMENTS (Post Phase 10a)

> **Context**: After Phase 10a shipped a working Maplibre map (base graph + trains +
> blocks + restrictions, HTTP-polling real-time updates, viewport persistence), a live
> review surfaced four gaps: (1) the demo network is a tiny, obviously-synthetic 5×4 grid
> that doesn't stress-test the visualization, (2) there is no way to create a block
> directly from the map, (3) data volume (40 nodes / 20 edges / 50 trains) is too small to
> validate clustering, tiling, and performance claims made in Section 5, and (4) there is
> no explicit test matrix for the map feature. This section brainstorms solutions to all
> four, grounded in [application_architecture_flow.md](./application_architecture_flow.md)
> Sections 17 (Shadow Finder), 19 (Track Dependency Analysis), 23 (Real-Time Event Flow),
> and 29.6 (GIS/Network Map Visualization).

## 12.1 Bigger, organically-random network topology

**Problem**: `db/seed.py` currently generates a deterministic 5×4 grid (40 junction
nodes, 20 edges, no stations, no branch lines, no loops). It looks like a test fixture,
not a railway network, and it can't exercise edge cases like dense junction clusters,
long single-track corridors, or disconnected sub-networks.

**Brainstormed approach — procedural network generator**:

1. **Backbone + branches generation algorithm** (new `db/network_gen.py`):
   - Generate a main corridor as a randomized walk of N "trunk" stations spaced with
     jittered distances (e.g. 8–25 km apart) instead of a fixed grid pitch.
   - Attach 3–6 branch lines off random trunk stations, each with its own random length
     (5–15 stations) and a random bearing (not orthogonal — use an angle jitter of
     ±35° off the branch's initial direction) so the shape looks organic, not grid-like.
   - Randomly add 2–4 **cross-links** (loop lines) connecting two otherwise-unconnected
     branches — this creates real Track Dependency Analysis scenarios (Section 19: "a
     block on one track may affect other tracks") because trains can be rerouted.
   - Insert junction nodes at every branch point and station nodes at terminal/mid-branch
     points; assign realistic `type` values (`station`, `junction`, `signal`) instead of
     making everything a junction.
   - Seed with a fixed RNG seed by default (reproducible for tests) but expose a
     `--seed` CLI flag and a `--randomize` flag for demo/story-telling runs.
2. **Scale target**: 300–800 nodes, 400–1000 edges (vs. current 40/20) — large enough to
   need clustering (Section 7.1 "trains" layer) and tile-based polling (Section 5) to
   actually matter, small enough to seed in a few seconds.
3. **Geometry realism**: avoid perfectly straight edges between nodes — generate 1–3
   intermediate waypoints per edge with small perpendicular jitter so rendered track
   lines have gentle curves (closer to real rail alignments), consumed by the existing
   `toLon`/`toLat` Cartesian→pseudo-lat/lng mapping already in `MapContainer.tsx`.
4. **Validation invariants** the generator must guarantee (so downstream services don't
   break): the graph is connected (no orphan sub-networks unless explicitly testing
   that), every edge references two existing nodes, no duplicate edge ids, and node ids
   are stable across re-seeds (needed for FK integrity in `Track`/`Block` tables).

### 12.1a Procedural curved track geometry — organic waypoint interpolation

**Motivation**: Real railway tracks are rarely perfectly straight over long distances —
they curve gently through valleys, around hills, and to follow existing right-of-ways.
The current `db/seed.py` produces Manhattan-grid straight edges that look synthetic on
the map. To make the network visually and geometrically convincing, track edges should
render as smooth curves with 2–4 intermediate waypoints per edge, not just straight
lines between nodes.

**Algorithm for generating curved track geometry**:

1. **For each edge** in the generated network (from node A to node B):
   - Compute the straight-line distance `d = distance(A, B)` and bearing `θ = bearing(A, B)`.
   - Divide the edge into `numSegments = max(2, ceil(d / 5000))` sub-segments (e.g. no
     segment longer than 5 km to maintain curve smoothness).
   - For each segment i ∈ [1, numSegments-1]:
     - Compute the segment's midpoint along the straight line.
     - Generate a perpendicular deflection: `deflection = random(-d*0.08, d*0.08)` (±8%
       of edge length, varying per run).
     - Perturb the midpoint perpendicular to the A→B bearing by `deflection` meters.
     - This becomes an **intermediate waypoint** that curves the track away from the
       straight line.
   - Store the sequence: [A, waypoint_1, waypoint_2, ..., waypoint_n, B].

2. **Rendering the curved edges**:
   - When inserting edge geometry into the Maplibre `sources.edges`, use the waypoint
     sequence (not just the two endpoints) as a LineString in the GeoJSON feature.
   - Maplibre will automatically render a polyline through all waypoints, producing a
     smooth, organic-looking curve.
   - Maplibre's line rendering can optionally enable line-join: "round" and line-cap:
     "round" for even smoother visual appeal.

3. **Parametrization for controlled realism**:
   - **Deflection magnitude** (`±d*0.08`): Controls how wiggly tracks are.
     - 0% → perfectly straight (current behavior, too synthetic).
     - 5–8% → gentle realistic curves (recommended for railway aesthetics).
     - 10%+ → exaggerated curves (OK for stylized/game-like aesthetic, but harder to read).
   - **Segment length** (5000 m): Shorter segments allow tighter curves; longer segments
     produce sweeping gentle curves. Tune based on zoom level and network scale.
   - **Randomness seed**: Use the edge ID as a component of the RNG seed (e.g.
     `seed = hash(edgeId) + masterSeed`) so waypoints are reproducible per edge but
     different from other edges.

4. **Database schema adjustment**:
   - The `Track` table's geometry column (currently storing just the two endpoints) should
     be extended to store the full waypoint sequence as a LineString or encoded polyline.
   - Alternatively, compute waypoints on-the-fly in `MapContainer.tsx` using the edge's
     `from`/`to` node IDs and a stored curve seed/deflection parameter.
   - Latency: pre-computing and storing is better (no render-time computation); on-the-fly
     is simpler if waypoint generation is deterministic and fast.

5. **Visual verification**:
   - Open the map in a real browser (not headless automation; see Section 12.5).
   - Pan to a high-zoom level where you can see individual edges clearly.
   - Verify that edges show as smooth curves, not straight lines.
   - Verify that trains (markers) follow the curved tracks when positioned at various
     points along the edges (e.g., by checking `map.querySourceFeatures()` for edge
     coordinates at train positions).

**Example deflection pattern** (pseudo-code):

```python
def generateCurvedEdgeGeometry(nodeA, nodeB, edgeId, masterSeed=12345):
    """Generate waypoints for a curved track between two nodes."""
    distance = euclidean(nodeA, nodeB)
    bearing = atan2(nodeB.y - nodeA.y, nodeB.x - nodeA.x)
    
    numSegments = max(2, ceil(distance / 5000))
    waypoints = [nodeA]
    
    edgeRng = Random(hash(edgeId) + masterSeed)
    
    for i in range(1, numSegments):
        t = i / numSegments  # parameter [0, 1]
        midpoint = lerp(nodeA, nodeB, t)  # linear interpolation
        
        # Perpendicular direction (rotated 90° from bearing)
        perpBearing = bearing + pi / 2
        
        # Random deflection magnitude: ±8% of total distance
        deflectionMagnitude = edgeRng.uniform(-0.08 * distance, 0.08 * distance)
        
        # Apply deflection perpendicular to the main bearing
        waypointX = midpoint.x + deflectionMagnitude * cos(perpBearing)
        waypointY = midpoint.y + deflectionMagnitude * sin(perpBearing)
        
        waypoints.append(Point(waypointX, waypointY))
    
    waypoints.append(nodeB)
    return waypoints  # LineString: [A, wp1, wp2, ..., B]
```

This approach ensures:
- **Deterministic reproducibility** — same edge ID + seed = same curve every time.
- **Visual realism** — gentle organic curves that look like real railway alignment.
- **Scalability** — fast O(segments) computation, no external geometry libraries required.
- **Integration** — works seamlessly with the existing Maplibre GeoJSON/LineString rendering.

## 12.2 "Live add blocks on map" — interactive block creation

**Problem**: Today a Block Request is only created via the `/requests` form. Section
29.6 asks for a GIS/network map that speeds up _understanding_; the brainstorm extends
that to _authoring_ — clicking directly on the map should let a planner draft a block.

**Brainstormed interaction flow**:

1. **Draw/select mode toggle** — a new map toolbar button ("Add Block") puts the map
   into "select track" mode: hovering an edge highlights it, clicking selects it (or
   shift-click to select a contiguous multi-edge corridor for a Corridor Block, Section
   29.1).
2. **Inline draft panel** — selecting track segment(s) opens a compact form docked to
   the map (not a full-page navigation): start/end time pickers (defaulting to the
   current business-clock time from `TimeControls.tsx`), reason/department dropdown,
   and a live-computed list of "affected resources" (reuses Track Dependency Analysis,
   Section 19) shown directly under the map as a preview before submit.
3. **Submit → Command Service** — on submit, `POST /block-requests` is called (existing
   Command Service endpoint) with `trackIds` derived from the selected edges' `trackId`
   field (already present on `BaseGraphEdge`); the map optimistically renders the new
   request as a dashed "planned/pending" overlay (reusing the existing `blocks-planned`
   layer style from Section 7.1) until the real event round-trips through Kafka →
   Optimization Service → Read Store (Section 21, Write Path) and the poller picks it up.
4. **Shadow Finder preview on the map itself** — while drafting, call a (new, read-only)
   `GET /shadow-finder/preview?trackIds=...&start=...&end=...` endpoint that runs the
   existing Shadow Finder logic (Section 17) against in-flight + approved requests and
   highlights any overlapping/mergeable existing block in a distinct color, with a
   tooltip explaining the potential merge — this turns an abstract backend concept into
   an immediate visual signal for the requester, before they even submit.
5. **Undo / cancel** — drafts are pure client-side state (Zustand `blockDraftStore`)
   until submit; canceling just clears the draft, no backend call needed.
6. **Permissions** — the "Add Block" toolbar button is gated by RBAC (Section 29.12):
   only roles allowed to create requests for the department scope of the selected track
   see the button enabled; others see it disabled with a tooltip explaining why.

## 12.3 Scaling data further

**Problem**: 50 trains / 99 schedules is too small to validate polling/tiling claims in
Section 5 and Section 6 ("Handles ~1000s of trains per tile" is asserted for RIVM but
never actually tested against Team-Waypoints).

**Brainstormed scale-up plan**:

1. Bump seed data to **500–2,000 trains** and **5,000+ schedules**, distributed
   unevenly across the new bigger network (busier trunk corridor, sparser branches) so
   clustering (Section 7.1 `trains` layer, `ClusterRadius: 50px`) is actually exercised
   at normal zoom levels, not just when zoomed far out.
2. Add **synthetic delay/restriction noise**: randomly assign 5–10% of trains a delay
   offset and randomly generate 10–30 active restrictions (Section 7.1 `restrictions`
   layer) spread across the network so the map is never "too clean" — mirrors the event
   injection work already done in Phase 11.
3. **Load-test the polling loop** (Section 6.1) once data is scaled: measure `/trainpositions`
   tile response time and payload size at 500/1000/2000 trains, and confirm Redis
   cache-aside (Section 9) keeps p95 latency low; document actual numbers in this file
   (replacing the currently-unverified "~200ms" RIVM comparison figure in Section 2.1).
4. Keep seed generation idempotent and parameterized (`--trains=2000 --nodes=500`) so
   CI/dev can still use a small fast dataset while demo/perf environments use the large one.

## 12.4 Test-case coverage brainstorm

A consolidated matrix to close testing gaps discovered during the Phase 10a live-browser
session (see [agent.md](./agent.md) for the specific hydration/viewport/StrictMode bugs
found and fixed):

| Area                           | Test case                                                                                                                                           | Why it matters                                                                                                                                 |
| ------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| **Rendering lifecycle**        | Map renders base graph + trains on first load with no persisted `localStorage` state                                                                | Covers the "fresh user" path                                                                                                                   |
|                                | Map recovers when persisted viewport is out-of-bounds/stale (Section 8 `mapStore`)                                                                  | Regression test for the exact bug found this session                                                                                           |
|                                | Map survives a hydration-mismatch-triggering child update (e.g. a live clock) without losing the WebGL canvas                                       | Regression test for the `next/dynamic({ssr:false})` fix                                                                                        |
|                                | Map init effect is resilient to React StrictMode double-invoke (mount→cleanup→mount) in dev                                                         | Prevents "blank map in dev only" bugs from recurring                                                                                           |
| **Network topology**           | Generated network is fully connected (no orphan islands) at every random seed                                                                       | Guarantees routing/dependency analysis has a valid graph                                                                                       |
|                                | Edge `trackId` values are unique/stable across re-seeds                                                                                             | FK integrity with `Track`/`Block` tables                                                                                                       |
|                                | Rendering 800 nodes / 1000 edges stays interactive (pan/zoom) at 30+ fps                                                                            | Perf budget for the "bigger network" goal                                                                                                      |
| **Trains & clustering**        | Trains cluster correctly at low zoom and un-cluster at high zoom without duplicate icons                                                            | Core Section 7.1 behavior                                                                                                                      |
|                                | Time-travel slider (`TimeControls.tsx`) correctly filters trains via `filterByTime` at boundary timestamps (exactly at start/end)                   | Off-by-one bugs are easy here                                                                                                                  |
|                                | Polling tile diffing (Section 5) sends unchanged-tile version and receives empty response, not full re-fetch                                        | Validates the whole tiling strategy actually saves bandwidth                                                                                   |
| **Live block creation (12.2)** | Selecting a multi-edge corridor produces a single Corridor Block request (Section 29.1), not N separate ones                                        | Correctness of the new authoring flow                                                                                                          |
|                                | Shadow Finder preview correctly flags an overlapping existing block before submit                                                                   | Validates Section 17 integration                                                                                                               |
|                                | Draft state is discarded on cancel/navigate-away with no backend side effects                                                                       | No orphaned partial requests                                                                                                                   |
|                                | RBAC-disabled users cannot submit even via direct API call (server-side check, not just UI-disabled button)                                         | OWASP: never trust client-side authorization alone                                                                                             |
| **Real-time & events**         | A `track.status_*` Kafka event (Section 23) updates the map's restriction layer within one polling interval                                         | Validates the real-time adaptive loop end-to-end                                                                                               |
|                                | Map does not flicker/reset viewport when new data arrives mid-pan                                                                                   | UX regression class                                                                                                                            |
| **Resilience**                 | Map still renders base graph if `/trainpositions` fails (graceful degradation)                                                                      | Backend/network fault tolerance                                                                                                                |
|                                | Map still renders if the external glyphs URL (Section 3.2) is unreachable — labels degrade, layout doesn't break                                    | Matches the 404-on-glyphs behavior already observed                                                                                            |
| **Accessibility/testability**  | Map container and controls are reachable via keyboard and have appropriate ARIA labels                                                              | A11y baseline                                                                                                                                  |
|                                | Canvas-based rendering is verifiable in automated tests via `map.isStyleLoaded()`/`loaded()` + screenshot diffing, not accessibility-tree snapshots | Canvas elements are invisible to a11y-tree tools (confirmed this session); document the correct verification technique for future contributors |

## 12.5 Known environment caveat (documented for future contributors)

During this session's live-browser verification, the map appeared completely blank in
the automated Playwright browser used for testing. Root-causing traced this to the test
harness's browser tab running with `document.visibilityState === "hidden"` permanently
(confirmed via `requestAnimationFrame` never firing even after `page.bringToFront()`),
which starves MapLibre GL's internal render loop — `'load'` never fires, independent of
any application code. **This is a limitation of headless/backgrounded browser automation,
not an application bug.** Two genuine bugs _were_ found and fixed along the way:

1. A hydration mismatch (`TimeControls`'s live clock rendering different text on server
   vs. client) was discarding/remounting the map's DOM subtree post-hydration — fixed by
   loading `MapContainer` via `next/dynamic({ ssr: false })` instead of `<Suspense>`.
2. A stale/out-of-bounds persisted viewport in `localStorage['map-store']` could strand
   the camera outside the network's bounding box with no visual explanation — fixed with
   a `resetViewport()` action, an auto-heal check in the `'load'` handler, and a manual
   "Fit Network" button.

Future live-browser verification of the map should use a real, focused desktop browser
window (not an automated/headless tab) to confirm visual rendering, and can additionally
assert `map.isStyleLoaded() === true` and `map.loaded() === true` programmatically as a
secondary, environment-independent signal.

Returns train positions for the given tiles (with versioning).

**Request:**

```json
[
  { "id": "125000_-10000_2026-08-31T09:15", "version": "8f1c...uuid" },
  { "id": "130000_-10000_2026-08-31T09:15" }
]
```

**Response:**

```json
{
  "data": [
    {
      "id": "train-pos-001",
      "trainServiceId": "T2843",
      "x": 127500,
      "y": -5000,
      "fromTime": "2026-08-31T09:15:00Z",
      "toTime": "2026-08-31T09:30:00Z",
      "dataTileIds": ["125000_-10000_2026-08-31T09:15"],
      "trackId": "T-A-01",
      "platformTrackId": "P-A-01"
    }
  ],
  "meta": {
    "dataTileVersions": {
      "125000_-10000_2026-08-31T09:15": "a2d3...uuid"
    }
  }
}
```

### `GET /blocks`

Returns blocks (derived from train positions). Filterable by `planId`, `trackId`, `status`.

### `GET /restrictions`

Returns active restrictions at a given time (`?effectiveAt=<ISO>`).

### `GET /business-clock`

Returns current business clock (mode, time, timezone).

---

# 10 — CACHING & OPTIMIZATION

## 10.1 Redis cache (Query Service)

```python
# cache_key(resource, filters) -> str
BASEGRAPH_KEY = "basegraph:v1"  # TTL: 3600 sec (1 hour)
TRAINPOS_KEY = f"trainpos:tile:{tile_id}"  # TTL: 10 sec
RESTRICTIONS_KEY = f"restrictions:time:{effective_at}"  # TTL: 30 sec
BUSINESS_CLOCK_KEY = "business_clock:current"  # TTL: 5 sec
```

**Rationale:**

- Base graph is mostly static → long TTL.
- Train positions change frequently → short TTL.
- Restrictions change less → medium TTL.
- Business clock may jump (controlled mode) → refresh often.

## 10.2 IndexedDB (frontend, Dexie)

```typescript
// db/infra-db.ts
const db = new Dexie("TEAM_WAYPOINTS_INFRA");
db.version(1).stores({
  baseGraph: "&id",
  mapConfig: "&id",
  locationTrackCoordinates: "&id",
  filterState: "&key",
});

// On bootstrap:
// 1. Try IndexedDB first; if miss → fetch from API
// 2. Cache the response in IndexedDB
// 3. On every subsequent reload, use cached data (unless explicitly invalidated)
```

Benefits:

- Faster map load (no HTTP round-trip for static data).
- Works offline (view only).
- Survives browser restart.

---

# 11 — PHASE 10 IMPLEMENTATION PLAN

## 11.1 Phase 10a — Core Map Visualization (MVP)

| Task                                                                                         | Effort                | Owner    | Dependencies         |
| -------------------------------------------------------------------------------------------- | --------------------- | -------- | -------------------- |
| **10a.1** Evaluate & install Maplibre GL + React bindings (`react-map-gl` or custom wrapper) | 1 day                 | Frontend | Phase 9C complete    |
| **10a.2** Render base graph (nodes, edges) from `GET /basegraph`                             | 1 day                 | Frontend | 10a.1                |
| **10a.3** Implement 3D tile computation + polling loop                                       | 2 days                | Frontend | 10a.2                |
| **10a.4** Render train positions on map (static test data first, then live)                  | 1 day                 | Frontend | 10a.3                |
| **10a.5** Add time-offset slider + date/time picker (no business-clock backend yet)          | 1 day                 | Frontend | 10a.4                |
| **10a.6** Implement train selection & detail panel integration                               | 1 day                 | Frontend | 10a.5, Phase 9C      |
| **10a.7** Add layer visibility toggles (trains, restrictions, labels) to Ribbon              | 1 day                 | Frontend | 10a.5                |
| **10a.8** Backend: Implement `POST /trainpositions` with tile versioning                     | 2 days                | Backend  | Phase 6 (Read Store) |
| **10a.9** Backend: Implement tile version tracking in Read Store ETL                         | 1 day                 | Backend  | 10a.8                |
| **10a.10** Integration testing: E2E tile polling + map update                                | 1 day                 | QA       | 10a.9                |
|                                                                                              | **11 days** (2 weeks) |          |                      |

**Output**: Functional map with real-time train visualization, time-travel slider, and tile caching.

---

## 11.2 Phase 10b — Advanced Features (future)

| Task                                                   | Effort      | Dependencies                                |
| ------------------------------------------------------ | ----------- | ------------------------------------------- |
| WebSocket upgrade (replace polling with streaming)     | 2 days      | 10a complete                                |
| Block occupancy rendering (color-coded track segments) | 1 day       | 10a complete                                |
| Restriction overlays (speed, blockage icons)           | 2 days      | 10a complete + Phase 12 (Restrictions CRUD) |
| Collision-avoiding train label placement               | 3 days      | 10a.4                                       |
| Playback controls (animate train movement over time)   | 2 days      | 10a.5                                       |
| **Total**                                              | **10 days** |                                             |

---

## 11.3 Phase 10c — Optimization & Polish (future)

- Worker thread for tile computation (offload from main thread).
- Tile pre-fetching (load adjacent tiles for smooth panning).
- Mobile responsiveness (sidebar → drawer, touch interactions).
- Accessibility audit (keyboard nav, screen reader support).

---

# 12 — MIGRATION GUIDE: CURRENT ARCHITECTURE → MAP ARCHITECTURE

## Current State (Phase 9C)

- Dashboard: KPI cards + data tables.
- No map.
- Polling: fetch-based per route (10s staleness).
- State: TanStack Query + React hooks.

## Transition Steps

1. **Phase 10a**: Add map page (`/infrastructure/map` or `/maps/main`) alongside existing dashboard. No changes to dashboard or existing routes.
2. **Phase 10b**: Gradually migrate train/block/restriction views to map-centric (allow both dashboard table + map).
3. **Phase 10c** (future): Retire table-based views in favor of map-only (if desired).

---

## Appendix A: Reference Architecture Comparison

| Feature                 | RIVM INFRA                                          | Team-Waypoints (Proposed)                                   |
| ----------------------- | --------------------------------------------------- | ----------------------------------------------------------- |
| **Map engine**          | OpenLayers 10                                       | Maplibre GL JS                                              |
| **State**               | NgRx (classic + signals)                            | TanStack Query + Zustand                                    |
| **Caching**             | IndexedDB + localStorage                            | IndexedDB (Dexie) + localStorage                            |
| **Real-time**           | RabbitMQ (backend) + HTTP polling (frontend, 2 sec) | HTTP polling (2 sec, 10 sec for restrictions)               |
| **Tile versioning**     | UUID per tile                                       | UUID per tile                                               |
| **Time-travel**         | Business clock (REALTIME / CONTROLLED) + slider     | Custom time + offset slider                                 |
| **Coordination system** | Cartesian (microscopically accurate)                | Cartesian (schematic, simplified)                           |
| **Scale**               | 1000s of trains                                     | 100s of trains (one corridor)                               |
| **Complexity**          | Very high                                           | Medium (simpler scope)                                      |
| **Deployment**          | Kubernetes + Helm                                   | Docker Compose (local), potentially Kubernetes (production) |
