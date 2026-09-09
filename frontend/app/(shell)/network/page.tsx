'use client';

import { useTracks } from '@/lib/hooks';
import { PageHeader } from '@/components/page-header';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { ErrorState } from '@/components/error-state';
import { FreshnessIndicator } from '@/components/freshness-indicator';

export default function NetworkPage() {
  const { data: tracks = [], isLoading, error, refetch } = useTracks();

  if (error && !isLoading) {
    return (
      <div>
        <PageHeader title="Track Network" description="Visualize the railway track network and dependencies." />
        <ErrorState
          title="Failed to load tracks"
          message="Could not fetch network data. Please try again."
          onRetry={() => refetch()}
        />
      </div>
    );
  }

  // Group tracks by section for visualization
  const tracksBySection = tracks.reduce(
    (acc, track) => {
      const section = track.section_name || 'Unknown';
      if (!acc[section]) acc[section] = [];
      acc[section].push(track);
      return acc;
    },
    {} as Record<string, typeof tracks>
  );

  const sections = Object.keys(tracksBySection).sort();

  return (
    <div>
      <PageHeader title="Track Network" description="Visualize the railway track network and dependencies." />

      {isLoading ? (
        <Card>
          <CardContent className="pt-6">
            <div className="space-y-4">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-32 w-full" />
              ))}
            </div>
          </CardContent>
        </Card>
      ) : tracks.length === 0 ? (
        <Card>
          <CardContent className="pt-6">
            <p className="text-muted-foreground">No tracks found in the network.</p>
          </CardContent>
        </Card>
      ) : (
        <>
          {/* Network Overview Card */}
          <Card className="mb-6">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Network Overview</CardTitle>
                {tracks.length > 0 && <FreshnessIndicator syncedAt={tracks[0].synced_at} />}
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 sm:grid-cols-4">
                <div className="text-center">
                  <p className="text-sm text-muted-foreground">Sections</p>
                  <p className="text-3xl font-bold mt-2">{sections.length}</p>
                </div>
                <div className="text-center">
                  <p className="text-sm text-muted-foreground">Total Tracks</p>
                  <p className="text-3xl font-bold mt-2">{tracks.length}</p>
                </div>
                <div className="text-center">
                  <p className="text-sm text-muted-foreground">Active Tracks</p>
                  <p className="text-3xl font-bold mt-2">{tracks.filter((t) => t.is_active).length}</p>
                </div>
                <div className="text-center">
                  <p className="text-sm text-muted-foreground">Inactive Tracks</p>
                  <p className="text-3xl font-bold mt-2">{tracks.filter((t) => !t.is_active).length}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Sections View */}
          <div className="space-y-4">
            {sections.map((section) => (
              <Card key={section}>
                <CardHeader>
                  <CardTitle className="text-lg">{section}</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {tracksBySection[section].map((track) => (
                      <div
                        key={track.track_id}
                        className={`flex items-center justify-between p-3 rounded-md border ${
                          track.is_active
                            ? 'bg-green-50 dark:bg-green-950 border-green-200 dark:border-green-800'
                            : 'bg-gray-50 dark:bg-gray-900 border-gray-200 dark:border-gray-800'
                        }`}
                      >
                        <div>
                          <p className="font-medium">{track.code} — {track.name}</p>
                          <p className="text-sm text-muted-foreground">
                            {track.line && `Line: ${track.line} `}
                            {track.direction && `| Direction: ${track.direction}`}
                          </p>
                        </div>
                        <span
                          className={`text-xs px-2 py-1 rounded font-medium ${
                            track.is_active
                              ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-100'
                              : 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-100'
                          }`}
                        >
                          {track.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          {/* Info Card */}
          <Card className="mt-6 bg-blue-50 dark:bg-blue-950 border-blue-200 dark:border-blue-800">
            <CardContent className="pt-6">
              <p className="text-sm text-blue-900 dark:text-blue-100">
                <strong>Note:</strong> This is a tabular view of the track network. A full schematic diagram with React Flow will be added in a later version to show track dependencies and block locations visually.
              </p>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
