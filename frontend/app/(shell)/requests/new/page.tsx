'use client';

import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { PageHeader } from '@/components/page-header';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import { useCreateBlockRequest, useDepartments, useUsers, useTracks } from '@/lib/hooks';
import { toast } from 'sonner';

// ── OPUS-5 Part G structured demand options ──────────────────────────
const BLOCK_CLASSES = [
  { value: 'routine', label: 'Routine' },
  { value: 'corridor', label: 'Corridor' },
  { value: 'mega', label: 'Mega / Weekend' },
  { value: 'major_works', label: 'Major Works / Commissioning' },
  { value: 'project', label: 'Project' },
  { value: 'third_party', label: 'Third Party' },
  { value: 'short_micro', label: 'Short / Micro' },
  { value: 'emergency', label: 'Emergency' },
  { value: 'restoration', label: 'Restoration' },
  { value: 'security', label: 'Security' },
];

const ORIGIN_TYPES = [
  { value: 'defect', label: 'Defect' },
  { value: 'statutory', label: 'Statutory' },
  { value: 'condition_based', label: 'Condition-based' },
  { value: 'project', label: 'Project' },
  { value: 'failure', label: 'Failure' },
  { value: 'directive', label: 'Directive' },
  { value: 'audit', label: 'Audit' },
  { value: 'ad_hoc', label: 'Ad-hoc' },
];

const CRITICALITIES = [
  { value: 'safety_critical', label: 'Safety-critical' },
  { value: 'high', label: 'High' },
  { value: 'medium', label: 'Medium' },
  { value: 'low', label: 'Low' },
];

const ADJACENT_LINE_STATUSES = [
  { value: 'open', label: 'Open' },
  { value: 'cautioned', label: 'Cautioned' },
  { value: 'blocked', label: 'Blocked' },
  { value: 'physical_barrier', label: 'Physical barrier' },
  { value: 'lookout_posted', label: 'Lookout posted' },
];

const QUANTUM_UNITS = ['rails', 'sleepers', 'metres', 'spans', 'masts', 'points', 'joints', 'cables', 'km'];

// Minimum notice period (days) per block class — mirrors the backend
// (OPUS-5 Part F5). Used to show a live lead-time / late indicator (SR-002).
const NOTICE_PERIOD_DAYS: Record<string, number> = {
  routine: 14,
  corridor: 365,
  mega: 30,
  major_works: 60,
  project: 90,
  third_party: 45,
  short_micro: 1,
  emergency: 0,
  restoration: 0,
  security: 0,
};

const blockRequestSchema = z
  .object({
    department_id: z.string().min(1, 'Department is required'),
    requested_by_user_id: z.string().min(1, 'Requester is required'),
    request_type: z.enum(['technical', 'operational']),
    track_id: z.string().min(1, 'Track is required'),
    requested_start: z.string().min(1, 'Start time is required'),
    requested_end: z.string().min(1, 'End time is required'),
    priority: z.enum(['normal', 'high', 'emergency']).default('normal'),
    is_emergency: z.boolean().default(false),
    // Structured demand (OPUS-5 Part G).
    block_class: z.string().default('routine'),
    origin_type: z.string().default('ad_hoc'),
    criticality: z.string().default('medium'),
    consequence_of_deferral: z.string().optional(),
    work_type: z.string().optional(),
    quantum: z.number().optional(),
    quantum_unit: z.string().optional(),
    estimated_duration_minutes: z.number().optional(),
    adjacent_line_status: z.string().optional(),
    // Technical fields.
    train_stops: z.string().optional(),
    railway_line: z.string().optional(),
    direction: z.string().optional(),
    restriction_type: z.string().optional(),
    train_type: z.string().optional(),
    finance_reference: z.string().optional(),
    // Operational fields.
    reason: z.string().optional(),
    reason_details: z.string().optional(),
    expected_duration_minutes: z.number().optional(),
    safety_notes: z.string().optional(),
  })
  .refine((d) => new Date(d.requested_end) > new Date(d.requested_start), {
    message: 'End time must be after start time',
    path: ['requested_end'],
  });

type BlockRequestFormData = z.infer<typeof blockRequestSchema>;

function SelectField({
  label,
  value,
  onChange,
  options,
  placeholder,
  error,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: { value: string; label: string }[];
  placeholder?: string;
  error?: string;
}) {
  return (
    <div>
      <label className="block text-sm font-medium mb-2">{label}</label>
      <select value={value} onChange={(e) => onChange(e.target.value)} className="w-full border rounded px-3 py-2 bg-background">
        {placeholder && <option value="">{placeholder}</option>}
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
      {error && <p className="text-destructive text-sm mt-1">{error}</p>}
    </div>
  );
}

export default function NewRequestPage() {
  const router = useRouter();
  const [requestType, setRequestType] = useState<'technical' | 'operational'>('technical');
  const createBlockRequest = useCreateBlockRequest();

  const { data: departments = [], isLoading: loadingDepts } = useDepartments();
  const { data: users = [], isLoading: loadingUsers } = useUsers();
  const { data: tracks = [], isLoading: loadingTracks } = useTracks();

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors },
  } = useForm<BlockRequestFormData>({
    resolver: zodResolver(blockRequestSchema),
    defaultValues: {
      request_type: 'technical',
      priority: 'normal',
      is_emergency: false,
      block_class: 'routine',
      origin_type: 'ad_hoc',
      criticality: 'medium',
    },
  });

  const typeValue = watch('request_type');
  const blockClass = watch('block_class');
  const requestedStart = watch('requested_start');
  const isEmergency = watch('is_emergency');

  // Live lead-time / late indicator (SR-002).
  const leadDays = requestedStart ? Math.floor((new Date(requestedStart).getTime() - Date.now()) / 86400000) : null;
  const notice = NOTICE_PERIOD_DAYS[blockClass] ?? 14;
  const isLate = leadDays !== null && leadDays < notice;

  const onSubmit = async (data: BlockRequestFormData) => {
    const technical =
      data.request_type === 'technical'
        ? {
            train_stops: data.train_stops || null,
            railway_line: data.railway_line || null,
            direction: data.direction || null,
            restriction_type: data.restriction_type || null,
            train_type: data.train_type || null,
            finance_reference: data.finance_reference || null,
          }
        : null;
    const operational =
      data.request_type === 'operational'
        ? {
            reason: data.reason || 'OTHER',
            reason_details: data.reason_details || null,
            expected_duration_minutes: data.expected_duration_minutes ?? null,
            safety_notes: data.safety_notes || null,
          }
        : null;

    const payload = {
      department_id: data.department_id,
      requested_by_user_id: data.requested_by_user_id,
      request_type: data.request_type,
      priority: data.priority,
      track_id: data.track_id,
      requested_start: new Date(data.requested_start).toISOString(),
      requested_end: new Date(data.requested_end).toISOString(),
      is_emergency: data.is_emergency,
      block_class: data.block_class,
      origin_type: data.origin_type,
      criticality: data.criticality,
      consequence_of_deferral: data.consequence_of_deferral || null,
      work_type: data.work_type || null,
      quantum: data.quantum ?? null,
      quantum_unit: data.quantum_unit || null,
      estimated_duration_minutes: data.estimated_duration_minutes ?? null,
      adjacent_line_status: data.adjacent_line_status || null,
      technical,
      operational,
    };

    try {
      const created = await createBlockRequest.mutateAsync(payload);
      toast.success('Block request submitted');
      router.push(`/requests/${created.id}`);
    } catch {
      // toast handled in the hook
    }
  };

  const loading = loadingDepts || loadingUsers || loadingTracks;

  return (
    <div>
      <PageHeader
        title="New Block Request"
        description="Create a structured block request. Fields are validated against the OPUS-5 demand catalogue."
      />

      {loading ? (
        <Card>
          <CardContent className="pt-6 space-y-2">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
              {/* Request Type */}
              <Card>
                <CardHeader>
                  <CardTitle>Request Type</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex gap-4">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input type="radio" value="technical" {...register('request_type')} onChange={() => setRequestType('technical')} />
                      <span>Technical</span>
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input type="radio" value="operational" {...register('request_type')} onChange={() => setRequestType('operational')} />
                      <span>Operational</span>
                    </label>
                  </div>
                </CardContent>
              </Card>

              {/* Origin & ownership */}
              <Card>
                <CardHeader>
                  <CardTitle>Origin &amp; Ownership</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid gap-4 sm:grid-cols-2">
                    <SelectField
                      label="Requesting Department"
                      value={watch('department_id') ?? ''}
                      onChange={(v) => setValue('department_id', v)}
                      options={departments.map((d) => ({ value: d.id, label: `${d.name} (${d.code})` }))}
                      placeholder="Select department"
                      error={errors.department_id?.message}
                    />
                    <SelectField
                      label="Requester"
                      value={watch('requested_by_user_id') ?? ''}
                      onChange={(v) => setValue('requested_by_user_id', v)}
                      options={users.map((u) => ({ value: u.id, label: u.full_name }))}
                      placeholder="Select requester"
                      error={errors.requested_by_user_id?.message}
                    />
                  </div>
                  <div className="grid gap-4 sm:grid-cols-2">
                    <SelectField
                      label="Origin Type"
                      value={watch('origin_type') ?? ''}
                      onChange={(v) => setValue('origin_type', v)}
                      options={ORIGIN_TYPES}
                    />
                    <SelectField
                      label="Block Class"
                      value={watch('block_class') ?? ''}
                      onChange={(v) => setValue('block_class', v)}
                      options={BLOCK_CLASSES}
                    />
                  </div>
                </CardContent>
              </Card>

              {/* Location & time */}
              <Card>
                <CardHeader>
                  <CardTitle>Location &amp; Time</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <SelectField
                    label="Track"
                    value={watch('track_id') ?? ''}
                    onChange={(v) => setValue('track_id', v)}
                    options={tracks.map((t) => ({ value: t.id, label: `${t.code} — ${t.name}` }))}
                    placeholder="Select track"
                    error={errors.track_id?.message}
                  />
                  <div className="grid gap-4 sm:grid-cols-2">
                    <div>
                      <label className="block text-sm font-medium mb-2">Start Time</label>
                      <Input type="datetime-local" {...register('requested_start')} />
                      {errors.requested_start && <p className="text-destructive text-sm mt-1">{errors.requested_start.message}</p>}
                    </div>
                    <div>
                      <label className="block text-sm font-medium mb-2">End Time</label>
                      <Input type="datetime-local" {...register('requested_end')} />
                      {errors.requested_end && <p className="text-destructive text-sm mt-1">{errors.requested_end.message}</p>}
                    </div>
                  </div>
                  {leadDays !== null && (
                    <div className={`rounded px-3 py-2 text-sm ${isLate ? 'bg-destructive/10 text-destructive' : 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400'}`}>
                      Lead time: <strong>{leadDays} days</strong> until start.{' '}
                      {isLate ? `Below the ${notice}-day notice period for ${blockClass} — flagged as late (SR-002).` : `Meets the ${notice}-day notice period for ${blockClass}.`}
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Work & criticality (OPUS-5 Part G) */}
              <Card>
                <CardHeader>
                  <CardTitle>Work &amp; Criticality</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid gap-4 sm:grid-cols-2">
                    <div>
                      <label className="block text-sm font-medium mb-2">
                        Work Type {!isEmergency && <span className="text-destructive">*</span>}
                      </label>
                      <Input placeholder="e.g., Rail renewal, OHE mast replacement" {...register('work_type')} />
                      {errors.work_type && <p className="text-destructive text-sm mt-1">{errors.work_type.message}</p>}
                    </div>
                    <SelectField
                      label="Criticality"
                      value={watch('criticality') ?? ''}
                      onChange={(v) => setValue('criticality', v)}
                      options={CRITICALITIES}
                    />
                  </div>
                  <div className="grid gap-4 sm:grid-cols-3">
                    <div>
                      <label className="block text-sm font-medium mb-2">
                        Quantum {!isEmergency && <span className="text-destructive">*</span>}
                      </label>
                      <Input type="number" placeholder="e.g., 40" {...register('quantum', { valueAsNumber: true })} />
                    </div>
                    <SelectField
                      label="Quantum Unit"
                      value={watch('quantum_unit') ?? ''}
                      onChange={(v) => setValue('quantum_unit', v)}
                      options={QUANTUM_UNITS.map((u) => ({ value: u, label: u }))}
                      placeholder="Select unit"
                    />
                    <div>
                      <label className="block text-sm font-medium mb-2">Est. Duration (min)</label>
                      <Input type="number" placeholder="e.g., 180" {...register('estimated_duration_minutes', { valueAsNumber: true })} />
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2">Consequence of Deferral</label>
                    <textarea
                      placeholder="What happens if this work is not done? (feeds the optimiser as a weight, SR-009)"
                      className="w-full border rounded px-3 py-2 min-h-20"
                      {...register('consequence_of_deferral')}
                    />
                  </div>
                  <div className="grid gap-4 sm:grid-cols-2">
                    <SelectField
                      label="Adjacent Line Status"
                      value={watch('adjacent_line_status') ?? ''}
                      onChange={(v) => setValue('adjacent_line_status', v)}
                      options={ADJACENT_LINE_STATUSES}
                      placeholder="Select (safety, SR-039)"
                    />
                    <div>
                      <label className="block text-sm font-medium mb-2">Priority</label>
                      <select {...register('priority')} className="w-full border rounded px-3 py-2 bg-background">
                        <option value="normal">Normal</option>
                        <option value="high">High</option>
                        <option value="emergency">Emergency</option>
                      </select>
                    </div>
                  </div>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input type="checkbox" {...register('is_emergency')} />
                    <span className="text-sm font-medium">Emergency (minimum-field fast path)</span>
                  </label>
                </CardContent>
              </Card>

              {/* Technical fields */}
              {requestType === 'technical' && (
                <Card>
                  <CardHeader>
                    <CardTitle>Technical Details</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium mb-2">Train Stops</label>
                      <Input placeholder="e.g., Platform 1, Platform 2" {...register('train_stops')} />
                    </div>
                    <div className="grid gap-4 sm:grid-cols-2">
                      <div>
                        <label className="block text-sm font-medium mb-2">Railway Line</label>
                        <Input placeholder="Line name or code" {...register('railway_line')} />
                      </div>
                      <div>
                        <label className="block text-sm font-medium mb-2">Direction</label>
                        <select {...register('direction')} className="w-full border rounded px-3 py-2 bg-background">
                          <option value="">Select direction</option>
                          <option value="up">Up</option>
                          <option value="down">Down</option>
                          <option value="both">Both</option>
                        </select>
                      </div>
                    </div>
                    <div className="grid gap-4 sm:grid-cols-2">
                      <div>
                        <label className="block text-sm font-medium mb-2">Restriction Type</label>
                        <Input placeholder="e.g., FULL_BLOCK, SPEED_RESTRICTION" {...register('restriction_type')} />
                      </div>
                      <div>
                        <label className="block text-sm font-medium mb-2">Train Type</label>
                        <Input placeholder="e.g., PASSENGER, FREIGHT" {...register('train_type')} />
                      </div>
                    </div>
                    <div>
                      <label className="block text-sm font-medium mb-2">Finance Reference</label>
                      <Input placeholder="Cost center or reference number" {...register('finance_reference')} />
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Operational fields */}
              {requestType === 'operational' && (
                <Card>
                  <CardHeader>
                    <CardTitle>Operational Details</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium mb-2">Reason</label>
                      <select {...register('reason')} className="w-full border rounded px-3 py-2 bg-background">
                        <option value="">Select reason</option>
                        <option value="BRIDGE">Bridge work</option>
                        <option value="UNDERPASS">Underpass work</option>
                        <option value="ROAD_CROSSING">Road crossing</option>
                        <option value="TREE_WORK">Tree work</option>
                        <option value="CABLE_MAINTENANCE">Cable maintenance</option>
                        <option value="TRACK_MAINTENANCE">Track maintenance</option>
                        <option value="OTHER">Other</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium mb-2">Reason Details</label>
                      <textarea placeholder="Additional details about the work" className="w-full border rounded px-3 py-2 min-h-24" {...register('reason_details')} />
                    </div>
                    <div>
                      <label className="block text-sm font-medium mb-2">Expected Duration (minutes)</label>
                      <Input type="number" placeholder="60" {...register('expected_duration_minutes', { valueAsNumber: true })} />
                    </div>
                    <div>
                      <label className="block text-sm font-medium mb-2">Safety Notes</label>
                      <textarea placeholder="Safety precautions and notes" className="w-full border rounded px-3 py-2 min-h-24" {...register('safety_notes')} />
                    </div>
                  </CardContent>
                </Card>
              )}

              <div className="flex gap-4">
                <Button type="submit" disabled={createBlockRequest.isPending}>
                  {createBlockRequest.isPending ? 'Submitting...' : 'Submit Request'}
                </Button>
              </div>
            </form>
          </div>

          {/* Info Sidebar */}
          <div>
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Form Guide</CardTitle>
              </CardHeader>
              <CardContent className="text-sm text-muted-foreground space-y-3">
                <div>
                  <p className="font-medium text-foreground">Structured demand</p>
                  <p>Work type, quantum and criticality make the request machine-plannable (SR-004/007/009).</p>
                </div>
                <div>
                  <p className="font-medium text-foreground">Lead time</p>
                  <p>Requests below the class notice period are flagged as late, not silently accepted (SR-002).</p>
                </div>
                <div>
                  <p className="font-medium text-foreground">Safety</p>
                  <p>Adjacent-line status is a first-class safety fact (SR-039).</p>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      )}
    </div>
  );
}
