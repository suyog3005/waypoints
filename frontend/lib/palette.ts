/**
 * OPUS-5 Part J2 — Semantic palette.
 *
 * "Colour means one thing, everywhere." A single semantic palette is shared
 * across the map, lists, timeline and dashboards. A colour is never re-used
 * for a different meaning in a different view.
 *
 * Colour is never the ONLY channel: every state also carries a pattern
 * (solid / dashed / hatched / dotted) and an icon, for accessibility and
 * greyscale printing (J1 principle 4, J11).
 *
 * This module is the single source of truth. Components and the map layers
 * import from here so the meaning of a colour can never drift between views.
 */

export type Pattern = "solid" | "dashed" | "hatched" | "dotted" | "outline" | "flashing";

export interface SemanticState {
  /** Stable key used across the app. */
  key: string;
  /** Human label. */
  label: string;
  /** Base colour (hex). */
  color: string;
  /** Foreground colour that reads on top of `color`. */
  onColor: string;
  /** Tailwind classes for a filled pill/badge. */
  badge: string;
  /** Tailwind classes for a soft (tinted) background chip. */
  chip: string;
  /** The non-colour channel: pattern. */
  pattern: Pattern;
  /** lucide icon name (resolved by the consumer). */
  icon: string;
  /** One-line description of what the state means. */
  description: string;
}

/**
 * The full semantic palette (J2 table).
 *
 * Order here is the legend order shown in the UI.
 */
export const SEMANTIC_STATES: Record<string, SemanticState> = {
  // ── Blocks ──────────────────────────────────────────────────────────
  active: {
    key: "active",
    label: "Active block",
    color: "#dc2626",
    onColor: "#ffffff",
    badge: "bg-red-600 text-white",
    chip: "bg-red-50 text-red-700 dark:bg-red-950/40 dark:text-red-300",
    pattern: "solid",
    icon: "square",
    description: "In force now — the line is closed.",
  },
  granted: {
    key: "granted",
    label: "Granted, not protected",
    color: "#dc2626",
    onColor: "#ffffff",
    badge: "bg-red-600 text-white",
    chip: "bg-red-50 text-red-700 dark:bg-red-950/40 dark:text-red-300",
    pattern: "hatched",
    icon: "square",
    description: "Sanctioned but protection not yet complete.",
  },
  approved: {
    key: "approved",
    label: "Approved / scheduled",
    color: "#d97706",
    onColor: "#ffffff",
    badge: "bg-amber-600 text-white",
    chip: "bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300",
    pattern: "solid",
    icon: "calendar",
    description: "Planned block in the future.",
  },
  requested: {
    key: "requested",
    label: "Requested / under review",
    color: "#d97706",
    onColor: "#ffffff",
    badge: "bg-amber-600 text-white",
    chip: "bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300",
    pattern: "dashed",
    icon: "file-question",
    description: "Demand not yet approved.",
  },
  proposed: {
    key: "proposed",
    label: "Proposed by optimiser",
    color: "#7c3aed",
    onColor: "#ffffff",
    badge: "bg-violet-600 text-white",
    chip: "bg-violet-50 text-violet-700 dark:bg-violet-950/40 dark:text-violet-300",
    pattern: "dotted",
    icon: "sparkles",
    description: "System suggestion — distinct from human decisions.",
  },
  bundle: {
    key: "bundle",
    label: "Bundle candidate",
    color: "#7c3aed",
    onColor: "#ffffff",
    badge: "bg-violet-600 text-white",
    chip: "bg-violet-50 text-violet-700 dark:bg-violet-950/40 dark:text-violet-300",
    pattern: "solid",
    icon: "git-merge",
    description: "Bundling opportunity (connecting brace).",
  },
  conflict: {
    key: "conflict",
    label: "Conflict",
    color: "#db2777",
    onColor: "#ffffff",
    badge: "bg-pink-600 text-white",
    chip: "bg-pink-50 text-pink-700 dark:bg-pink-950/40 dark:text-pink-300",
    pattern: "flashing",
    icon: "alert-octagon",
    description: "Anything requiring resolution.",
  },
  restriction: {
    key: "restriction",
    label: "Restriction (speed)",
    color: "#ea580c",
    onColor: "#ffffff",
    badge: "bg-orange-600 text-white",
    chip: "bg-orange-50 text-orange-700 dark:bg-orange-950/40 dark:text-orange-300",
    pattern: "dashed",
    icon: "gauge",
    description: "TSR / PSR along the track.",
  },
  emergency: {
    key: "emergency",
    label: "Emergency / incident",
    color: "#dc2626",
    onColor: "#ffffff",
    badge: "bg-red-600 text-white",
    chip: "bg-red-50 text-red-700 dark:bg-red-950/40 dark:text-red-300",
    pattern: "flashing",
    icon: "siren",
    description: "Emergency block or incident (flashing halo).",
  },
  // ── Trains ──────────────────────────────────────────────────────────
  train_passenger: {
    key: "train_passenger",
    label: "Train (passenger)",
    color: "#2563eb",
    onColor: "#ffffff",
    badge: "bg-blue-600 text-white",
    chip: "bg-blue-50 text-blue-700 dark:bg-blue-950/40 dark:text-blue-300",
    pattern: "solid",
    icon: "train-front",
    description: "Passenger train position marker.",
  },
  train_freight: {
    key: "train_freight",
    label: "Train (freight)",
    color: "#16a34a",
    onColor: "#ffffff",
    badge: "bg-green-600 text-white",
    chip: "bg-green-50 text-green-700 dark:bg-green-950/40 dark:text-green-300",
    pattern: "solid",
    icon: "train",
    description: "Freight train position marker.",
  },
  train_delayed: {
    key: "train_delayed",
    label: "Train (delayed)",
    color: "#2563eb",
    onColor: "#ffffff",
    badge: "bg-blue-600 text-white ring-2 ring-red-500",
    chip: "bg-blue-50 text-blue-700 dark:bg-blue-950/40 dark:text-blue-300",
    pattern: "solid",
    icon: "train-front",
    description: "Delayed beyond threshold (red ring).",
  },
  // ── Line / traction ─────────────────────────────────────────────────
  line_available: {
    key: "line_available",
    label: "Line available",
    color: "#64748b",
    onColor: "#ffffff",
    badge: "bg-slate-500 text-white",
    chip: "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
    pattern: "solid",
    icon: "minus",
    description: "Normal track.",
  },
  line_unavailable: {
    key: "line_unavailable",
    label: "Line unavailable (derived)",
    color: "#94a3b8",
    onColor: "#1e293b",
    badge: "bg-slate-300 text-slate-800",
    chip: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400",
    pattern: "hatched",
    icon: "slash",
    description: "Not blocked itself, but rendered unusable.",
  },
  electrically_dead: {
    key: "electrically_dead",
    label: "Electrically dead",
    color: "#475569",
    onColor: "#facc15",
    badge: "bg-slate-600 text-yellow-300",
    chip: "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
    pattern: "hatched",
    icon: "zap-off",
    description: "Traction isolation footprint.",
  },
  derived: {
    key: "derived",
    label: "Derived block",
    color: "#7c3aed",
    onColor: "#ffffff",
    badge: "bg-violet-600 text-white",
    chip: "bg-violet-50 text-violet-700 dark:bg-violet-950/40 dark:text-violet-300",
    pattern: "dotted",
    icon: "git-branch",
    description: "Auto-derived from a rule (e.g. stranded via a CO).",
  },
  // ── Degradation ─────────────────────────────────────────────────────
  stale: {
    key: "stale",
    label: "Stale / low confidence",
    color: "#94a3b8",
    onColor: "#1e293b",
    badge: "bg-slate-300 text-slate-800 opacity-50",
    chip: "bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400",
    pattern: "solid",
    icon: "clock",
    description: "Any state at 50% opacity + a clock badge.",
  },
};

/**
 * Map a block request / block status string to a semantic state key.
 * This is the bridge between backend lifecycle strings and the J2 palette.
 */
export function statusToSemanticKey(status: string | null | undefined): string {
  const s = (status ?? "").toLowerCase();
  switch (s) {
    case "active":
    case "working":
    case "in_force":
      return "active";
    case "granted":
    case "protected":
    case "isolated":
      return "granted";
    case "approved":
    case "scheduled":
    case "merged":
      return "approved";
    case "requested":
    case "submitted":
    case "under_review":
    case "draft":
      return "requested";
    case "proposed":
    case "optimised":
      return "proposed";
    case "emergency":
    case "incident":
      return "emergency";
    case "conflict":
      return "conflict";
    case "completed":
    case "closed":
    case "handed_back":
      return "line_available";
    case "cancelled":
    case "superseded":
      return "stale";
    default:
      return "requested";
  }
}

export function getSemantic(key: string): SemanticState {
  return SEMANTIC_STATES[key] ?? SEMANTIC_STATES.requested;
}

/**
 * Legend entries for the map / list legend (J2). Ordered for display.
 */
export const LEGEND_ORDER = [
  "active",
  "granted",
  "approved",
  "requested",
  "proposed",
  "bundle",
  "conflict",
  "restriction",
  "emergency",
  "train_passenger",
  "train_freight",
  "line_available",
  "line_unavailable",
  "electrically_dead",
  "derived",
] as const;
