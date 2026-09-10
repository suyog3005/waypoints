"use client";

import { useState } from "react";
import {
  RefreshCw,
  Star,
  GitCompare,
  Map as MapIcon,
  Calendar,
  Lightbulb,
  TrendingUp,
  Check,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { getPlanningRun, type PlanOption } from "@/lib/demo-data";
import { cn } from "@/lib/utils";

/**
 * OPUS-5 Part J6 — Planning workspace (options comparison).
 *
 * "One screen per decision" (J1 principle 2). The optimiser produces several
 * ranked options; the planner compares them side by side, reads the
 * explanation of the recommended option, and adopts it (or a modified
 * version). Every figure is reachable — no dead ends.
 */

interface Metric {
  key: keyof PlanOption;
  label: string;
  format: (v: number) => string;
  lowerIsBetter?: boolean;
}

const METRICS: Metric[] = [
  { key: "demandsScheduled", label: "Demands scheduled", format: (v) => `${v}` },
  { key: "detentionMin", label: "Detention (min)", format: (v) => v.toLocaleString(), lowerIsBetter: true },
  { key: "cancellations", label: "Cancellations", format: (v) => `${v}`, lowerIsBetter: true },
  { key: "freightDelayedT", label: "Freight delayed (t)", format: (v) => v.toLocaleString(), lowerIsBetter: true },
  { key: "blockHoursUsed", label: "Block-hours used", format: (v) => `${v}`, lowerIsBetter: true },
  { key: "bundlesFormed", label: "Bundles formed", format: (v) => `${v}` },
  { key: "blockHoursSaved", label: "Block-hours SAVED", format: (v) => `${v}` },
  { key: "statutoryAtRisk", label: "Statutory at risk", format: (v) => `${v}`, lowerIsBetter: true },
  { key: "machineUtilisation", label: "Machine utilisation", format: (v) => `${v}%` },
  { key: "objectiveScore", label: "Objective score", format: (v) => `${v}` },
];

export default function PlanningWorkspacePage() {
  const run = getPlanningRun();
  const [selected, setSelected] = useState<string | null>(null);

  const recommended = run.options.find((o) => o.recommended)!;
  const active = selected ? run.options.find((o) => o.id === selected) ?? recommended : recommended;

  // Best value per metric (for highlighting).
  const bestValue = (m: Metric) => {
    const vals = run.options.map((o) => o[m.key] as number);
    return m.lowerIsBetter ? Math.min(...vals) : Math.max(...vals);
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 className="text-lg font-semibold">Planning run {run.runId}</h1>
          <p className="text-sm text-muted-foreground">
            Horizon: {run.horizon} · Weights: {run.weights}
          </p>
        </div>
        <Button variant="outline" size="sm">
          <RefreshCw className="mr-1 h-4 w-4" /> Re-run
        </Button>
      </div>

      {/* Options comparison table */}
      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left">
                  <th className="p-3 font-medium text-muted-foreground">Option</th>
                  {run.options.map((o) => (
                    <th
                      key={o.id}
                      className={cn(
                        "cursor-pointer p-3 text-center font-medium",
                        active.id === o.id && "bg-primary/5",
                      )}
                      onClick={() => setSelected(o.id)}
                    >
                      <div className="flex items-center justify-center gap-1">
                        {o.recommended && <Star className="h-3.5 w-3.5 fill-amber-400 text-amber-400" />}
                        {o.name}
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {METRICS.map((m) => {
                  const best = bestValue(m);
                  return (
                    <tr key={m.key} className="border-b last:border-0">
                      <td className="p-3 text-muted-foreground">{m.label}</td>
                      {run.options.map((o) => {
                        const v = o[m.key] as number;
                        const isBest = v === best;
                        const isActive = active.id === o.id;
                        return (
                          <td
                            key={o.id}
                            className={cn(
                              "p-3 text-center tabular-nums",
                              isActive && "bg-primary/5",
                              isBest && "font-semibold text-emerald-600 dark:text-emerald-400",
                            )}
                          >
                            {m.format(v)}
                            {m.key === "demandsScheduled" && (
                              <span className="text-muted-foreground">/{o.totalDemands}</span>
                            )}
                          </td>
                        );
                      })}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Action row */}
      <div className="flex flex-wrap gap-2">
        <Button variant="outline" size="sm">
          <GitCompare className="mr-1 h-4 w-4" /> Compare A vs C
        </Button>
        <Button variant="outline" size="sm">
          <MapIcon className="mr-1 h-4 w-4" /> View {active.name.split(":")[0]} on map
        </Button>
        <Button variant="outline" size="sm">
          <Calendar className="mr-1 h-4 w-4" /> View on calendar
        </Button>
        <Button variant="outline" size="sm">
          <Lightbulb className="mr-1 h-4 w-4" /> Explain {active.name.split(":")[0]}
        </Button>
      </div>

      {/* Why + what would improve */}
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm">
              <TrendingUp className="h-4 w-4 text-primary" /> Why option {active.name.split(":")[0]}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2 text-sm">
              {run.why.map((w, i) => (
                <li key={i} className="flex gap-2">
                  <span className="text-primary">•</span>
                  <span>{w}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm">
              <Lightbulb className="h-4 w-4 text-amber-500" /> What would improve it
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2 text-sm">
              {run.improve.map((w, i) => (
                <li key={i} className="flex gap-2">
                  <span className="text-amber-500">•</span>
                  <span>{w}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      </div>

      {/* Adopt */}
      <div className="flex justify-end gap-2">
        <Button variant="outline" size="sm">
          Adopt with modifications
        </Button>
        <Button size="sm">
          <Check className="mr-1 h-4 w-4" /> Adopt option {active.name.split(":")[0]}
        </Button>
      </div>
    </div>
  );
}
