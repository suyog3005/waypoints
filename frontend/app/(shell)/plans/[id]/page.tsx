'use client';

import { usePlans, useBlocks } from '@/lib/hooks';
import { PageHeader } from '@/components/page-header';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { StatusBadge } from '@/components/status-badge';
import { Skeleton } from '@/components/ui/skeleton';
import { ErrorState } from '@/components/error-state';
import { formatDateTime } from '@/lib/format';
import { FreshnessIndicator } from '@/components/freshness-indicator';
import { BlockGantt } from '@/components/block-gantt';

interface PlanDetailPageProps {
  params: {
    id: string;
  };
}

export default function PlanDetailPage({ params }: PlanDetailPageProps) {
  const { data: plans = [], isLoading: plansLoading, error: plansError, refetch: refetchPlans } = usePlans();
  const plan = plans.find((p) => p.plan_id === params.id);

  const { data: blocks = [], isLoading: blocksLoading, error: blocksError, refetch: refetchBlocks } = useBlocks({
    plan_id: params.id,
  });

  if ((plansError || blocksError) && !plansLoading && !blocksLoading) {
    return (
      <div>
        <PageHeader title="Plan Details" description="View plan details and blocks." />
        <ErrorState
          title="Failed to load plan details"
          message="Could not fetch plan details. Please try again."
          onRetry={() => {
            refetchPlans();
            refetchBlocks();
          }}
        />
      </div>
    );
  }

  if (plansLoading) {
    return (
      <div>
        <PageHeader title="Plan Details" description="Loading..." />
        <Card>
          <CardContent className="pt-6">
            <div className="space-y-2">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-6 w-full" />
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!plan) {
    return (
      <div>
        <PageHeader title="Plan Not Found" />
        <Card>
          <CardContent className="pt-6">
            <p className="text-muted-foreground">Plan with ID {params.id} not found.</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        title={plan.section_name}
        description={`Plan Status: ${plan.status}`}
      />

      <div className="grid gap-4 lg:grid-cols-4">
        <Card>
          <CardContent className="pt-6">
            <div className="text-center">
              <p className="text-sm text-muted-foreground">Status</p>
              <div className="mt-2">
                <StatusBadge status={plan.status} />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-center">
              <p className="text-sm text-muted-foreground">Blocks</p>
              <p className="text-2xl font-bold mt-2">{plan.block_count}</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-center">
              <p className="text-sm text-muted-foreground">Requests</p>
              <p className="text-2xl font-bold mt-2">{plan.request_count}</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-center">
              <p className="text-sm text-muted-foreground">Duration</p>
              <p className="text-2xl font-bold mt-2">
                {(plan.total_block_duration_minutes / 60).toFixed(1)}h
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card className="mt-6">
        <CardHeader>
          <CardTitle>Plan Metadata</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <p className="text-sm text-muted-foreground">Division</p>
              <p className="font-medium">{plan.division_name || '—'}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Zone</p>
              <p className="font-medium">{plan.zone_name || '—'}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Created</p>
              <p className="font-medium">{formatDateTime(plan.created_at)}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Last Synced</p>
              <p className="font-medium">{formatDateTime(plan.synced_at)}</p>
            </div>
          </div>
          <div className="mt-4">
            <FreshnessIndicator syncedAt={plan.synced_at} />
          </div>
        </CardContent>
      </Card>

      <Card className="mt-6">
        <CardHeader>
          <CardTitle>Block Schedule Visualization</CardTitle>
        </CardHeader>
        <CardContent>
          {blocksLoading ? (
            <Skeleton className="h-96 w-full" />
          ) : blocks.length === 0 ? (
            <p className="text-sm text-muted-foreground">No blocks to visualize.</p>
          ) : (
            <BlockGantt blocks={blocks} planId={params.id} />
          )}
        </CardContent>
      </Card>

      <Card className="mt-6">
        <CardHeader>
          <CardTitle>Blocks in this Plan</CardTitle>
        </CardHeader>
        <CardContent>
          {blocksLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : blocks.length === 0 ? (
            <p className="text-sm text-muted-foreground">No blocks in this plan.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b">
                    <th className="text-left p-2 font-medium">Track</th>
                    <th className="text-left p-2 font-medium">Start</th>
                    <th className="text-left p-2 font-medium">End</th>
                    <th className="text-left p-2 font-medium">Duration (min)</th>
                    <th className="text-left p-2 font-medium">Merged</th>
                    <th className="text-left p-2 font-medium">Requests</th>
                  </tr>
                </thead>
                <tbody>
                  {blocks.map((block) => {
                    const start = new Date(block.start_time);
                    const end = new Date(block.end_time);
                    const duration = (end.getTime() - start.getTime()) / 60000;
                    return (
                      <tr key={block.block_id} className="border-b hover:bg-accent">
                        <td className="p-2 font-medium">{block.track_code}</td>
                        <td className="p-2 text-xs">{formatDateTime(block.start_time)}</td>
                        <td className="p-2 text-xs">{formatDateTime(block.end_time)}</td>
                        <td className="p-2">{Math.round(duration)}</td>
                        <td className="p-2">{block.is_merged ? '✓' : '—'}</td>
                        <td className="p-2">{block.request_count}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
