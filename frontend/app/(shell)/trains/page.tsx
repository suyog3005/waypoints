'use client';

import Link from 'next/link';
import { useTrains } from '@/lib/hooks';
import { PageHeader } from '@/components/page-header';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { ErrorState } from '@/components/error-state';
import { EmptyState } from '@/components/empty-state';
import { formatDateTime } from '@/lib/format';

export default function TrainsPage() {
  const { data: trains = [], isLoading, error, refetch } = useTrains();

  if (error && !isLoading) {
    return (
      <div>
        <PageHeader title="Trains" description="View all active and inactive trains." />
        <ErrorState
          title="Failed to load trains"
          message="Could not fetch trains. Please try again."
          onRetry={() => refetch()}
        />
      </div>
    );
  }

  return (
    <div>
      <PageHeader title="Trains" description="View all active and inactive trains." />

      <div className="mt-6">
        {isLoading ? (
          <Card>
            <CardHeader>
              <CardTitle>Loading trains...</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {Array.from({ length: 5 }).map((_, i) => (
                  <Skeleton key={i} className="h-12 w-full" />
                ))}
              </div>
            </CardContent>
          </Card>
        ) : trains.length === 0 ? (
          <EmptyState
            title="No trains found"
            description="There are no trains in the system."
          />
        ) : (
          <Card>
            <CardHeader>
              <CardTitle>{trains.length} Train{trains.length !== 1 ? 's' : ''}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b">
                      <th className="text-left p-2 font-medium">Train Number</th>
                      <th className="text-left p-2 font-medium">Type</th>
                      <th className="text-left p-2 font-medium">Schedules</th>
                      <th className="text-left p-2 font-medium">Status</th>
                      <th className="text-left p-2 font-medium">Last Synced</th>
                      <th className="text-left p-2 font-medium">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {trains.map((train) => (
                      <tr key={train.train_id} className="border-b hover:bg-accent">
                        <td className="p-2 font-medium">{train.train_number}</td>
                        <td className="p-2 text-muted-foreground">{train.train_type || '—'}</td>
                        <td className="p-2">{train.schedule_count}</td>
                        <td className="p-2">
                          <span
                            className={`text-xs px-2 py-1 rounded ${
                              train.is_active
                                ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-100'
                                : 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-100'
                            }`}
                          >
                            {train.is_active ? 'Active' : 'Inactive'}
                          </span>
                        </td>
                        <td className="p-2 text-xs text-muted-foreground">
                          {formatDateTime(train.synced_at)}
                        </td>
                        <td className="p-2">
                          <Link
                            href={`/trains/${train.train_id}`}
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
