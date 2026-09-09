'use client';

import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';
import { PageHeader } from '@/components/page-header';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { StatusBadge } from '@/components/status-badge';
import { Skeleton } from '@/components/ui/skeleton';

interface RequestDetailPageProps {
  params: {
    id: string;
  };
}

export default function RequestDetailPage({ params }: RequestDetailPageProps) {
  // TODO: Wire with useBlockRequest(id) hook once API endpoint is available
  const isLoading = false;
  const request: any = null;

  return (
    <div>
      <div className="mb-6 flex items-center gap-2">
        <Link href="/requests">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back
          </Button>
        </Link>
      </div>

      <PageHeader
        title={request ? `Request ${request.id.slice(0, 8)}` : 'Request Details'}
        description={request ? `${request.request_type} request` : 'Loading...'}
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
      ) : !request ? (
        <Card>
          <CardContent className="pt-6">
            <p className="text-muted-foreground">Request not found.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-6">
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
                  <p className="text-sm text-muted-foreground">Type</p>
                  <p className="text-lg font-semibold mt-2 capitalize">{request.request_type}</p>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="text-center">
                  <p className="text-sm text-muted-foreground">Priority</p>
                  <p className="text-lg font-semibold mt-2 capitalize">{request.priority}</p>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="text-center">
                  <p className="text-sm text-muted-foreground">Emergency</p>
                  <p className="text-lg font-semibold mt-2">{request.is_emergency ? '⚠️ Yes' : 'No'}</p>
                </div>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Request Details</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <p className="text-sm text-muted-foreground">Track</p>
                  <p className="font-medium">{request.track_id || '—'}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Department</p>
                  <p className="font-medium">{request.department_id}</p>
                </div>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <p className="text-sm text-muted-foreground">Requested Start</p>
                  <p className="font-medium">{new Date(request.requested_start).toLocaleString()}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Requested End</p>
                  <p className="font-medium">{new Date(request.requested_end).toLocaleString()}</p>
                </div>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <p className="text-sm text-muted-foreground">Created</p>
                  <p className="font-medium">{new Date(request.created_at).toLocaleString()}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Submitted</p>
                  <p className="font-medium">
                    {request.submitted_at ? new Date(request.submitted_at).toLocaleString() : '—'}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
