"use client";

import { useState } from "react";
import {
  Clock,
  ShieldCheck,
  ShieldAlert,
  Zap,
  Users,
  Phone,
  AlertTriangle,
  Check,
  X,
  MapPin,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { SemanticBadge } from "@/components/semantic-badge";
import { getWorkPackages, getExtensionRequest } from "@/lib/demo-data";
import { cn } from "@/lib/utils";

/**
 * OPUS-5 Part J8 — Live block console (control room).
 *
 * The controller sees the safety state, the work packages, the people on
 * site, and — critically — an extension request with BOTH consequences
 * (grant and refuse) shown, because refusing also has a cost and today that
 * cost is invisible (S-29).
 */

const SAFETY_STATES = [
  { label: "Traffic block", state: "GRANTED", time: "01:07", ok: true },
  { label: "Protection", state: "COMPLETE", time: "01:24", ok: true },
  { label: "OHE isolation", state: "GRANTED", time: "01:15", ok: true },
  { label: "Earthing", state: "CONFIRMED", time: "01:21", ok: true },
  { label: "Adjacent line", state: "BLOCKED", time: "", ok: true },
];

const TIMELINE = [
  "01:00 sanctioned",
  "01:07 granted",
  "01:15 isolation",
  "01:21 earthed",
  "01:24 protected",
  "01:26 work started",
  "04:52 WP-2 complete",
];

export default function LiveBlockConsolePage() {
  const seed = "B-2291";
  const packages = getWorkPackages(seed);
  const ext = getExtensionRequest(seed);
  const [reason, setReason] = useState("");

  return (
    <div className="space-y-4">
      {/* Header */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-lg font-semibold">B-2291</h1>
                <SemanticBadge stateKey="active" label="ACTIVE" />
              </div>
              <p className="text-sm text-muted-foreground">
                UP Main 412.100–413.500 · Bundle: D-1041 + D-1043 + D-1047
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                Granted 01:07 (sanctioned 01:00, +7 min: "last goods clearance")
              </p>
            </div>
            <div className="flex items-center gap-6">
              <div className="text-center">
                <p className="text-xs text-muted-foreground">Sanctioned end</p>
                <p className="text-lg font-semibold">06:35</p>
              </div>
              <div className="text-center">
                <p className="text-xs text-muted-foreground">Remaining</p>
                <p className="flex items-center gap-1 text-lg font-semibold">
                  <Clock className="h-4 w-4" /> 1 h 12 m
                </p>
              </div>
              <div className="w-40">
                <p className="mb-1 text-xs text-muted-foreground">Progress 68%</p>
                <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
                  <div className="h-full rounded-full bg-primary" style={{ width: "68%" }} />
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Safety state + work packages */}
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Safety state</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {SAFETY_STATES.map((s) => (
              <div key={s.label} className="flex items-center justify-between text-sm">
                <span className="flex items-center gap-2">
                  {s.ok ? (
                    <ShieldCheck className="h-4 w-4 text-emerald-500" />
                  ) : (
                    <ShieldAlert className="h-4 w-4 text-amber-500" />
                  )}
                  {s.label}
                </span>
                <span className="flex items-center gap-2">
                  <span className="font-medium">{s.state}</span>
                  {s.time && <span className="text-xs text-muted-foreground">{s.time}</span>}
                </span>
              </div>
            ))}
            <div className="flex items-center justify-between border-t pt-2 text-sm">
              <span className="flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 text-amber-500" /> Disconnections
              </span>
              <span className="font-medium text-amber-600">2 open ⚠</span>
            </div>
            <div className="flex items-center justify-between border-t pt-2 text-sm">
              <span className="flex items-center gap-2">
                <Users className="h-4 w-4 text-muted-foreground" /> People on site
              </span>
              <span className="font-medium">23</span>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="flex items-center gap-2">
                <Phone className="h-4 w-4 text-muted-foreground" /> Contact
              </span>
              <span className="font-medium">SSE/P.Way 9xxxxxxxxx</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Work packages</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {packages.map((wp) => (
              <div key={wp.id} className="rounded-md border p-2.5">
                <div className="flex items-center justify-between text-sm">
                  <span className="font-medium">
                    {wp.id} {wp.dept} {wp.task}
                  </span>
                  <span
                    className={cn(
                      "text-xs font-medium",
                      wp.status === "done"
                        ? "text-emerald-600"
                        : wp.status === "slow"
                          ? "text-amber-600"
                          : "text-muted-foreground",
                    )}
                  >
                    {wp.status === "done" ? "✓ done" : wp.status === "slow" ? "⚠ slow" : "on time"}
                  </span>
                </div>
                <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-muted">
                  <div
                    className={cn(
                      "h-full rounded-full",
                      wp.status === "done" ? "bg-emerald-500" : wp.status === "slow" ? "bg-amber-500" : "bg-primary",
                    )}
                    style={{ width: `${wp.progress}%` }}
                  />
                </div>
                <p className="mt-1 text-xs text-muted-foreground">
                  Site-in-charge: {wp.siteInCharge}
                  {wp.note ? ` · ${wp.note}` : ""}
                </p>
              </div>
            ))}
            <div className="rounded-md border p-2.5">
              <p className="mb-1.5 text-xs font-semibold">Worksite positions (live)</p>
              <ul className="space-y-1 text-xs text-muted-foreground">
                <li className="flex items-center gap-1.5">
                  <MapPin className="h-3 w-3" /> WP-1 at km 412.9 (moving)
                </li>
                <li className="flex items-center gap-1.5">
                  <MapPin className="h-3 w-3" /> WP-3 at km 413.1 (static)
                </li>
              </ul>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Extension request — both consequences */}
      <Card className="border-amber-300 dark:border-amber-700">
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-sm text-amber-700 dark:text-amber-400">
            <AlertTriangle className="h-4 w-4" /> Extension requested — {ext.wp} {ext.dept}, +{ext.minutes} min
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm">Reason: "{ext.reason}"</p>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-md border p-3 text-sm">
              <p className="mb-1 font-semibold text-emerald-600">IF GRANTED</p>
              <p className="text-muted-foreground">
                {ext.ifGranted.trains} trains affected · +{ext.ifGranted.detentionMin} detention-min ·{" "}
                {ext.ifGranted.cancellations} cancellations
              </p>
              <p className="mt-1 text-xs text-muted-foreground">{ext.ifGranted.detail}</p>
            </div>
            <div className="rounded-md border p-3 text-sm">
              <p className="mb-1 font-semibold text-red-600">IF REFUSED</p>
              <p className="text-xs text-muted-foreground">{ext.ifRefused}</p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Button size="sm">
              <Check className="mr-1 h-4 w-4" /> Grant +{ext.minutes}
            </Button>
            <Button size="sm" variant="outline">
              Grant +20
            </Button>
            <Button size="sm" variant="outline" className="text-red-600">
              <X className="mr-1 h-4 w-4" /> Refuse
            </Button>
            <Input
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Reason…"
              className="max-w-xs"
            />
          </div>
        </CardContent>
      </Card>

      {/* Timeline */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Timeline</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap items-center gap-2 text-xs">
            {TIMELINE.map((t, i) => (
              <span key={t} className="flex items-center gap-2">
                <span className="rounded bg-muted px-2 py-1 font-mono">{t}</span>
                {i < TIMELINE.length - 1 && <span className="text-muted-foreground">─</span>}
              </span>
            ))}
          </div>
          <Button variant="ghost" size="sm" className="mt-3">
            Full event log
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
