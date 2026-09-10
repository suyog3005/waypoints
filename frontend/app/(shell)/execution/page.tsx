"use client";

import Link from "next/link";
import { ClipboardCheck, Clock, AlertTriangle, CheckCircle2 } from "lucide-react";
import { PageHeader } from "@/components/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { SemanticBadge } from "@/components/semantic-badge";
import { useBlockRequests } from "@/lib/hooks";
import { getNowPanel } from "@/lib/demo-data";
import { statusToSemanticKey } from "@/lib/palette";
import { formatDateTime } from "@/lib/format";
import { cn } from "@/lib/utils";

/**
 * OPUS-5 Part J3 (EXECUTION) — Today's blocks (control view) + readiness
 * board (T-24h gate). Lists the day's blocks with their execution/safety
 * state and a readiness checklist, and links into the live block console.
 */

export default function ExecutionPage() {
  const { data: requests = [] } = useBlockRequests();
  const now = getNowPanel();

  // Merge live requests with the demo "active now" set so the board is
  // always populated for the demo.
  const rows = [
    ...now.activeBlocks.map((b) => ({
      id: b.id,
      line: b.line,
      extent: `${b.fromKm}–${b.toKm}`,
      endsAt: b.endsAt,
      remainingMin: b.remainingMin,
      progress: b.progress,
      emergency: b.emergency,
      note: b.note,
      semantic: b.emergency ? "emergency" : "active",
      live: false,
    })),
    ...requests.slice(0, 6).map((r) => ({
      id: r.id.slice(0, 8),
      line: r.work_type ?? "—",
      extent: "—",
      endsAt: r.requested_end ? formatDateTime(r.requested_end) : "—",
      remainingMin: null as number | null,
      progress: r.execution?.quantum_completed ?? 0,
      emergency: r.is_emergency,
      note: r.block_class,
      semantic: statusToSemanticKey(r.status),
      live: true,
      fullId: r.id,
    })),
  ];

  return (
    <div className="space-y-4">
      <PageHeader
        title="Today's blocks"
        description="Control view of the day's blocks with readiness and safety state."
      />

      {/* Readiness board (T-24h gate) */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-sm">
            <ClipboardCheck className="h-4 w-4" /> Readiness board (T-24h gate)
          </CardTitle>
        </CardHeader>
        <CardContent className="grid gap-2 sm:grid-cols-3">
          <ReadinessItem label="Materials confirmed" done />
          <ReadinessItem label="Machine TM-07 allocated" done />
          <ReadinessItem label="Gang rested & briefed" done={false} />
        </CardContent>
      </Card>

      {/* Today's blocks */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">{rows.length} blocks today</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {rows.map((r) => (
            <Link
              key={r.id}
              href={`/execution/console?block=${r.id}`}
              className={cn(
                "flex flex-wrap items-center justify-between gap-3 rounded-md border p-3 transition-colors hover:bg-accent",
                r.emergency && "border-red-400 bg-red-50 dark:border-red-700 dark:bg-red-950/30",
              )}
            >
              <div className="flex items-center gap-3">
                <SemanticBadge stateKey={r.semantic} label={r.semantic} />
                <div>
                  <p className="font-medium">{r.id}</p>
                  <p className="text-xs text-muted-foreground">
                    {r.line} · {r.extent}
                    {r.note ? ` · ${r.note}` : ""}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-4">
                {typeof r.progress === "number" && (
                  <div className="w-28">
                    <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
                      <div
                        className={cn("h-full rounded-full", r.emergency ? "bg-red-500" : "bg-primary")}
                        style={{ width: `${r.progress}%` }}
                      />
                    </div>
                  </div>
                )}
                <span className="flex items-center gap-1 text-xs text-muted-foreground">
                  <Clock className="h-3 w-3" /> ends {r.endsAt}
                </span>
                <Button size="sm" variant="outline" className="h-7">
                  Open console
                </Button>
              </div>
            </Link>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}

function ReadinessItem({ label, done }: { label: string; done?: boolean }) {
  return (
    <div className="flex items-center gap-2 rounded-md border p-2 text-sm">
      {done ? (
        <CheckCircle2 className="h-4 w-4 text-emerald-500" />
      ) : (
        <AlertTriangle className="h-4 w-4 text-amber-500" />
      )}
      <span className={cn(!done && "text-amber-600")}>{label}</span>
    </div>
  );
}
