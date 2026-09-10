'use client';

import Link from 'next/link';
import { Plus } from 'lucide-react';
import { PageHeader } from '@/components/page-header';
import { FilterBar } from '@/components/filter-bar';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { StatusBadge } from '@/components/status-badge';
import { Skeleton } from '@/components/ui/skeleton';
import { ErrorState } from '@/components/error-state';
import { EmptyState } from '@/components/empty-state';
import { formatDateTime } from '@/lib/format';
import { useSearchParams } from 'next/navigation';
import { Suspense } from 'react';
import { useBlockRequests, useTracks } from '@/lib/hooks';

function RequestsContent() {
  const searchParams = useSearchParams();
  const status = searchParams.get('status');

  const { data: requests = [], isLoading, error } = useBlockRequests(status);
  const { data: tracks = [] } = useTracks();
  const trackCode = (id: string) => tracks.find((t) => t.id === id)?.code ?? id.slice(0, 8);

  return (
    <div>
      <PageHeader
        title="Block Requests"
        description="View and manage block requests."
      >
        <Link href="/requests/new">
          <Button>
            <Plus className="mr-2 h-4 w-4" />
            New Request
          </Button>
        </Link>
      </PageHeader>

      <FilterBar
        statusOptions={[
          { label: 'Draft', value: 'DRAFT' },
          { label: 'Submitted', value: 'SUBMITTED' },
          { label: 'Approved', value: 'APPROVED' },
          { label: 'Rejected', value: 'REJECTED' },
          { label: 'Superseded', value: 'SUPERSEDED' },
        ]}
      />

      <div className="mt-6">
        {isLoading ? (
          <Card>
            <CardHeader>
              <CardTitle>Loading requests...</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {Array.from({ length: 5 }).map((_, i) => (
                  <Skeleton key={i} className="h-12 w-full" />
                ))}
              </div>
            </CardContent>
          </Card>
        ) : error ? (
          <ErrorState
            title="Failed to load requests"
            message="Could not fetch block requests. Please try again."
          />
        ) : requests.length === 0 ? (
          <EmptyState
            title="No block requests found"
            description="Create a new block request to get started."
          />
        ) : (
          <Card>
            <CardHeader>
              <CardTitle>
                {requests.length} Request{requests.length !== 1 ? 's' : ''}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b">
                      <th className="text-left p-2 font-medium">Request ID</th>
                      <th className="text-left p-2 font-medium">Track</th>
                      <th className="text-left p-2 font-medium">Work Type</th>
                      <th className="text-left p-2 font-medium">Class</th>
                      <th className="text-left p-2 font-medium">Criticality</th>
                      <th className="text-left p-2 font-medium">Start</th>
                      <th className="text-left p-2 font-medium">Status</th>
                      <th className="text-left p-2 font-medium">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {requests.map((req) => (
                      <tr key={req.id} className="border-b hover:bg-accent">
                        <td className="p-2 font-medium">{req.id.slice(0, 8)}</td>
                        <td className="p-2 text-muted-foreground">{trackCode(req.track_id)}</td>
                        <td className="p-2">{req.work_type || '—'}</td>
                        <td className="p-2 capitalize">{req.block_class}</td>
                        <td className="p-2 capitalize">{req.criticality}</td>
                        <td className="p-2 text-xs">
                          {formatDateTime(req.requested_start)}
                        </td>
                        <td className="p-2">
                          <StatusBadge status={req.status} />
                        </td>
                        <td className="p-2">
                          <Link
                            href={`/requests/${req.id}`}
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

export default function RequestsPage() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <RequestsContent />
    </Suspense>
  );
}
