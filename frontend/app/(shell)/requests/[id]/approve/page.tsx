"use client";

import { useState } from "react";
import {
  Check,
  X,
  RotateCcw,
  GitMerge,
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Phone,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { SemanticBadge } from "@/components/semantic-badge";
import { useBlockRequest } from "@/lib/hooks";
import { getImpact, getRuleFindings } from "@/lib/demo-data";
import { cn } from "@/lib/utils";

/**
 * OPUS-5 Part J7 — Approval screen.
 *
 * "One screen per decision" (J1 principle 2): the demand, the impact, the
 * options, the conflicts and the explanation are all on one screen. The
 * approver never needs a second tab.
 *
 * Left: the request (quantum, method, duration, nominated, adjacent line,
 * machines, gang) + bundle + rule findings. Right: impact + alternatives +
 * explanation. Bottom: the decision actions with a required justification
 * when not adopting the recommended option.
 */

const ALTERNATIVES = [
  { label: "Separate execution", detail: "268 min · 1 cancel" },
  { label: "Sunday as requested", detail: "340 min · 3 cancel" },
  { label: "Defer 1 month", detail: "0 min · risk: none" },
];

export default function ApprovalPage({ params }: { params: { id: string } }) {
  const { data: request } = useBlockRequest(params.id);
  const seed = params.id;
  const impact = getImpact(seed);
  const rules = getRuleFindings(seed);
  const [justification, setJustification] = useState("");
  const [showExplanation, setShowExplanation] = useState(true);

  const req = request;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 className="text-lg font-semibold">
            D-1041 · Through packing · UP Main 411.000–413.500
          </h1>
          <p className="text-sm text-muted-foreground">
            Engineering / SBB sub-division
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs">
          <SemanticBadge stateKey="approved" label="Condition-based" showSwatch={false} />
          <span className="text-muted-foreground">Origin: TRC recording 14 Aug</span>
          <span className="rounded bg-amber-100 px-2 py-0.5 font-medium text-amber-700 dark:bg-amber-900/40 dark:text-amber-300">
            SLA: 2 d 4 h remaining
          </span>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        {/* ── LEFT: request + bundle + rules ─────────────────────────── */}
        <div className="space-y-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">Request</CardTitle>
            </CardHeader>
            <CardContent className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
              <Field label="Quantum" value="1.4 km through packing" />
              <Field label="Method" value="mechanised (tamper)" />
              <Field label="Duration" value="5:35 (bundled)" />
              <Field label="Nominated" value="SSE/P.Way SBB ✓ competent" ok />
              <Field label="Adjacent line" value="BLOCKED ✓" ok />
              <Field label="Machines" value="TM-07 ✓ available" ok />
              <Field label="Materials" value="n/a" />
              <Field label="Gang" value="Gang-14 ✓ rested" ok />
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-sm">
                <GitMerge className="h-4 w-4 text-violet-500" /> Bundle B-07
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <ul className="space-y-1">
                <li>+ D-1043 OHE insulator replacement</li>
                <li>+ D-1047 S&amp;T axle counter alteration</li>
              </ul>
              <p className="text-xs text-muted-foreground">
                Shared: window, protection, isolation
              </p>
              <p className="text-xs font-medium text-emerald-600">
                Saves: 5h45m block time, 176 train-min
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">Rule findings</CardTitle>
            </CardHeader>
            <CardContent className="space-y-1.5">
              {rules.map((r) => (
                <div key={r.code} className="flex items-start gap-2 text-sm">
                  {r.status === "pass" ? (
                    <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-emerald-500" />
                  ) : r.status === "warn" ? (
                    <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-500" />
                  ) : (
                    <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0 text-red-500" />
                  )}
                  <span>
                    <span className="font-mono text-xs text-muted-foreground">{r.code}</span> {r.text}
                  </span>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>

        {/* ── RIGHT: impact + alternatives + explanation ─────────────── */}
        <div className="space-y-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">Impact — Tue 23 Sep 01:00–06:35 (bundled)</CardTitle>
            </CardHeader>
            <CardContent className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
              <Field label="Affected trains" value={String(impact.affectedTrains)} />
              <Field label="Detention" value={`${impact.detentionMin} min`} />
              <Field label="Cancellations" value={String(impact.cancellations)} />
              <Field label="Freight delayed" value={`${impact.freightDelayedT} t`} />
              <Field label="Passengers affected" value={`~${impact.passengersAffected}`} />
              <Field label="Indicative cost" value={`₹ ${(impact.indicativeCostINR / 100000).toFixed(2)}L`} />
              <div className="col-span-2">
                <Field
                  label="Post-block restriction"
                  value="30 kmph, 1.4 km, expected 5 days"
                />
              </div>
              <div className="col-span-2">
                <Field label="Confidence" value={`${impact.confidence} · timetable as at 09:12`} />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">Alternatives</CardTitle>
            </CardHeader>
            <CardContent className="space-y-1.5">
              {ALTERNATIVES.map((a) => (
                <div key={a.label} className="flex items-center justify-between text-sm">
                  <span>{a.label}</span>
                  <span className="text-muted-foreground">{a.detail}</span>
                </div>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between py-2">
              <CardTitle className="text-sm">Explanation</CardTitle>
              <button
                className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
                onClick={() => setShowExplanation((v) => !v)}
              >
                {showExplanation ? <ChevronDown className="h-4 w-4" /> : <ChevronUp className="h-4 w-4" />}
                {showExplanation ? "collapse" : "expand"}
              </button>
            </CardHeader>
            {showExplanation && (
              <CardContent className="text-sm text-muted-foreground">
                Recommended because it forms the highest-value bundle in the horizon and
                avoids all protected services. It schedules the statutory-due item before its
                deadline and uses the Tue night window, saving 5h45m of block time versus
                separate execution.
              </CardContent>
            )}
          </Card>
        </div>
      </div>

      {/* ── Decision actions ─────────────────────────────────────────── */}
      <Card>
        <CardContent className="space-y-3 p-4">
          <div className="flex flex-wrap gap-2">
            <Button size="sm">
              <Check className="mr-1 h-4 w-4" /> Approve as recommended
            </Button>
            <Button size="sm" variant="outline">
              Approve with changes
            </Button>
            <Button size="sm" variant="outline" className="text-red-600">
              <X className="mr-1 h-4 w-4" /> Refuse
            </Button>
            <Button size="sm" variant="ghost">
              <RotateCcw className="mr-1 h-4 w-4" /> Return for info
            </Button>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">
              Justification <span className="text-muted-foreground">(required if not adopting the recommended option)</span>
            </label>
            <Input
              value={justification}
              onChange={(e) => setJustification(e.target.value)}
              placeholder="Explain the decision…"
            />
          </div>
          {req && (
            <p className="text-xs text-muted-foreground">
              Linked request {req.id.slice(0, 8)} · {req.work_type ?? "no work type"} ·{" "}
              {req.criticality}
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function Field({ label, value, ok }: { label: string; value: string; ok?: boolean }) {
  return (
    <div>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className={cn("font-medium", ok && "text-emerald-600 dark:text-emerald-400")}>{value}</p>
    </div>
  );
}
