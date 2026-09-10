/**
 * OPUS-5 Part K — The Map: data model + geometry.
 *
 * A single deterministic network (stations, parallel lines, blocks in every
 * semantic state, trains, restrictions, conflicts, traction sections, assets)
 * is defined once and projected into the three view modes (K1):
 *
 *   - geographic : true coordinates with real curvature
 *   - schematic  : straightened, evenly-spaced line diagram
 *   - linear     : one section as a horizontal chainage strip, lines stacked
 *
 * All three are projections of the SAME objects (K1 critical requirement).
 *
 * Geometry is DETERMINISTIC (K3/K10): the same segment looks identical to
 * every user, every session. Rendered geometry is NEVER used for distance —
 * chainage (km) is the source of truth.
 */

// ── Seeded PRNG (deterministic "random" data) ──────────────────────────
function hashSeed(str: string): number {
  let h = 1779033703 ^ str.length;
  for (let i = 0; i < str.length; i++) {
    h = Math.imul(h ^ str.charCodeAt(i), 3432918353);
    h = (h << 13) | (h >>> 19);
  }
  return h >>> 0;
}
function mulberry32(seed: number) {
  let a = seed;
  return function () {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const rng = mulberry32(hashSeed("DLI-corridor-v1"));
const between = (min: number, max: number) => min + rng() * (max - min);
const intBetween = (min: number, max: number) => Math.floor(between(min, max + 1));
const pick = <T,>(arr: T[]): T => arr[Math.floor(rng() * arr.length)];

// ── View modes (K1) ────────────────────────────────────────────────────
export type ViewMode = "geographic" | "schematic" | "linear";

// ── Corridor definition ────────────────────────────────────────────────
export const KM_MIN = 408;
export const KM_MAX = 420;

/**
 * Real-alignment curvature for geographic mode (K3). A smooth bend so the
 * line does not look like a straight schematic pretending to be geography.
 * Returns a perpendicular deflection in meters for a given chainage.
 */
function curve(km: number): number {
  const t = (km - KM_MIN) / (KM_MAX - KM_MIN);
  // A gentle S-curve: rises then falls, a few % of the corridor length.
  return Math.sin(t * Math.PI) * 900 + Math.sin(t * Math.PI * 2.3) * 250;
}

export interface Pt {
  x: number;
  y: number;
}

/**
 * Project a (chainage km, perpendicular offset m) into screen meters for a
 * given view mode. This is the single source of truth for all geometry.
 */
export function project(km: number, offset: number, mode: ViewMode, lineIndex = 0): Pt {
  const x = (km - KM_MIN) * 1000; // 1 km = 1000 m along the corridor
  switch (mode) {
    case "geographic":
      return { x, y: curve(km) + offset };
    case "schematic":
      // Straightened: no curvature, lines keep their perpendicular offset.
      return { x, y: offset };
    case "linear":
      // Chainage strip: lines stacked vertically, evenly spaced, no curvature.
      return { x, y: lineIndex * 120 };
  }
}

/** Sample a line's polyline between two chainages for a view mode. */
export function linePolyline(
  fromKm: number,
  toKm: number,
  offset: number,
  mode: ViewMode,
  lineIndex: number,
  steps = 24,
): Pt[] {
  const pts: Pt[] = [];
  for (let i = 0; i <= steps; i++) {
    const km = fromKm + ((toKm - fromKm) * i) / steps;
    pts.push(project(km, offset, mode, lineIndex));
  }
  return pts;
}

// ── Network entities ───────────────────────────────────────────────────
export interface Station {
  id: string;
  name: string;
  km: number;
}

export interface Line {
  id: string;
  name: string;
  direction: "UP" | "DN";
  offset: number; // perpendicular offset (m)
  index: number; // stacking index for linear mode
  color: string;
}

export type BlockState =
  | "active"
  | "granted"
  | "approved"
  | "requested"
  | "proposed"
  | "emergency"
  | "derived"
  | "electrically_dead";

export interface Block {
  id: string;
  lineId: string;
  fromKm: number;
  toKm: number;
  state: BlockState;
  window: string; // e.g. "01:00–06:35"
  progress: number; // 0-100
  bundle?: string;
  note?: string;
}

export interface Train {
  id: string;
  number: string;
  type: "passenger" | "freight";
  km: number;
  lineId: string;
  speed: number;
  delayed: boolean;
  delayMin: number;
  inferred: boolean; // hollow = position inferred, not live
}

export interface Restriction {
  id: string;
  lineId: string;
  fromKm: number;
  toKm: number;
  speed: number;
  permanent: boolean;
  overdue: boolean;
}

export interface Conflict {
  id: string;
  km: number;
  lineId: string;
  a: string;
  b: string;
}

export interface TractionSection {
  id: string;
  fromKm: number;
  toKm: number;
  state: "energised" | "isolated" | "earthed";
}

export interface Asset {
  id: string;
  km: number;
  lineId: string;
  kind: string;
  condition: "good" | "watch" | "defective" | "failed";
}

// ── Stations ───────────────────────────────────────────────────────────
export const STATIONS: Station[] = [
  { id: "DLI", name: "DLI", km: 408.0 },
  { id: "SBB", name: "SBB", km: 411.0 },
  { id: "JN12", name: "JN12", km: 413.0 },
  { id: "GZB", name: "GZB", km: 414.5 },
  { id: "MUT", name: "MUT", km: 418.0 },
];

// ── Lines (parallel, K3 consistent perpendicular offset) ───────────────
export const LINES: Line[] = [
  { id: "up-main", name: "UP Main", direction: "UP", offset: 0, index: 0, color: "#64748b" },
  { id: "dn-main", name: "DN Main", direction: "DN", offset: -28, index: 1, color: "#64748b" },
  { id: "up-loop", name: "UP Loop", direction: "UP", offset: 28, index: 2, color: "#94a3b8" },
  { id: "siding", name: "Sidings", direction: "UP", offset: 58, index: 3, color: "#cbd5e1" },
];

const lineById = (id: string) => LINES.find((l) => l.id === id)!;

// ── Blocks (every semantic state, K4) ─────────────────────────────────
export const BLOCKS: Block[] = [
  { id: "B-2291", lineId: "up-main", fromKm: 412.1, toKm: 413.5, state: "active", window: "01:00–06:35", progress: 68, bundle: "D-1041+D-1043+D-1047", note: "through packing" },
  { id: "B-2288", lineId: "dn-main", fromKm: 409.0, toKm: 410.2, state: "granted", window: "02:00–05:00", progress: 40, note: "OHE inspection" },
  { id: "B-2295", lineId: "up-main", fromKm: 415.0, toKm: 416.2, state: "approved", window: "14:30–18:00", progress: 0, note: "axle counter" },
  { id: "B-2301", lineId: "up-loop", fromKm: 413.2, toKm: 414.0, state: "requested", window: "16:00–20:00", progress: 0, note: "ballast cleaning" },
  { id: "B-2304", lineId: "dn-main", fromKm: 416.5, toKm: 417.4, state: "proposed", window: "22:00–02:00", progress: 0, note: "optimiser option C" },
  { id: "E-0034", lineId: "up-main", fromKm: 415.0, toKm: 415.4, state: "emergency", window: "now", progress: 30, note: "rail fracture" },
  { id: "D-1052", lineId: "up-loop", fromKm: 415.0, toKm: 415.8, state: "derived", window: "—", progress: 0, note: "stranded via CO/14" },
  { id: "E-7", lineId: "up-main", fromKm: 412.0, toKm: 414.5, state: "electrically_dead", window: "—", progress: 0, note: "OHE isolation E-7" },
  // Extra random blocks to fill the corridor (deterministic).
  ...Array.from({ length: 6 }).map((_, i) => {
    const from = between(408.5, 417);
    const to = from + between(0.3, 1.2);
    const states: BlockState[] = ["approved", "requested", "proposed", "granted"];
    return {
      id: `B-${2310 + i}`,
      lineId: pick(LINES).id,
      fromKm: Math.round(from * 10) / 10,
      toKm: Math.round(to * 10) / 10,
      state: pick(states),
      window: `${intBetween(0, 23).toString().padStart(2, "0")}:00–${intBetween(0, 23).toString().padStart(2, "0")}:00`,
      progress: 0,
      note: pick(["OHE", "S&T", "Engg", "Project"]),
    };
  }),
];

// ── Trains (K5) ────────────────────────────────────────────────────────
export const TRAINS: Train[] = Array.from({ length: 26 }).map((_, i) => {
  const type: "passenger" | "freight" = rng() > 0.4 ? "passenger" : "freight";
  const delayed = rng() > 0.7;
  return {
    id: `trn-${i}`,
    number: type === "passenger" ? `${12000 + intBetween(0, 999)}` : `GDS-${4000 + intBetween(0, 999)}`,
    type,
    km: Math.round(between(KM_MIN + 0.3, KM_MAX - 0.3) * 100) / 100,
    lineId: pick(LINES.slice(0, 3)).id,
    speed: intBetween(30, 110),
    delayed,
    delayMin: delayed ? intBetween(5, 45) : 0,
    inferred: rng() > 0.75,
  };
});

// ── Restrictions (K4.1 / K2 z=40) ──────────────────────────────────────
export const RESTRICTIONS: Restriction[] = Array.from({ length: 8 }).map((_, i) => {
  const from = between(KM_MIN + 0.5, KM_MAX - 1);
  return {
    id: `R-${100 + i}`,
    lineId: pick(LINES.slice(0, 3)).id,
    fromKm: Math.round(from * 10) / 10,
    toKm: Math.round((from + between(0.3, 1.5)) * 10) / 10,
    speed: pick([20, 30, 40, 50, 60]),
    permanent: rng() > 0.6,
    overdue: rng() > 0.7,
  };
});

// ── Conflicts (K7) ─────────────────────────────────────────────────────
export const CONFLICTS: Conflict[] = [
  { id: "C-1", km: 415.2, lineId: "up-main", a: "B-2295", b: "E-0034" },
  { id: "C-2", km: 413.4, lineId: "up-loop", a: "B-2301", b: "D-1052" },
];

// ── Traction elementary sections (K8) ──────────────────────────────────
export const TRACTION: TractionSection[] = [
  { id: "E-5", fromKm: 408.0, toKm: 411.0, state: "energised" },
  { id: "E-6", fromKm: 411.0, toKm: 412.0, state: "energised" },
  { id: "E-7", fromKm: 412.0, toKm: 414.5, state: "earthed" },
  { id: "E-8", fromKm: 414.5, toKm: 418.0, state: "isolated" },
];

// ── Assets (K2 z=30) ───────────────────────────────────────────────────
export const ASSETS: Asset[] = Array.from({ length: 40 }).map((_, i) => ({
  id: `A-${1000 + i}`,
  km: Math.round(between(KM_MIN + 0.2, KM_MAX - 0.2) * 100) / 100,
  lineId: pick(LINES).id,
  kind: pick(["bridge", "tunnel", "level crossing", "neutral section", "signal"]),
  condition: pick(["good", "good", "watch", "defective", "failed"]),
}));

// ── GeoJSON builders (per view mode) ───────────────────────────────────
const M = 1 / 111_320;
const toLon = (x: number) => x * M;
const toLat = (y: number) => y * M;

type FC = { type: "FeatureCollection"; features: any[] };

export function linesGeoJSON(mode: ViewMode): FC {
  return {
    type: "FeatureCollection",
    features: LINES.map((l) => ({
      type: "Feature",
      properties: { id: l.id, name: l.name, direction: l.direction, color: l.color },
      geometry: {
        type: "LineString",
        coordinates: linePolyline(KM_MIN, KM_MAX, l.offset, mode, l.index).map((p) => [toLon(p.x), toLat(p.y)]),
      },
    })),
  };
}

export function stationsGeoJSON(mode: ViewMode): FC {
  return {
    type: "FeatureCollection",
    features: STATIONS.map((s) => {
      const p = project(s.km, 0, mode, 0);
      return {
        type: "Feature",
        properties: { id: s.id, name: s.name, km: s.km },
        geometry: { type: "Point", coordinates: [toLon(p.x), toLat(p.y)] },
      };
    }),
  };
}

export function blocksGeoJSON(mode: ViewMode): FC {
  return {
    type: "FeatureCollection",
    features: BLOCKS.map((b) => {
      const l = lineById(b.lineId);
      return {
        type: "Feature",
        properties: {
          id: b.id,
          state: b.state,
          lineId: b.lineId,
          lineName: l.name,
          fromKm: b.fromKm,
          toKm: b.toKm,
          window: b.window,
          progress: b.progress,
          bundle: b.bundle ?? "",
          note: b.note ?? "",
        },
        geometry: {
          type: "LineString",
          coordinates: linePolyline(b.fromKm, b.toKm, l.offset, mode, l.index).map((p) => [toLon(p.x), toLat(p.y)]),
        },
      };
    }),
  };
}

export function trainsGeoJSON(mode: ViewMode): FC {
  return {
    type: "FeatureCollection",
    features: TRAINS.map((t) => {
      const l = lineById(t.lineId);
      const p = project(t.km, l.offset, mode, l.index);
      return {
        type: "Feature",
        properties: {
          id: t.id,
          number: t.number,
          type: t.type,
          speed: t.speed,
          delayed: t.delayed,
          delayMin: t.delayMin,
          inferred: t.inferred,
          km: t.km,
          lineName: l.name,
        },
        geometry: { type: "Point", coordinates: [toLon(p.x), toLat(p.y)] },
      };
    }),
  };
}

export function restrictionsGeoJSON(mode: ViewMode): FC {
  return {
    type: "FeatureCollection",
    features: RESTRICTIONS.map((r) => {
      const l = lineById(r.lineId);
      return {
        type: "Feature",
        properties: { id: r.id, speed: r.speed, permanent: r.permanent, overdue: r.overdue, lineName: l.name },
        geometry: {
          type: "LineString",
          coordinates: linePolyline(r.fromKm, r.toKm, l.offset, mode, l.index).map((p) => [toLon(p.x), toLat(p.y)]),
        },
      };
    }),
  };
}

export function conflictsGeoJSON(mode: ViewMode): FC {
  return {
    type: "FeatureCollection",
    features: CONFLICTS.map((c) => {
      const l = lineById(c.lineId);
      const p = project(c.km, l.offset, mode, l.index);
      return {
        type: "Feature",
        properties: { id: c.id, a: c.a, b: c.b, km: c.km, lineName: l.name },
        geometry: { type: "Point", coordinates: [toLon(p.x), toLat(p.y)] },
      };
    }),
  };
}

export function tractionGeoJSON(mode: ViewMode): FC {
  return {
    type: "FeatureCollection",
    features: TRACTION.map((t) => ({
      type: "Feature",
      properties: { id: t.id, state: t.state, fromKm: t.fromKm, toKm: t.toKm },
      geometry: {
        type: "LineString",
        coordinates: linePolyline(t.fromKm, t.toKm, 0, mode, 0).map((p) => [toLon(p.x), toLat(p.y)]),
      },
    })),
  });
}

export function assetsGeoJSON(mode: ViewMode): FC {
  return {
    type: "FeatureCollection",
    features: ASSETS.map((a) => {
      const l = lineById(a.lineId);
      const p = project(a.km, l.offset, mode, l.index);
      return {
        type: "Feature",
        properties: { id: a.id, kind: a.kind, condition: a.condition, km: a.km, lineName: l.name },
        geometry: { type: "Point", coordinates: [toLon(p.x), toLat(p.y)] },
      };
    }),
  };
}

/** Bounding box (in meters) of the whole network for a view mode, for fitBounds. */
export function networkBounds(mode: ViewMode): { minX: number; maxX: number; minY: number; maxY: number } {
  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
  const consider = (p: Pt) => {
    if (p.x < minX) minX = p.x;
    if (p.x > maxX) maxX = p.x;
    if (p.y < minY) minY = p.y;
    if (p.y > maxY) maxY = p.y;
  };
  for (const l of LINES) {
    for (const p of linePolyline(KM_MIN, KM_MAX, l.offset, mode, l.index, 8)) consider(p);
  }
  return { minX, maxX, minY, maxY };
}
