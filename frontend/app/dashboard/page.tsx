'use client';

import Link from 'next/link';
import { CalendarRange, FilePlus2, Layers, Merge } from 'lucide-react';
import { usePlans } from '@/lib/hooks';
import { KpiCard } from '@/components/kpi-card';
import { PageHeader } from '@/components/page-header';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { StatusBadge } from '@/components/status-badge';
import { ErrorState } from '@/components/error-state';
import { formatDateTime } from '@/lib/format';

export default function DashboardPage() {
  const { data: plans = [], isLoading, error } = usePlans();

  // Calculate KPIs from plans data
  const activePlans = plans.filter((p) => p.status === 'active').length;
  const totalBlockHours = plans.reduce((sum, p) => sum + p.total_block_duration_minutes, 0) / 60;
  const avgMergeRatio = plans.length > 0
    ? (plans.reduce((sum, p) => sum + (p.block_count > 0 ? (p.request_count / p.block_count) : 0), 0) / plans.length * 100).toFixed(1)
    : '0';

  if (error && !isLoading) {
    return (
      <div>
        <PageHeader
          title="Dashboard"
          description="Overview of plans, requests, and optimization activity."
        />
        <ErrorState
          title="Failed to load dashboard"
          message="Could not fetch plans and metrics. Please try again."
        />
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        title="Dashboard"
        description="Overview of plans, requests, and optimization activity."
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard
          label="Active Plans"
          value={String(activePlans)}
          icon={Layers}
          loading={isLoading}
        />
        <KpiCard
          label="Pending Requests"
          value={String(plans.reduce((sum, p) => sum + p.request_count, 0))}
          icon={FilePlus2}
          loading={isLoading}
        />
        <KpiCard
          label="Block Hours (total)"
          value={totalBlockHours.toFixed(1)}
          icon={CalendarRange}
          loading={isLoading}
        />
        <KpiCard
          label="Avg Merge Ratio"
          value={`${avgMergeRatio}%`}
          icon={Merge}
          loading={isLoading}
        />
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Active &amp; Proposed Plans</CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="space-y-2">
                {Array.from({ length: 4 }).map((_, i) => (
                  <Skeleton key={i} className="h-10 w-full" />
                ))}
              </div>
            ) : plans.length === 0 ? (
              <p className="text-sm text-muted-foreground">No plans found.</p>
            ) : (
              <div className="space-y-2">
                {plans.slice(0, 5).map((plan) => (
                  <div
                    key={plan.plan_id}
                    className="flex items-center justify-between rounded-md border p-2 text-sm hover:bg-accent"
                  >
                    <div className="flex-1">
                      <Link
                        href={`/plans/${plan.plan_id}`}
                        className="hover:underline font-medium"
                      >
                        {plan.section_name}
                      </Link>
                      <p className="text-xs text-muted-foreground">
                        {plan.block_count} blocks, {plan.request_count} requests
                      </p>
                    </div>
                    <StatusBadge status={plan.status} />
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Recent Block Requests</CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="space-y-2">
                {Array.from({ length: 4 }).map((_, i) => (
                  <Skeleton key={i} className="h-10 w-full" />
                ))}
              </div>
            ) : plans.length === 0 ? (
              <p className="text-sm text-muted-foreground">No block requests found.</p>
            ) : (
              <div className="space-y-2">
                {plans
                  .filter((p) => p.request_count > 0)
                  .slice(0, 5)
                  .map((plan) => (
                    <div
                      key={plan.plan_id}
                      className="flex items-center justify-between rounded-md border p-2 text-sm hover:bg-accent"
                    >
                      <div className="flex-1">
                        <Link
                          href={`/requests`}
                          className="hover:underline font-medium"
                        >
                          {plan.section_name}
                        </Link>
                        <p className="text-xs text-muted-foreground">
                          {plan.request_count} requests pending
                        </p>
                      </div>
                      <StatusBadge status={plan.status} />
                    </div>
                  ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
