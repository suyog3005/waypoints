'use client';

import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';
import { useTrains } from '@/lib/hooks';
import { PageHeader } from '@/components/page-header';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { formatDateTime } from '@/lib/format';

interface TrainDetailPageProps {
  params: {
    id: string;
  };
}

export default function TrainDetailPage({ params }: TrainDetailPageProps) {
  const { data: trains = [], isLoading } = useTrains();
  const train = trains.find((t) => t.train_id === params.id);

  return (
    <div>
      <div className="mb-6 flex items-center gap-2">
        <Link href="/trains">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back
          </Button>
        </Link>
      </div>

      <PageHeader
        title={train ? train.train_number : 'Train Details'}
        description={train ? `Type: ${train.train_type || 'Unknown'}` : 'Loading...'}
      />

      {isLoading ? (
        <Card>
          <CardContent className="pt-6">
            <div className="space-y-2">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-6 w-full" />
              ))}
            </div>
          </CardContent>
        </Card>
      ) : !train ? (
        <Card>
          <CardContent className="pt-6">
            <p className="text-muted-foreground">Train not found.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-6">
          <div className="grid gap-4 lg:grid-cols-4">
            <Card>
              <CardContent className="pt-6">
                <div className="text-center">
                  <p className="text-sm text-muted-foreground">Train Number</p>
                  <p className="text-2xl font-bold mt-2">{train.train_number}</p>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="text-center">
                  <p className="text-sm text-muted-foreground">Type</p>
                  <p className="text-xl font-medium mt-2">{train.train_type || '—'}</p>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="text-center">
                  <p className="text-sm text-muted-foreground">Schedules</p>
                  <p className="text-2xl font-bold mt-2">{train.schedule_count}</p>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="text-center">
                  <p className="text-sm text-muted-foreground">Status</p>
                  <div className="mt-2">
                    <span
                      className={`text-sm px-3 py-1 rounded font-medium ${
                        train.is_active
                          ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-100'
                          : 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-100'
                      }`}
                    >
                      {train.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Train Information</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <p className="text-sm text-muted-foreground">Train ID</p>
                  <p className="font-medium">{train.train_id}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Last Synced</p>
                  <p className="font-medium">{formatDateTime(train.synced_at)}</p>
                </div>
              </div>

              <div className="bg-amber-50 dark:bg-amber-950 border border-amber-200 dark:border-amber-800 rounded p-4">
                <p className="text-sm text-amber-900 dark:text-amber-100">
                  <strong>Note:</strong> Detailed schedule information and delay history will be available in Phase 9C.
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
