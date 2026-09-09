'use client';

import Link from 'next/link';
import { usePlans } from '@/lib/hooks';
import { PageHeader } from '@/components/page-header';
import { FilterBar } from '@/components/filter-bar';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { StatusBadge } from '@/components/status-badge';
import { Skeleton } from '@/components/ui/skeleton';
import { ErrorState } from '@/components/error-state';
import { EmptyState } from '@/components/empty-state';
import { formatDateTime } from '@/lib/format';
import { useSearchParams } from 'next/navigation';
import { Suspense } from 'react';

function PlansContent() {
  const searchParams = useSearchParams();
  const status = searchParams.get('status');
  const sectionId = searchParams.get('section_id');

  const { data: plans = [], isLoading, error, refetch } = usePlans({
    status: status || undefined,
    section_id: sectionId || undefined,
  });

  if (error && !isLoading) {
    return (
      <div>
        <PageHeader title="Plans" description="View and filter all plans." />
        <ErrorState
          title="Failed to load plans"
          message="Could not fetch plans. Please try again."
          onRetry={() => refetch()}
        />
      </div>
    );
  }

  return (
    <div>
      <PageHeader title="Plans" description="View and filter all plans." />

      <FilterBar
        statusOptions={[
          { label: 'Proposed', value: 'proposed' },
          { label: 'Approved', value: 'approved' },
          { label: 'Active', value: 'active' },
          { label: 'Completed', value: 'completed' },
          { label: 'Superseded', value: 'superseded' },
          { label: 'Cancelled', value: 'cancelled' },
        ]}
      />

      <div className="mt-6">
        {isLoading ? (
          <Card>
            <CardHeader>
              <CardTitle>Loading plans...</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {Array.from({ length: 5 }).map((_, i) => (
                  <Skeleton key={i} className="h-12 w-full" />
                ))}
              </div>
            </CardContent>
          </Card>
        ) : plans.length === 0 ? (
          <EmptyState
            title="No plans found"
            description="Try adjusting your filters or create a new plan."
          />
        ) : (
          <Card>
            <CardHeader>
              <CardTitle>{plans.length} Plan{plans.length !== 1 ? 's' : ''}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b">
                      <th className="text-left p-2 font-medium">Section</th>
                      <th className="text-left p-2 font-medium">Division</th>
                      <th className="text-left p-2 font-medium">Blocks</th>
                      <th className="text-left p-2 font-medium">Requests</th>
                      <th className="text-left p-2 font-medium">Duration (h)</th>
                      <th className="text-left p-2 font-medium">Status</th>
                      <th className="text-left p-2 font-medium">Created</th>
                      <th className="text-left p-2 font-medium">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {plans.map((plan) => (
                      <tr key={plan.plan_id} className="border-b hover:bg-accent">
                        <td className="p-2">{plan.section_name}</td>
                        <td className="p-2 text-muted-foreground">{plan.division_name || '—'}</td>
                        <td className="p-2">{plan.block_count}</td>
                        <td className="p-2">{plan.request_count}</td>
                        <td className="p-2">
                          {(plan.total_block_duration_minutes / 60).toFixed(1)}
                        </td>
                        <td className="p-2">
                          <StatusBadge status={plan.status} />
                        </td>
                        <td className="p-2 text-xs text-muted-foreground">
                          {formatDateTime(plan.created_at)}
                        </td>
                        <td className="p-2">
                          <Link
                            href={`/plans/${plan.plan_id}`}
                            className="text-primary hover:underline"
                          >
                            View
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}

export default function PlansPage() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <PlansContent />
    </Suspense>
  );
}
