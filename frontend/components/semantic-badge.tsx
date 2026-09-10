"use client";

import {
  Square,
  Calendar,
  FileQuestion,
  Sparkles,
  GitMerge,
  AlertOctagon,
  Gauge,
  Siren,
  TrainFront,
  Train,
  Minus,
  Slash,
  ZapOff,
  Clock,
  type LucideIcon,
} from "lucide-react";
import { getSemantic, type SemanticState } from "@/lib/palette";
import { cn } from "@/lib/utils";

const ICONS: Record<string, LucideIcon> = {
  square: Square,
  calendar: Calendar,
  "file-question": FileQuestion,
  sparkles: Sparkles,
  "git-merge": GitMerge,
  "alert-octagon": AlertOctagon,
  gauge: Gauge,
  siren: Siren,
  "train-front": TrainFront,
  train: Train,
  minus: Minus,
  slash: Slash,
  "zap-off": ZapOff,
  clock: Clock,
};

/**
 * A small swatch that shows the state's colour AND pattern (J2: colour is
 * never the only channel). Used in legends and inline chips.
 */
export function PatternSwatch({ state, className }: { state: SemanticState; className?: string }) {
  const style: React.CSSProperties = {
    backgroundColor: state.pattern === "outline" ? "transparent" : state.color,
    border: state.pattern === "outline" ? `2px dashed ${state.color}` : "none",
  };
  // Overlay a pattern for hatched / dotted / dashed fills.
  let backgroundImage: string | undefined;
  if (state.pattern === "hatched") {
    backgroundImage = `repeating-linear-gradient(45deg, rgba(255,255,255,0.55) 0 2px, transparent 2px 5px)`;
  } else if (state.pattern === "dotted") {
    backgroundImage = `radial-gradient(${state.onColor} 1px, transparent 1.4px)`;
    style.backgroundSize = "5px 5px";
  } else if (state.pattern === "dashed") {
    backgroundImage = `repeating-linear-gradient(90deg, ${state.onColor} 0 3px, transparent 3px 6px)`;
  }
  return (
    <span
      aria-hidden
      className={cn("inline-block h-3 w-5 shrink-0 rounded-sm", className)}
      style={{ ...style, backgroundImage }}
    />
  );
}

/**
 * SemanticBadge — renders a semantic state as a labelled chip with icon +
 * pattern swatch + text. The single component used everywhere a block/train
 * state is shown, so the meaning of a colour is consistent app-wide (J2).
 */
export function SemanticBadge({
  stateKey,
  label,
  className,
  showSwatch = true,
}: {
  stateKey: string;
  label?: string;
  className?: string;
  showSwatch?: boolean;
}) {
  const state = getSemantic(stateKey);
  const Icon = ICONS[state.icon] ?? Square;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-md px-2 py-0.5 text-xs font-medium",
        state.chip,
        className,
      )}
      title={state.description}
    >
      {showSwatch && <PatternSwatch state={state} />}
      <Icon className="h-3 w-3" />
      {label ?? state.label}
    </span>
  );
}

/**
 * SemanticLegend — the J2 palette legend. Colour + pattern + icon + meaning.
 */
export function SemanticLegend({
  keys,
  className,
}: {
  keys?: readonly string[];
  className?: string;
}) {
  const list = (keys ?? (["active", "granted", "approved", "requested", "proposed", "conflict", "emergency"] as const));
  return (
    <div className={cn("grid grid-cols-1 gap-1.5", className)}>
      {list.map((k) => {
        const state = getSemantic(k);
        const Icon = ICONS[state.icon] ?? Square;
        return (
          <div key={k} className="flex items-center gap-2 text-xs">
            <PatternSwatch state={state} />
            <Icon className="h-3.5 w-3.5 text-muted-foreground" />
            <span className="text-foreground">{state.label}</span>
          </div>
        );
      })}
    </div>
  );
}
