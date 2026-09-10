'use client';

import Link from 'next/link';
import { ArrowLeft, ShieldCheck, ShieldAlert, Clock } from 'lucide-react';
import { PageHeader } from '@/components/page-header';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { StatusBadge } from '@/components/status-badge';
import { Skeleton } from '@/components/ui/skeleton';
import { ErrorState } from '@/components/error-state';
import { useBlockRequest, useUpdateExecutionState } from '@/lib/hooks';
import { formatDateTime } from '@/lib/format';

// OPUS-5 Part H execution state machine.
const EXECUTION_STEPS = [
  { key: 'requested', label: 'Requested' },
  { key: 'approved', label: 'Approved' },
  { key: 'granted', label: 'Granted' },
  { key: 'protected', label: 'Protected' },
  { key: 'isolated', label: 'Isolated' },
  { key: 'working', label: 'Working' },
  { key: 'handed_back', label: 'Handed Back' },
  { key: 'closed', label: 'Closed' },
];

const POWER_STATES = [
  { key: 'not_requested', label: 'Not Requested' },
  { key: 'requested', label: 'Requested' },
  { key: 'granted', label: 'Granted' },
  { key: 'earthed', label: 'Earthed' },
  { key: 'earth_removed', label: 'Earth Removed' },
];

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <p className="text-sm text-muted-foreground">{label}</p>
      <p className="font-medium">{value ?? '—'}</p>
    </div>
  );
}

export default function RequestDetailPage({ params }: { params: { id: string } }) {
  const { data: request, isLoading, error } = useBlockRequest(params.id);
  const updateExecution = useUpdateExecutionState(params.id);

  const exec = request?.execution;
  const currentIdx = exec ? EXECUTION_STEPS.findIndex((s) => s.key === exec.execution_state) : -1;

  // The next legal transition (for the "advance" button).
  const nextStep =
    currentIdx >= 0 && currentIdx < EXECUTION_STEPS.length - 1 ? EXECUTION_STEPS[currentIdx + 1] : null;

  const advance = () => {
    if (!nextStep) return;
    // Safety gate (SR-038): to reach WORKING the power block must be EARTHED.
    if (nextStep.key === 'working' && exec?.power_block_state !== 'earthed') {
      updateExecution.mutate({ power_block_state: 'earthed', execution_state: 'working' });
    } else {
      updateExecution.mutate({ execution_state: nextStep.key });
    }
  };

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <Link href="/requests">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back
          </Button>
        </Link>
        <Link href={`/requests/${params.id}/approve`}>
          <Button size="sm">
            <ShieldCheck className="mr-2 h-4 w-4" />
            Approve (J7)
          </Button>
        </Link>
      </div>

      {isLoading ? (
        <Card>
          <CardContent className="pt-6 space-y-2">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-6 w-full" />
            ))}
          </CardContent>
        </Card>
      ) : error || !request ? (
        <ErrorState title="Failed to load request" message="Could not fetch this block request." />
      ) : (
        <div className="space-y-6">
          <PageHeader
            title={`Request ${request.id.slice(0, 8)}`}
            description={`${request.request_type} · ${request.block_class} · ${request.work_type || 'no work type'}`}
          />

          {/* Status summary */}
          <div className="grid gap-4 lg:grid-cols-4">
            <Card>
              <CardContent className="pt-6">
                <div className="text-center">
                  <p className="text-sm text-muted-foreground">Status</p>
                  <div className="mt-2">
                    <StatusBadge status={request.status} />
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="text-center">
                  <p className="text-sm text-muted-foreground">Criticality</p>
                  <p className="text-lg font-semibold mt-2 capitalize">{request.criticality}</p>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="text-center">
                  <p className="text-sm text-muted-foreground">Lead Time</p>
                  <p className={`text-lg font-semibold mt-2 ${request.is_late ? 'text-destructive' : ''}`}>
                    {request.lead_time_days ?? '—'} days
                    {request.is_late && <span className="ml-1 text-sm">⚠ late</span>}
                  </p>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="text-center">
                  <p className="text-sm text-muted-foreground">Adjacent Line</p>
                  <p className="text-lg font-semibold mt-2 capitalize">{request.adjacent_line_status || '—'}</p>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Execution state machine (OPUS-5 Part H) */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <Clock className="h-4 w-4" /> Execution &amp; Safety State
              </CardTitle>
              {nextStep && (
                <Button size="sm" onClick={advance} disabled={updateExecution.isPending}>
                  {updateExecution.isPending ? 'Updating…' : `Advance to ${nextStep.label}`}
                </Button>
              )}
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Execution timeline */}
              <div className="flex flex-wrap items-center gap-2">
                {EXECUTION_STEPS.map((step, i) => {
                  const done = i <= currentIdx;
                  const active = i === currentIdx;
                  return (
                    <div key={step.key} className="flex items-center gap-2">
                      <div
                        className={`rounded-full px-3 py-1 text-xs font-medium ${
                          active
                            ? 'bg-primary text-primary-foreground'
                            : done
                              ? 'bg-primary/20 text-primary'
                              : 'bg-muted text-muted-foreground'
                        }`}
                      >
                        {step.label}
                      </div>
                      {i < EXECUTION_STEPS.length - 1 && <span className="text-muted-foreground">→</span>}
                    </div>
                  );
                })}
              </div>

              {/* Power block state (SR-038) — distinct, separately confirmed */}
              <div className="rounded-lg border p-4">
                <div className="flex items-center gap-2 mb-3">
                  {exec?.power_block_state === 'earthed' ? (
                    <ShieldCheck className="h-4 w-4 text-emerald-500" />
                  ) : (
                    <ShieldAlert className="h-4 w-4 text-amber-500" />
                  )}
                  <p className="font-medium">Power Block (OHE Isolation)</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  {POWER_STATES.map((p) => (
                    <span
                      key={p.key}
                      className={`rounded px-2 py-0.5 text-xs ${
                        exec?.power_block_state === p.key
                          ? 'bg-primary text-primary-foreground'
                          : 'bg-muted text-muted-foreground'
                      }`}
                    >
                      {p.label}
                    </span>
                  ))}
                </div>
                {exec?.earthed_at && (
                  <p className="text-sm text-muted-foreground mt-2">
                    Earthed at {formatDateTime(exec.earthed_at)}
                    {exec.earthed_by ? ` by ${exec.earthed_by}` : ''}
                  </p>
                )}
              </div>

              {/* Actuals (F1 principle 5) */}
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                <Field label="Granted At" value={exec?.granted_at ? formatDateTime(exec.granted_at) : null} />
                <Field label="Protected At" value={exec?.protected_at ? formatDateTime(exec.protected_at) : null} />
                <Field label="Work Started" value={exec?.work_started_at ? formatDateTime(exec.work_started_at) : null} />
                <Field label="Work Ended" value={exec?.work_ended_at ? formatDateTime(exec.work_ended_at) : null} />
                <Field label="Handed Back" value={exec?.handed_back_at ? formatDateTime(exec.handed_back_at) : null} />
                <Field label="Handed Back By" value={exec?.handed_back_by} />
                <Field label="Imposed Speed" value={exec?.imposed_speed_kmph ? `${exec.imposed_speed_kmph} kmph` : null} />
                <Field label="Quantum Completed" value={exec?.quantum_completed ?? null} />
                <Field
                  label="Open Disconnection"
                  value={exec?.has_open_disconnection ? '⚠ Yes (blocks hand-back)' : 'No'}
                />
              </div>
            </CardContent>
          </Card>

          {/* Structured demand (OPUS-5 Part G) */}
          <Card>
            <CardHeader>
              <CardTitle>Structured Demand</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              <Field label="Block Class" value={<span className="capitalize">{request.block_class}</span>} />
              <Field label="Origin Type" value={<span className="capitalize">{request.origin_type}</span>} />
              <Field label="Work Type" value={request.work_type} />
              <Field
                label="Quantum"
                value={request.quantum != null ? `${request.quantum} ${request.quantum_unit || ''}`.trim() : null}
              />
              <Field
                label="Est. Duration"
                value={request.estimated_duration_minutes != null ? `${request.estimated_duration_minutes} min` : null}
              />
              <Field label="Priority" value={<span className="capitalize">{request.priority}</span>} />
              <div className="sm:col-span-2 lg:col-span-3">
                <Field label="Consequence of Deferral" value={request.consequence_of_deferral} />
              </div>
            </CardContent>
          </Card>

          {/* Request details */}
          <Card>
            <CardHeader>
              <CardTitle>Request Details</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              <Field label="Requested Start" value={formatDateTime(request.requested_start)} />
              <Field label="Requested End" value={formatDateTime(request.requested_end)} />
              <Field label="Submitted" value={request.submitted_at ? formatDateTime(request.submitted_at) : '—'} />
              <Field label="Created" value={formatDateTime(request.created_at)} />
              <Field label="Department" value={request.department_id.slice(0, 8)} />
              <Field label="Requester" value={request.requested_by_user_id.slice(0, 8)} />
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
