'use client';

import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useState } from 'react';
import { PageHeader } from '@/components/page-header';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useCreateBlockRequest } from '@/lib/hooks';
import { toast } from 'sonner';

// Validation schema
const blockRequestSchema = z.object({
  request_type: z.enum(['technical', 'operational']),
  track_id: z.string().min(1, 'Track is required'),
  requested_start: z.string().min(1, 'Start time is required'),
  requested_end: z.string().min(1, 'End time is required'),
  priority: z.enum(['normal', 'high', 'emergency']).default('normal'),
  is_emergency: z.boolean().default(false),
  // Technical fields
  train_stops: z.string().optional(),
  railway_line: z.string().optional(),
  direction: z.string().optional(),
  restriction_type: z.string().optional(),
  train_type: z.string().optional(),
  finance_reference: z.string().optional(),
  // Operational fields
  reason: z.string().optional(),
  reason_details: z.string().optional(),
  expected_duration_minutes: z.number().optional(),
  safety_notes: z.string().optional(),
});

type BlockRequestFormData = z.infer<typeof blockRequestSchema>;

export default function NewRequestPage() {
  const [requestType, setRequestType] = useState<'technical' | 'operational'>('technical');
  const createBlockRequest = useCreateBlockRequest();

  const {
    register,
    handleSubmit,
    formState: { errors },
    watch,
  } = useForm<BlockRequestFormData>({
    resolver: zodResolver(blockRequestSchema),
    defaultValues: {
      request_type: 'technical',
      priority: 'normal',
      is_emergency: false,
    },
  });

  const typeValue = watch('request_type');

  const onSubmit = async (data: BlockRequestFormData) => {
    // TODO: Wire with actual API submission
    // For now, show form structure
    toast.info('Form submitted. API wiring needed.');
    console.log('Form data:', data);
  };

  return (
    <div>
      <PageHeader
        title="New Block Request"
        description="Create a new block request for track maintenance or operations."
      />

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
            {/* Request Type Selection */}
            <Card>
              <CardHeader>
                <CardTitle>Request Type</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex gap-4">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="radio"
                      value="technical"
                      {...register('request_type')}
                      onChange={() => setRequestType('technical')}
                      defaultChecked
                    />
                    <span>Technical</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="radio"
                      value="operational"
                      {...register('request_type')}
                      onChange={() => setRequestType('operational')}
                    />
                    <span>Operational</span>
                  </label>
                </div>
              </CardContent>
            </Card>

            {/* Common Fields */}
            <Card>
              <CardHeader>
                <CardTitle>Basic Information</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-2">Track</label>
                  <Input
                    placeholder="Track ID or code"
                    {...register('track_id')}
                  />
                  {errors.track_id && (
                    <p className="text-destructive text-sm mt-1">{errors.track_id.message}</p>
                  )}
                </div>

                <div className="grid gap-4 sm:grid-cols-2">
                  <div>
                    <label className="block text-sm font-medium mb-2">Start Time</label>
                    <Input
                      type="datetime-local"
                      {...register('requested_start')}
                    />
                    {errors.requested_start && (
                      <p className="text-destructive text-sm mt-1">{errors.requested_start.message}</p>
                    )}
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2">End Time</label>
                    <Input
                      type="datetime-local"
                      {...register('requested_end')}
                    />
                    {errors.requested_end && (
                      <p className="text-destructive text-sm mt-1">{errors.requested_end.message}</p>
                    )}
                  </div>
                </div>

                <div className="grid gap-4 sm:grid-cols-2">
                  <div>
                    <label className="block text-sm font-medium mb-2">Priority</label>
                    <select
                      {...register('priority')}
                      className="w-full border rounded px-3 py-2"
                    >
                      <option value="normal">Normal</option>
                      <option value="high">High</option>
                      <option value="emergency">Emergency</option>
                    </select>
                  </div>
                  <div>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input type="checkbox" {...register('is_emergency')} />
                      <span className="text-sm font-medium">Emergency</span>
                    </label>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Technical Fields */}
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
                      <select {...register('direction')} className="w-full border rounded px-3 py-2">
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

            {/* Operational Fields */}
            {requestType === 'operational' && (
              <Card>
                <CardHeader>
                  <CardTitle>Operational Details</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium mb-2">Reason</label>
                    <select {...register('reason')} className="w-full border rounded px-3 py-2">
                      <option value="">Select reason</option>
                      <option value="BRIDGE">Bridge work</option>
                      <option value="UNDERPASS">Underpass work</option>
                      <option value="ROAD_CROSSING">Road crossing</option>
                      <option value="TREE_WORK">Tree work</option>
                      <option value="OTHER">Other</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-2">Reason Details</label>
                    <textarea
                      placeholder="Additional details about the work"
                      className="w-full border rounded px-3 py-2 min-h-24"
                      {...register('reason_details')}
                    />
                  </div>

                  <div className="grid gap-4 sm:grid-cols-2">
                    <div>
                      <label className="block text-sm font-medium mb-2">Expected Duration (minutes)</label>
                      <Input type="number" placeholder="60" {...register('expected_duration_minutes', { valueAsNumber: true })} />
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-2">Safety Notes</label>
                    <textarea
                      placeholder="Safety precautions and notes"
                      className="w-full border rounded px-3 py-2 min-h-24"
                      {...register('safety_notes')}
                    />
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Submit */}
            <div className="flex gap-4">
              <Button type="submit" disabled={createBlockRequest.isPending}>
                {createBlockRequest.isPending ? 'Submitting...' : 'Submit Request'}
              </Button>
              <Button variant="outline" type="reset">
                Reset
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
                <p className="font-medium text-foreground">Technical Requests</p>
                <p>Used for scheduled maintenance, track work, and signal upgrades.</p>
              </div>
              <div>
                <p className="font-medium text-foreground">Operational Requests</p>
                <p>Used for external work like bridge/road crossing repairs or tree work.</p>
              </div>
              <div>
                <p className="font-medium text-foreground">Emergency</p>
                <p>Mark as emergency for urgent blocks requiring immediate planning.</p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
