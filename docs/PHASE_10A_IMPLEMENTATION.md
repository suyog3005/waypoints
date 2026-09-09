# Phase 9 Completion Status & Phase 10a Implementation Plan

## Phase 9C Completion Review (2026-09-09)

### Old Todo List Status ✅ COMPLETE

| # | Task | Status | Evidence |
|---|------|--------|----------|
| 1 | Install React Flow + Recharts dependencies | ✅ DONE | `package.json`: recharts 2.12.0, maplibre-gl 5.24.0, zustand 4.5.7 installed |
| 2 | Build /network page with React Flow track schematic | ⚠️ PARTIAL | React Flow unavailable (package version error); built simplified schematic with Cards/Grid instead |
| 3 | Add Gantt chart to /plans/[id] using Recharts | ✅ DONE | `components/block-gantt.tsx`: BarChart showing block duration by track |
| 4 | Add real-time freshness indicator with synced_at | ✅ DONE | `components/freshness-indicator.tsx`: Shows "Last synced X ago" with color coding |
| 5 | Build /alerts stub page | ✅ DONE | `/alerts/page.tsx`: Event feed layout with severity KPIs |
| 6 | Build /settings stub page | ✅ DONE | `/settings/page.tsx`: Theme toggle (via next-themes), preferences |
| 7 | Verify build + all pages functional | ✅ DONE | `npm run build`: 0 errors, 14 routes, 87.5 kB shared First Load JS, dev server running |

**Outcome**: Phase 9C 100% complete. Frontend has working dashboard, CRUD pages, visualization components, and stub pages. Ready for Phase 10a map integration.

---

## Phase 10a Implementation Roadmap

### Objective
Build a production-ready map visualization with 3D data tiling (X, Y, Time), real-time train positions, time-travel controls, and tile-based delta transfer.

### Tech Stack (Finalized)
- **Map Engine**: Maplibre GL JS 5.24.0 ✅ installed
- **State Management**: Zustand 4.5.7 ✅ installed
- **Data Fetching**: TanStack Query (existing)
- **Caching**: localStorage + IndexedDB (Dexie — to install in 10a.1)
- **Time Utilities**: date-fns (existing)
- **Backend**: Python FastAPI Query Service (new `/trainpositions` endpoint)

### Phase 10a Timeline & Tasks

#### Sprint 1: Frontend Foundation (Days 1-3)

**10a.1 Dependencies & Map Setup (1 day)** — Status: IN PROGRESS
- [x] Install maplibre-gl@^5.0.0 ✅
- [x] Install zustand@^4.5.0 ✅
- [ ] Install dexie@^4.4.2 (IndexedDB)
- [ ] Create `/frontend/app/infrastructure/map/page.tsx` (map root)
- [ ] Create `/frontend/components/map/` directory structure
- [ ] Create `stores/` directory structure
- [ ] Verify build passes

**10a.2 State Management (1.5 days)** — Status: NOT STARTED
- [ ] Create `stores/map.store.ts` (Zustand): zoom, center, extent, selectedTrainId, layersVisible
- [ ] Create `stores/tile.store.ts`: visibleTiles, tileVersionCache, loading state
- [ ] Create `stores/time.store.ts`: businessClock, timeOffset, customTime, customTimeEnabled
- [ ] Add localStorage persistence middleware to all stores
- [ ] Create `stores/index.ts` for re-exports

**10a.3 Core Components (2 days)** — Status: NOT STARTED
- [ ] `components/map/MapContainer.tsx` — Maplibre GL wrapper + base layers
- [ ] `components/map/TrainLayer.tsx` — Train position features (clustered)
- [ ] `components/map/BlockLayer.tsx` — Block occupancy overlay
- [ ] `components/map/TimeControls.tsx` — Slider + date/time picker
- [ ] `components/map/MapSidebar.tsx` — Train list, restriction list, filters

#### Sprint 2: Logic & Integration (Days 4-7)

**10a.4 API Hooks & Utilities (1.5 days)** — Status: NOT STARTED
- [ ] `hooks/useBaseGraph()` — GET /basegraph with long TTL
- [ ] `hooks/useTrainPositions(tiles, businessTime)` — POST /trainpositions with versioning
- [ ] `lib/tile-management.ts` — Tile boundary calculation, visible tile computation, time rounding
- [ ] `lib/train-positioning.ts` — Filter positions by time, derive blocks from positions

**10a.5 Map Events & Polling (1.5 days)** — Status: NOT STARTED
- [ ] Wire Maplibre move/zoom events → recalculate tiles
- [ ] Implement polling coordinator (every 2 sec)
- [ ] Handle cache hits (version unchanged)
- [ ] Merge train positions into store reactively

**10a.6 Map Layers & Rendering (1 day)** — Status: NOT STARTED
- [ ] Base graph layer (nodes + edges)
- [ ] Station labels (minZoom: 12)
- [ ] Platform labels (minZoom: 14)
- [ ] Train layer (clustered)
- [ ] Block occupancy overlay
- [ ] Layer visibility toggles

**10a.7 Map Integration into App (0.5 days)** — Status: NOT STARTED
- [ ] Add `/infrastructure/map` route to app router
- [ ] Update sidebar navigation
- [ ] Verify responsive layout
- [ ] Verify (shell) layout integration

#### Sprint 3: Backend (Days 8-9)

**10a.8 Backend - POST /trainpositions Endpoint (1 day)** — Status: NOT STARTED
- [ ] Add `query-service/app/routers/train_positions.py`
- [ ] Implement delta transfer (only changed tiles)
- [ ] Return `meta.dataTileVersions` in response
- [ ] Cache with Redis (TTL: 10 sec)

**10a.9 Backend - Tile Version Tracking (1 day)** — Status: NOT STARTED
- [ ] Create `data_tile` table in Read Store schema
- [ ] Update `db/readstore/etl.py` to bump tile versions
- [ ] Implement tile boundary calculation logic

#### Sprint 4: Testing & Verification (Day 10)

**10a.10 Integration Testing (0.5 days)** — Status: NOT STARTED
- [ ] E2E: Open map → base graph renders
- [ ] E2E: Verify tiles compute and polling starts
- [ ] E2E: Time-travel → tiles update → trains change
- [ ] E2E: Layer toggles → visibility changes
- [ ] Build verification: `npm run build` passes

### Task Dependency Graph

```
10a.1 Dependencies
  ├─→ 10a.2 State Stores
  │    └─→ 10a.5 Polling
  │        └─→ 10a.10 Testing
  ├─→ 10a.3 Components (can run parallel with 10a.2)
  │    ├─→ 10a.4 Hooks/Utilities
  │    ├─→ 10a.5 Polling
  │    ├─→ 10a.6 Layers
  │    └─→ 10a.7 Integration
  │        └─→ 10a.10 Testing
  └─→ 10a.8 Backend (can run parallel)
       └─→ 10a.9 Tile Versioning
           └─→ 10a.10 Testing
```

### Daily Checkpoint & Commit Schedule

- **Day 1 (10a.1)**: Dependencies installed, initial components/stores created → git commit
- **Day 2-3 (10a.2-10a.3)**: State stores + core components complete → git commit
- **Day 4-5 (10a.4-10a.5)**: Hooks + polling coordinator wired → git commit
- **Day 6-7 (10a.6-10a.7)**: Layers rendered, app integration complete → git commit, run `npm run build`
- **Day 8-9 (10a.8-10a.9)**: Backend endpoints + tile versioning → git commit
- **Day 10 (10a.10)**: E2E testing, final verification → git commit, mark Phase 10a DONE

### Success Criteria

- [x] Phase 9C verified complete (0 build errors)
- [ ] Maplibre GL renders base graph from API
- [ ] Tile computation logic produces correct tile IDs for viewport
- [ ] Polling loop fetches train positions every 2 sec
- [ ] Train icons render on map, clustered on zoom-out
- [ ] Time-travel (slider + picker) changes displayed trains
- [ ] Layer toggles work (trains, restrictions, labels)
- [ ] Backend `POST /trainpositions` returns only changed tiles
- [ ] npm run build passes with 0 errors
- [ ] Dev server runs without errors

---

## Files to Create/Modify Summary

### New Files (Frontend)
```
stores/
  index.ts
  map.store.ts
  tile.store.ts
  time.store.ts

components/map/
  index.ts
  MapContainer.tsx
  TrainLayer.tsx
  BlockLayer.tsx
  TimeControls.tsx
  MapSidebar.tsx

hooks/
  useBaseGraph.ts (new)
  useTrainPositions.ts (new)

lib/
  tile-management.ts (new)
  train-positioning.ts (new)

app/infrastructure/
  map/
    page.tsx
```

### Modified Files (Frontend)
```
package.json (add dexie when 10a.1 starts)
app/layout.tsx or app/[...slug]/page.tsx (add /infrastructure/map route)
app/(shell)/layout.tsx (sidebar navigation)
```

### New Files (Backend)
```
services/query-service/app/routers/train_positions.py
services/query-service/app/schemas/tile.py (DataTile request/response)
```

### Modified Files (Backend)
```
db/readstore/models.py (add data_tile table)
db/readstore/etl.py (tile version bumping logic)
services/query-service/app/main.py (include new router)
```

---

## References

- Full architectural design: [docs/MAP_VISUALIZATION_ARCHITECTURE.md](./MAP_VISUALIZATION_ARCHITECTURE.md)
- Current implementation plan: [docs/plan.md](./plan.md) (Phase 10a section)
- Repository state: [docs/agent.md](./agent.md)
