/**
 * Deterministic demo data for OPUS-5 Part J analytical screens.
 *
 * The backend does not yet produce optimiser options, impact quantification,
 * bundling, or divisional scorecards (those are later phases). These screens
 * (J6 planning workspace, J7 approval, J8 live console, J10 executive
 * dashboard) need realistic figures to demonstrate the experience.
 *
 * Everything here is DETERMINISTIC (seeded by a stable string) so the same
 * figures appear for every user, every session — the map/UI must not look
 * random (K10 determinism principle, applied to demo data).
 *
 * When the real endpoints land, these functions are replaced 1:1.
 */

// ── Seeded PRNG (mulberry32) ────────────────────────────────────────────
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

function rng(seed: string) {
  return mulberry32(hashSeed(seed));
}

function pick<T>(r: () => number, arr: T[]): T {
  return arr[Math.floor(r() * arr.length)];
}

function between(r: () => number, min: number, max: number): number {
  return min + r() * (max - min);
}

function intBetween(r: () => number, min: number, max: number): number {
  return Math.floor(between(r, min, max + 1));
}

// ── J6: Planning options ────────────────────────────────────────────────
export interface PlanOption {
  id: string;
  name: string;
  demandsScheduled: number;
  totalDemands: number;
  detentionMin: number;
  cancellations: number;
  freightDelayedT: number;
  blockHoursUsed: number;
  bundlesFormed: number;
  blockHoursSaved: number;
  statutoryAtRisk: number;
  machineUtilisation: number; // 0-100
  objectiveScore: number; // 0-100
  recommended: boolean;
}

export interface PlanningRun {
  runId: string;
  horizon: string;
  weights: string;
  options: PlanOption[];
  why: string[];
  improve: string[];
}

const OPTION_NAMES = [
  "A: Least traffic",
  "B: Max output",
  "C: Balanced",
  "D: As asked",
  "E: Low risk",
];

export function getPlanningRun(seed = "DLI-2026-09"): PlanningRun {
  const r = rng(seed);
  const totalDemands = intBetween(r, 44, 58);
  const options: PlanOption[] = OPTION_NAMES.map((name, i) => {
    const scheduled = intBetween(r, Math.floor(totalDemands * 0.7), totalDemands);
    const detention = intBetween(r, 900, 4200);
    const cancels = intBetween(r, 0, 12);
    const freight = intBetween(r, 1500, 9500);
    const blockHours = intBetween(r, 100, 175);
    const bundles = intBetween(r, 2, 12);
    const saved = intBetween(r, 6, 48);
    const statutory = intBetween(r, 0, 7);
    const machine = intBetween(r, 55, 92);
    // Objective score: reward bundles + low statutory risk + reasonable detention.
    const score = Math.max(
      0,
      Math.min(
        100,
        Math.round(
          40 +
            bundles * 2.2 -
            statutory * 3 -
            Math.max(0, detention - 1500) / 60 +
            (scheduled / totalDemands) * 20,
        ),
      ),
    );
    return {
      id: `opt-${i}`,
      name,
      demandsScheduled: scheduled,
      totalDemands,
      detentionMin: detention,
      cancellations: cancels,
      freightDelayedT: freight,
      blockHoursUsed: blockHours,
      bundlesFormed: bundles,
      blockHoursSaved: saved,
      statutoryAtRisk: statutory,
      machineUtilisation: machine,
      objectiveScore: score,
      recommended: false,
    };
  });
  // Mark the highest-scoring option as recommended.
  const best = options.reduce((a, b) => (b.objectiveScore > a.objectiveScore ? b : a));
  best.recommended = true;

  return {
    runId: `#${intBetween(r, 4000, 5999)}`,
    horizon: "21 Sep – 27 Sep",
    weights: "DLI-standard v4",
    options,
    why: [
      `Forms ${best.bundlesFormed} bundles, saving ${best.blockHoursSaved} block-hours against executing every demand separately.`,
      `Schedules all statutory-due items before their deadlines; uses Tue/Wed nights for most work and avoids protected services.`,
      `${best.totalDemands - best.demandsScheduled} demands unscheduled: ${intBetween(r, 2, 5)} lack confirmed materials, ${intBetween(r, 1, 3)} need a committed machine, ${intBetween(r, 0, 2)} have an unresolved dependency.`,
    ],
    improve: [
      `Releasing tamper TM-07 two days earlier would allow ${intBetween(r, 2, 4)} more demands (+${intBetween(r, 6, 12)} block-hrs saved, statutory risk unchanged).`,
      `If the Wed 24 embargo were lifted, detention falls a further ${intBetween(r, 8, 14)}%.`,
    ],
  };
}

// ── J5/J7: Live impact ──────────────────────────────────────────────────
export interface ImpactFigure {
  affectedTrains: number;
  detentionMin: number;
  cancellations: number;
  freightDelayedT: number;
  passengersAffected: number;
  indicativeCostINR: number;
  confidence: "L1 empirical" | "L2 analytical" | "L3 heuristic";
  protectedServicesAffected: number;
}

export function getImpact(seed: string): ImpactFigure {
  const r = rng(seed);
  const affected = intBetween(r, 3, 18);
  return {
    affectedTrains: affected,
    detentionMin: intBetween(r, 40, 420),
    cancellations: intBetween(r, 0, 4),
    freightDelayedT: intBetween(r, 0, 1600),
    passengersAffected: intBetween(r, 0, 2400),
    indicativeCostINR: Math.round(between(r, 120000, 900000)),
    confidence: pick(r, ["L1 empirical", "L2 analytical", "L2 analytical", "L3 heuristic"]),
    protectedServicesAffected: intBetween(r, 0, 4),
  };
}

export interface BetterWindow {
  label: string;
  detentionMin: number;
  cancellations: number;
  savingPct: number;
  best: boolean;
  note?: string;
}

export function getBetterWindows(seed: string): BetterWindow[] {
  const r = rng(seed);
  const base = intBetween(r, 200, 360);
  const windows: BetterWindow[] = [
    {
      label: "Sun 21 Sep 01:00–05:00",
      detentionMin: Math.round(base * between(r, 0.5, 0.7)),
      cancellations: 0,
      savingPct: intBetween(r, 55, 75),
      best: false,
    },
    {
      label: "Tue 23 Sep 01:00–05:00",
      detentionMin: Math.round(base * between(r, 0.3, 0.5)),
      cancellations: 0,
      savingPct: intBetween(r, 70, 85),
      best: true,
      note: "Bundled with D-1043, D-1047 — 92 min total for 3 works",
    },
  ];
  return windows;
}

// ── J5: Nearby open demands (bundling) ──────────────────────────────────
export interface NearbyDemand {
  id: string;
  dept: string;
  km: number;
  durationH: number;
  canBundle: boolean;
}

export function getNearbyDemands(seed: string): NearbyDemand[] {
  const r = rng(seed);
  const depts = ["OHE", "S&T", "Engg", "Project"];
  return Array.from({ length: intBetween(r, 3, 5) }).map((_, i) => ({
    id: `D-${intBetween(r, 1000, 1999)}`,
    dept: pick(r, depts),
    km: Math.round(between(r, 411, 416) * 10) / 10,
    durationH: intBetween(r, 1, 4),
    canBundle: r() > 0.4,
  }));
}

// ── J7: Rule findings ───────────────────────────────────────────────────
export interface RuleFinding {
  code: string;
  text: string;
  status: "pass" | "warn" | "fail";
}

export function getRuleFindings(seed: string): RuleFinding[] {
  const r = rng(seed);
  return [
    { code: "R-0142", text: "Adjacent line — satisfied", status: "pass" },
    { code: "R-0088", text: "Competency — valid", status: "pass" },
    {
      code: "R-0203",
      text: `${intBetween(r, 2, 3)} depts in one bundle — joint readiness historically ${intBetween(r, 70, 85)}%`,
      status: "warn",
    },
    ...(r() > 0.6
      ? [{ code: "R-0311", text: "Machine TM-07 available in window", status: "pass" as const }]
      : []),
  ];
}

// ── J8: Work packages ───────────────────────────────────────────────────
export interface WorkPackage {
  id: string;
  dept: string;
  task: string;
  progress: number; // 0-100
  status: "on_time" | "slow" | "done";
  siteInCharge: string;
  note?: string;
}

export function getWorkPackages(seed: string): WorkPackage[] {
  const r = rng(seed);
  const defs = [
    { dept: "Engg", task: "packing", sic: "SSE/P.Way SBB" },
    { dept: "OHE", task: "insulator replacement", sic: "JE/OHE SBB" },
    { dept: "S&T", task: "axle counter alteration", sic: "SE/S&T GZB" },
  ];
  return defs.map((d, i) => {
    const progress = i === 1 ? 100 : intBetween(r, 30, 90);
    return {
      id: `WP-${i + 1}`,
      dept: d.dept,
      task: d.task,
      progress,
      status: progress >= 100 ? "done" : progress < 50 ? "slow" : "on_time",
      siteInCharge: d.sic,
      note:
        progress < 50
          ? "testing not yet started (0:30 needed)"
          : progress >= 100
            ? "complete"
            : undefined,
    };
  });
}

// ── J8: Extension request ───────────────────────────────────────────────
export interface ExtensionRequest {
  wp: string;
  dept: string;
  minutes: number;
  reason: string;
  ifGranted: { trains: number; detentionMin: number; cancellations: number; detail: string };
  ifRefused: string;
}

export function getExtensionRequest(seed: string): ExtensionRequest {
  const r = rng(seed);
  return {
    wp: "WP-3",
    dept: "S&T",
    minutes: intBetween(r, 20, 60),
    reason: "cable termination fault found",
    ifGranted: {
      trains: intBetween(r, 2, 6),
      detentionMin: intBetween(r, 30, 90),
      cancellations: 0,
      detail: `${intBetween(r, 1, 3)} trains held, ${intBetween(r, 1, 3)} goods rerouted via loop`,
    },
    ifRefused:
      "Work incomplete; axle counter must be restored to previous state (0:20); a fresh 2 h block will be required within 7 days.",
  };
}

// ── J10: Executive dashboard ────────────────────────────────────────────
export interface KpiTrend {
  label: string;
  value: string;
  delta: number; // signed
  goodWhenUp: boolean;
  spark: number[];
}

export interface ScorecardRow {
  dept: string;
  demands: number;
  sanctioned: number;
  utilised: number; // %
  grantPunct: number; // %
  overrun: number; // %
  askedUsed: string;
  statutoryOk: string;
}

export interface ExecutiveDashboard {
  period: string;
  division: string;
  kpis: KpiTrend[];
  scorecard: ScorecardRow[];
  topCauses: { label: string; pct: number }[];
  worstSections: { label: string; detentionPerBlockHour: number }[];
  restrictionsOverdue: number;
  oldestRestriction: string;
  attention: string[];
}

export function getExecutiveDashboard(seed = "DLI-2026-08"): ExecutiveDashboard {
  const r = rng(seed);
  const spark = () => Array.from({ length: 8 }).map(() => intBetween(r, 20, 100));
  const kpis: KpiTrend[] = [
    { label: "Block utilisation", value: `${intBetween(r, 60, 74)}%`, delta: intBetween(r, 2, 8), goodWhenUp: true, spark: spark() },
    { label: "Grant punctuality", value: `${intBetween(r, 76, 88)}%`, delta: intBetween(r, 3, 10), goodWhenUp: true, spark: spark() },
    { label: "Overrun rate", value: `${intBetween(r, 8, 16)}%`, delta: -intBetween(r, 1, 5), goodWhenUp: false, spark: spark() },
    { label: "Non-utilisation", value: `${intBetween(r, 2, 6)}%`, delta: -intBetween(r, 1, 3), goodWhenUp: false, spark: spark() },
    { label: "Detention / block-hour", value: `${(between(r, 11, 18)).toFixed(1)} min`, delta: -Number(between(r, 1, 4).toFixed(1)), goodWhenUp: false, spark: spark() },
    { label: "Bundling ratio", value: `${intBetween(r, 30, 45)}%`, delta: intBetween(r, 6, 15), goodWhenUp: true, spark: spark() },
    { label: "Backlog (stat. overdue)", value: String(intBetween(r, 12, 30)), delta: -intBetween(r, 4, 14), goodWhenUp: false, spark: spark() },
    { label: "Emergency share", value: `${intBetween(r, 6, 12)}%`, delta: -intBetween(r, 1, 4), goodWhenUp: false, spark: spark() },
  ];

  const depts = ["Engg", "Elec", "S&T", "Project"];
  const scorecard: ScorecardRow[] = depts.map((dept) => {
    const demands = intBetween(r, 30, 200);
    const sanctioned = intBetween(r, Math.floor(demands * 0.8), demands);
    return {
      dept,
      demands,
      sanctioned,
      utilised: intBetween(r, 55, 85),
      grantPunct: intBetween(r, 74, 90),
      overrun: intBetween(r, 6, 24),
      askedUsed: `${(between(r, 2.5, 8)).toFixed(1)}/${(between(r, 2, 7)).toFixed(1)}h`,
      statutoryOk: dept === "Project" ? "—" : `${intBetween(r, 86, 98)}%`,
    };
  });

  return {
    period: "Aug 2026",
    division: "DLI",
    kpis,
    scorecard,
    topCauses: [
      { label: "Late grant (traffic)", pct: intBetween(r, 18, 26) },
      { label: "Machine late arrival", pct: intBetween(r, 12, 20) },
      { label: "Protection took longer", pct: intBetween(r, 10, 16) },
      { label: "Material not at site", pct: intBetween(r, 8, 14) },
      { label: "Testing underestimated", pct: intBetween(r, 6, 11) },
    ],
    worstSections: [
      { label: "SBB–GZB", detentionPerBlockHour: Number(between(r, 24, 32).toFixed(1)) },
      { label: "GZB–MUT", detentionPerBlockHour: Number(between(r, 16, 22).toFixed(1)) },
      { label: "DLI–SBB", detentionPerBlockHour: Number(between(r, 13, 19).toFixed(1)) },
    ],
    restrictionsOverdue: intBetween(r, 4, 9),
    oldestRestriction: `${intBetween(r, 20, 40)} kmph at ${intBetween(r, 410, 420)}.${intBetween(r, 0, 9)} — ${intBetween(r, 60, 120)} days`,
    attention: [
      `${intBetween(r, 2, 4)} statutory items will breach their due date within 21 days and are unscheduled`,
      "Corridor block for 12 Oct has no bids from S&T — capacity likely to be wasted",
      "Tamper TM-07 utilisation 61% — 14 idle days next month; reserve queue has 9 jobs",
    ],
  };
}

// ── J4: Now panel (extensions pending, active blocks, alerts) ───────────
export interface ExtensionPending {
  id: string;
  minutes: number;
  impactMin: number;
}

export interface ActiveBlockNow {
  id: string;
  line: string;
  fromKm: number;
  toKm: number;
  endsAt: string;
  remainingMin: number;
  progress: number;
  emergency?: boolean;
  note?: string;
}

export interface NowPanel {
  extensionsPending: ExtensionPending[];
  activeBlocks: ActiveBlockNow[];
  next6Hours: { time: string; id: string; label: string }[];
  alerts: { id: string; text: string }[];
}

export function getNowPanel(seed = "DLI-now"): NowPanel {
  const r = rng(seed);
  return {
    extensionsPending: [
      { id: "B-2291", minutes: 45, impactMin: 62 },
      { id: "B-2288", minutes: 20, impactMin: 8 },
    ],
    activeBlocks: [
      { id: "B-2291", line: "UP Main", fromKm: 412.1, toKm: 413.5, endsAt: "14:00", remainingMin: 72, progress: 68 },
      { id: "B-2288", line: "DN Loop", fromKm: 409.0, toKm: 410.2, endsAt: "13:30", remainingMin: 42, progress: 55 },
      { id: "E-0034", line: "UP Main", fromKm: 415.0, toKm: 415.4, endsAt: "15:00", remainingMin: 102, progress: 30, emergency: true, note: "rail fracture" },
    ],
    next6Hours: [
      { time: "14:30", id: "B-2295", label: "OHE inspection" },
      { time: "16:00", id: "B-2301", label: "Through packing" },
      { time: "17:15", id: "B-2304", label: "Axle counter" },
    ],
    alerts: [
      { id: "A-1", text: "B-2301 AT RISK — material unconfirmed" },
      { id: "A-2", text: "3 acknowledgements outstanding" },
      { id: "A-3", text: "E-0034 emergency — rail fracture under inspection" },
    ],
  };
}
