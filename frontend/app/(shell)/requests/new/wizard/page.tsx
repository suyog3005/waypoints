"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import {
  MapPin,
  Hammer,
  Clock,
  Wrench,
  ChevronLeft,
  ChevronRight,
  Zap,
  GitMerge,
  AlertTriangle,
  Check,
  Sparkles,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { SemanticBadge } from "@/components/semantic-badge";
import {
  useCreateBlockRequest,
  useDepartments,
  useUsers,
  useTracks,
} from "@/lib/hooks";
import {
  getImpact,
  getBetterWindows,
  getNearbyDemands,
} from "@/lib/demo-data";
import { cn } from "@/lib/utils";

/**
 * OPUS-5 Part J5 — New demand (map-first wizard).
 *
 * "The form is not a form. It is a map with a panel that fills itself in."
 * Four steps: WHERE → WHAT → WHEN → HOW. The requester sees the cost of
 * their own request before anyone argues with them, and is offered a better
 * option with the reasoning attached (J5 "why this design works").
 *
 * The map canvas in step 1 is a schematic extent drawer (the full map-draw
 * gesture is Part K). Submission reuses the real create-block-request hook.
 */

const STEPS = [
  { key: "where", label: "WHERE", icon: MapPin },
  { key: "what", label: "WHAT", icon: Hammer },
  { key: "when", label: "WHEN", icon: Clock },
  { key: "how", label: "HOW", icon: Wrench },
] as const;

const BLOCK_CLASSES = [
  { value: "routine", label: "Routine" },
  { value: "corridor", label: "Corridor" },
  { value: "mega", label: "Mega / Weekend" },
  { value: "major_works", label: "Major Works" },
  { value: "project", label: "Project" },
  { value: "third_party", label: "Third Party" },
  { value: "short_micro", label: "Short / Micro" },
  { value: "emergency", label: "Emergency" },
];

const ORIGIN_TYPES = [
  { value: "defect", label: "Defect" },
  { value: "statutory", label: "Statutory" },
  { value: "condition_based", label: "Condition-based" },
  { value: "project", label: "Project" },
  { value: "failure", label: "Failure" },
  { value: "directive", label: "Directive" },
  { value: "audit", label: "Audit" },
  { value: "ad_hoc", label: "Ad-hoc" },
];

const CRITICALITIES = [
  { value: "safety_critical", label: "Safety-critical" },
  { value: "high", label: "High" },
  { value: "medium", label: "Medium" },
  { value: "low", label: "Low" },
];

const ADJACENT = [
  { value: "open", label: "Open" },
  { value: "cautioned", label: "Cautioned" },
  { value: "blocked", label: "Blocked" },
  { value: "physical_barrier", label: "Physical barrier" },
  { value: "lookout_posted", label: "Lookout posted" },
];

const QUANTUM_UNITS = ["rails", "sleepers", "metres", "spans", "masts", "points", "joints", "cables", "km"];

function Select({
  label,
  value,
  onChange,
  options,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: { value: string; label: string }[];
  placeholder?: string;
}) {
  return (
    <div>
      <label className="mb-1 block text-sm font-medium">{label}</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded border bg-background px-3 py-2 text-sm"
      >
        {placeholder && <option value="">{placeholder}</option>}
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </div>
  );
}

export default function NewDemandWizardPage() {
  const router = useRouter();
  const createBlockRequest = useCreateBlockRequest();
  const { data: departments = [] } = useDepartments();
  const { data: users = [] } = useUsers();
  const { data: tracks = [] } = useTracks();

  const [step, setStep] = useState(0);

  // ── WHERE ────────────────────────────────────────────────────────────
  const [trackId, setTrackId] = useState("");
  const [fromKm, setFromKm] = useState("412.100");
  const [toKm, setToKm] = useState("413.500");
  const [powerBlock, setPowerBlock] = useState(false);

  // ── WHAT ─────────────────────────────────────────────────────────────
  const [blockClass, setBlockClass] = useState("routine");
  const [originType, setOriginType] = useState("ad_hoc");
  const [criticality, setCriticality] = useState("medium");
  const [workType, setWorkType] = useState("");
  const [quantum, setQuantum] = useState("");
  const [quantumUnit, setQuantumUnit] = useState("km");
  const [consequence, setConsequence] = useState("");

  // ── WHEN ─────────────────────────────────────────────────────────────
  const [date, setDate] = useState("2026-09-21");
  const [startTime, setStartTime] = useState("10:00");
  const [endTime, setEndTime] = useState("14:00");
  const [flexibility, setFlexibility] = useState("±3 hours");

  // ── HOW ──────────────────────────────────────────────────────────────
  const [departmentId, setDepartmentId] = useState("");
  const [userId, setUserId] = useState("");
  const [adjacent, setAdjacent] = useState("blocked");

  const lengthKm = useMemo(() => {
    const a = parseFloat(fromKm);
    const b = parseFloat(toKm);
    return isNaN(a) || isNaN(b) ? 0 : Math.abs(b - a);
  }, [fromKm, toKm]);

  const seed = `${trackId}-${fromKm}-${toKm}-${date}-${startTime}`;
  const impact = useMemo(() => getImpact(seed), [seed]);
  const windows = useMemo(() => getBetterWindows(seed), [seed]);
  const nearby = useMemo(() => getNearbyDemands(seed), [seed]);

  const canSubmit = trackId && departmentId && userId && workType;

  const submit = async () => {
    const start = new Date(`${date}T${startTime}:00`);
    const end = new Date(`${date}T${endTime}:00`);
    try {
      const res = await createBlockRequest.mutateAsync({
        department_id: departmentId,
        requested_by_user_id: userId,
        request_type: "technical",
        track_id: trackId,
        requested_start: start.toISOString(),
        requested_end: end.toISOString(),
        block_class: blockClass,
        origin_type: originType,
        criticality,
        work_type: workType,
        quantum: quantum ? Number(quantum) : undefined,
        quantum_unit: quantumUnit,
        estimated_duration_minutes: Math.round((end.getTime() - start.getTime()) / 60000),
        adjacent_line_status: adjacent,
        consequence_of_deferral: consequence || null,
      });
      router.push(`/requests/${res.id}`);
    } catch {
      // toast handled by hook
    }
  };

  return (
    <div className="space-y-4">
      {/* Header + step indicator */}
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold">New block demand</h1>
        <div className="flex items-center gap-2">
          {STEPS.map((s, i) => (
            <div key={s.key} className="flex items-center gap-2">
              <div
                className={cn(
                  "flex h-7 w-7 items-center justify-center rounded-full text-xs font-semibold",
                  i === step
                    ? "bg-primary text-primary-foreground"
                    : i < step
                      ? "bg-primary/20 text-primary"
                      : "bg-muted text-muted-foreground",
                )}
              >
                {i < step ? <Check className="h-3.5 w-3.5" /> : i + 1}
              </div>
              {i < STEPS.length - 1 && <span className="text-muted-foreground">—</span>}
            </div>
          ))}
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        {/* ── LEFT: map / context ─────────────────────────────────────── */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">
              {STEPS[step].label} — {step === 0 ? "Draw the extent" : step === 1 ? "What work" : step === 2 ? "When" : "How"}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {step === 0 && (
              <div className="space-y-3">
                {/* Schematic extent drawer (map-draw gesture is Part K) */}
                <div className="rounded-lg border bg-gradient-to-br from-slate-50 to-slate-100 p-4 dark:from-slate-950 dark:to-slate-900">
                  <p className="mb-2 text-xs text-muted-foreground">Schematic extent (UP Main)</p>
                  <div className="relative h-16">
                    <div className="absolute top-6 left-0 right-0 h-1 rounded bg-slate-300 dark:bg-slate-700" />
                    <div
                      className="absolute top-4 h-5 rounded bg-red-500/80"
                      style={{ left: "10%", width: `${Math.min(80, lengthKm * 40)}%` }}
                    />
                    <span className="absolute top-1 left-[10%] text-[10px] font-mono">{fromKm}</span>
                    <span className="absolute top-1 right-[10%] text-[10px] font-mono">{toKm}</span>
                  </div>
                  <p className="mt-2 text-center text-xs font-medium">
                    Length {lengthKm.toFixed(3)} km
                  </p>
                </div>

                {/* Derived unavailability */}
                <div className="rounded-md border p-3">
                  <p className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold">
                    <AlertTriangle className="h-3.5 w-3.5 text-amber-500" /> Also becomes unavailable (3)
                  </p>
                  <ul className="space-y-1 text-xs text-muted-foreground">
                    <li>• UP Loop — only crossover CO/14 lies inside the worksite</li>
                    <li>• Platform 3 at SBB — reachable only via the blocked extent</li>
                    <li>• Siding S/12 — placement not possible</li>
                  </ul>
                </div>

                {/* Electrically dead if power block */}
                <label className="flex cursor-pointer items-center gap-2 rounded-md border p-3 text-xs">
                  <input
                    type="checkbox"
                    checked={powerBlock}
                    onChange={(e) => setPowerBlock(e.target.checked)}
                    className="h-4 w-4 accent-blue-600"
                  />
                  <Zap className="h-4 w-4 text-yellow-500" />
                  <span>
                    <span className="font-semibold">Power block required</span> — electrically dead if
                    power block: E-7 (SBB–GZB, 6.2 km, 2 stations)
                  </span>
                </label>

                {/* Nearby open demands (bundling) */}
                <div className="rounded-md border p-3">
                  <p className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold">
                    <GitMerge className="h-3.5 w-3.5 text-violet-500" /> Nearby open demands ({nearby.length})
                  </p>
                  <ul className="space-y-1 text-xs">
                    {nearby.map((d) => (
                      <li key={d.id} className="flex items-center justify-between">
                        <span>
                          {d.id} {d.dept} {d.km} {d.durationH}h
                        </span>
                        {d.canBundle && (
                          <SemanticBadge stateKey="bundle" label="can bundle" showSwatch={false} />
                        )}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            )}

            {step === 1 && (
              <div className="space-y-3 text-sm">
                <p className="text-muted-foreground">
                  Describe the work. This is what the approver and the optimiser use to
                  schedule, bundle and check competency.
                </p>
                <div className="rounded-md border p-3 text-xs">
                  <p className="font-medium">Extent</p>
                  <p className="text-muted-foreground">
                    {tracks.find((t) => t.track_id === trackId)?.code ?? "—"} · km {fromKm}–{toKm} · {lengthKm.toFixed(3)} km
                  </p>
                </div>
                <p className="text-xs text-muted-foreground">
                  Consequence of deferral is shown to the approver so they can weigh the cost of
                  saying no (Part G).
                </p>
              </div>
            )}

            {step === 2 && (
              <div className="space-y-3">
                {/* Live impact */}
                <div className="rounded-md border p-3">
                  <p className="mb-2 flex items-center gap-1.5 text-xs font-semibold">
                    <Sparkles className="h-3.5 w-3.5 text-violet-500" /> Live impact (updates as you choose)
                  </p>
                  <p className="mb-2 text-xs text-muted-foreground">
                    As chosen: {date} {startTime}–{endTime}
                  </p>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <ImpactRow label="Affected trains" value={String(impact.affectedTrains)} />
                    <ImpactRow label="Detention" value={`${impact.detentionMin} min`} warn={impact.detentionMin > 200} />
                    <ImpactRow label="Cancellations" value={String(impact.cancellations)} warn={impact.cancellations > 0} />
                    <ImpactRow label="Freight delayed" value={`${impact.freightDelayedT} t`} />
                    <ImpactRow label="Passengers" value={`~${impact.passengersAffected}`} />
                    <ImpactRow label="Indicative cost" value={`₹ ${(impact.indicativeCostINR / 100000).toFixed(2)}L`} />
                  </div>
                  <p className="mt-2 text-[11px] text-muted-foreground">Confidence: {impact.confidence}</p>
                  {impact.protectedServicesAffected > 0 && (
                    <p className="mt-1 flex items-center gap-1 text-[11px] text-amber-600">
                      <AlertTriangle className="h-3 w-3" /> {impact.protectedServicesAffected} protected services affected
                    </p>
                  )}
                </div>

                {/* Better windows */}
                <div className="rounded-md border p-3">
                  <p className="mb-2 text-xs font-semibold">✦ Better windows</p>
                  <div className="space-y-2">
                    {windows.map((w) => (
                      <div key={w.label} className={cn("rounded-md border p-2 text-xs", w.best && "border-violet-400 bg-violet-50 dark:bg-violet-950/30")}>
                        <div className="flex items-center justify-between">
                          <span className="font-medium">{w.label}</span>
                          <span className="text-emerald-600">−{w.savingPct}%</span>
                        </div>
                        <p className="text-muted-foreground">
                          {w.detentionMin} min · {w.cancellations} cancel
                          {w.best && " ★ best"}
                        </p>
                        {w.note && <p className="mt-0.5 text-[11px] text-violet-600">{w.note}</p>}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {step === 3 && (
              <div className="space-y-3 text-sm">
                <p className="text-muted-foreground">
                  Confirm ownership and method. The approver sees competency, machine and
                  gang readiness here (J7).
                </p>
                <div className="rounded-md border p-3 text-xs">
                  <p className="font-medium">Summary</p>
                  <ul className="mt-1 space-y-0.5 text-muted-foreground">
                    <li>Class: <span className="capitalize text-foreground">{blockClass}</span></li>
                    <li>Work: {workType || "—"}</li>
                    <li>When: {date} {startTime}–{endTime} ({flexibility})</li>
                    <li>Impact: {impact.affectedTrains} trains · {impact.detentionMin} min detention</li>
                  </ul>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* ── RIGHT: form fields ──────────────────────────────────────── */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">
              {step + 1} {STEPS[step].label}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {step === 0 && (
              <>
                <Select label="Between (track)" value={trackId} onChange={setTrackId} placeholder="Select track…" options={tracks.map((t) => ({ value: t.track_id, label: `${t.code} — ${t.name}` }))} />
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="mb-1 block text-sm font-medium">From km</label>
                    <Input value={fromKm} onChange={(e) => setFromKm(e.target.value)} />
                  </div>
                  <div>
                    <label className="mb-1 block text-sm font-medium">To km</label>
                    <Input value={toKm} onChange={(e) => setToKm(e.target.value)} />
                  </div>
                </div>
              </>
            )}

            {step === 1 && (
              <>
                <Select label="Block class" value={blockClass} onChange={setBlockClass} options={BLOCK_CLASSES} />
                <Select label="Origin type" value={originType} onChange={setOriginType} options={ORIGIN_TYPES} />
                <Select label="Criticality" value={criticality} onChange={setCriticality} options={CRITICALITIES} />
                <div>
                  <label className="mb-1 block text-sm font-medium">Work type</label>
                  <Input value={workType} onChange={(e) => setWorkType(e.target.value)} placeholder="e.g. Through packing" />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="mb-1 block text-sm font-medium">Quantum</label>
                    <Input value={quantum} onChange={(e) => setQuantum(e.target.value)} placeholder="1.4" />
                  </div>
                  <Select label="Unit" value={quantumUnit} onChange={setQuantumUnit} options={QUANTUM_UNITS.map((u) => ({ value: u, label: u }))} />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium">Consequence of deferral</label>
                  <Input value={consequence} onChange={(e) => setConsequence(e.target.value)} placeholder="e.g. rail defect may propagate" />
                </div>
              </>
            )}

            {step === 2 && (
              <>
                <div>
                  <label className="mb-1 block text-sm font-medium">Preferred date</label>
                  <Input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="mb-1 block text-sm font-medium">Start time</label>
                    <Input type="time" value={startTime} onChange={(e) => setStartTime(e.target.value)} />
                  </div>
                  <div>
                    <label className="mb-1 block text-sm font-medium">End time</label>
                    <Input type="time" value={endTime} onChange={(e) => setEndTime(e.target.value)} />
                  </div>
                </div>
                <Select label="Flexibility" value={flexibility} onChange={setFlexibility} options={["Fixed", "±3 hours", "Any time", "Night only"].map((f) => ({ value: f, label: f }))} />
              </>
            )}

            {step === 3 && (
              <>
                <Select label="Department" value={departmentId} onChange={setDepartmentId} placeholder="Select department…" options={departments.map((d) => ({ value: d.id, label: d.name }))} />
                <Select label="Requester" value={userId} onChange={setUserId} placeholder="Select requester…" options={users.map((u) => ({ value: u.id, label: u.full_name }))} />
                <Select label="Adjacent line" value={adjacent} onChange={setAdjacent} options={ADJACENT} />
              </>
            )}

            {/* Nav */}
            <div className="flex items-center justify-between pt-2">
              <Button variant="ghost" size="sm" onClick={() => setStep((s) => Math.max(0, s - 1))} disabled={step === 0}>
                <ChevronLeft className="mr-1 h-4 w-4" /> Back
              </Button>
              {step < STEPS.length - 1 ? (
                <Button size="sm" onClick={() => setStep((s) => Math.min(STEPS.length - 1, s + 1))}>
                  Next: {STEPS[step + 1].label} <ChevronRight className="ml-1 h-4 w-4" />
                </Button>
              ) : (
                <Button size="sm" onClick={submit} disabled={!canSubmit || createBlockRequest.isPending}>
                  {createBlockRequest.isPending ? "Submitting…" : "Submit demand"}
                </Button>
              )}
            </div>
            {step === 3 && !canSubmit && (
              <p className="text-xs text-muted-foreground">
                Select a track, department, requester and work type to submit.
              </p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function ImpactRow({ label, value, warn }: { label: string; value: string; warn?: boolean }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-muted-foreground">{label}</span>
      <span className={cn("font-medium", warn && "text-amber-600")}>{value}</span>
    </div>
  );
}
