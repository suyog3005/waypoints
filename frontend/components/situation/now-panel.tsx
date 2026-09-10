"use client";

import Link from "next/link";
import { AlertTriangle, Clock, Check, X } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { getNowPanel } from "@/lib/demo-data";
import { cn } from "@/lib/utils";

/**
 * OPUS-5 Part J4 — the "NOW" panel (right column of the Situation screen).
 *
 * Extensions pending appear at the top with their computed impact already
 * visible — the controller decides in one glance, not after a phone call
 * (S-29). Below: active blocks, the next 6 hours, and alerts.
 */
export function NowPanel() {
  const now = getNowPanel();

  return (
    <div className="flex h-full flex-col gap-3 overflow-y-auto">
      {/* Extensions pending — top priority */}
      <Card className="border-amber-300 dark:border-amber-700">
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-sm text-amber-700 dark:text-amber-400">
            <AlertTriangle className="h-4 w-4" />
            {now.extensionsPending.length} extensions pending
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {now.extensionsPending.map((ext) => (
            <div key={ext.id} className="rounded-md border p-2 text-xs">
              <div className="flex items-center justify-between">
                <span className="font-semibold">{ext.id}</span>
                <span className="text-amber-700 dark:text-amber-400">+{ext.minutes} min</span>
              </div>
              <p className="my-1 text-muted-foreground">impact {ext.impactMin} min</p>
              <div className="flex gap-1.5">
                <Button size="sm" variant="outline" className="h-6 flex-1 gap-1 px-2 text-xs">
                  <Check className="h-3 w-3" /> Grant
                </Button>
                <Button size="sm" variant="ghost" className="h-6 flex-1 gap-1 px-2 text-xs">
                  <X className="h-3 w-3" /> Refuse
                </Button>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      {/* Active blocks */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">
            Active blocks <span className="text-muted-foreground">{now.activeBlocks.length}</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {now.activeBlocks.map((b) => (
            <Link
              key={b.id}
              href={`/execution/console?block=${b.id}`}
              className={cn(
                "block rounded-md border p-2 text-xs transition-colors hover:bg-accent",
                b.emergency && "border-red-400 bg-red-50 dark:border-red-700 dark:bg-red-950/30",
              )}
            >
              <div className="flex items-center justify-between">
                <span className={cn("font-semibold", b.emergency && "text-red-600 dark:text-red-400")}>
                  {b.emergency ? "● " : "● "}{b.id}
                </span>
                <span className="flex items-center gap-1 text-muted-foreground">
                  <Clock className="h-3 w-3" /> {b.endsAt}
                </span>
              </div>
              <p className="text-muted-foreground">
                {b.line} {b.fromKm}–{b.toKm}
                {b.note ? ` · ${b.note}` : ""}
              </p>
              {/* Progress bar */}
              <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-muted">
                <div
                  className={cn("h-full rounded-full", b.emergency ? "bg-red-500" : "bg-primary")}
                  style={{ width: `${b.progress}%` }}
                />
              </div>
            </Link>
          ))}
        </CardContent>
      </Card>

      {/* Next 6 hours */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Next 6 hours</CardTitle>
        </CardHeader>
        <CardContent className="space-y-1">
          {now.next6Hours.map((n) => (
            <div key={n.id} className="flex items-center gap-2 text-xs">
              <span className="w-10 font-mono text-muted-foreground">{n.time}</span>
              <span className="font-medium">{n.id}</span>
              <span className="truncate text-muted-foreground">{n.label}</span>
            </div>
          ))}
        </CardContent>
      </Card>

      {/* Alerts */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">
            Alerts <span className="text-muted-foreground">{now.alerts.length}</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-1.5">
          {now.alerts.map((a) => (
            <div key={a.id} className="flex items-start gap-1.5 text-xs">
              <AlertTriangle className="mt-0.5 h-3 w-3 shrink-0 text-amber-500" />
              <span>{a.text}</span>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
