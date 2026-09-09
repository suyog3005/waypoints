'use client';

import { Bell, AlertTriangle, CheckCircle } from 'lucide-react';
import { PageHeader } from '@/components/page-header';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { EmptyState } from '@/components/empty-state';

export default function AlertsPage() {
  // Placeholder: In production, this would fetch alerts from Kafka topics or an event stream
  const alerts: any[] = [];

  return (
    <div>
      <PageHeader
        title="Alerts"
        description="Real-time notifications and events from the optimization system."
      />

      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <CardContent className="pt-6">
            <div className="text-center">
              <AlertTriangle className="h-8 w-8 text-amber-500 mx-auto mb-2" />
              <p className="text-sm text-muted-foreground">Critical Alerts</p>
              <p className="text-2xl font-bold mt-2">0</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-center">
              <Bell className="h-8 w-8 text-blue-500 mx-auto mb-2" />
              <p className="text-sm text-muted-foreground">Warnings</p>
              <p className="text-2xl font-bold mt-2">0</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-center">
              <CheckCircle className="h-8 w-8 text-green-500 mx-auto mb-2" />
              <p className="text-sm text-muted-foreground">Info</p>
              <p className="text-2xl font-bold mt-2">0</p>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card className="mt-6">
        <CardHeader>
          <CardTitle>Recent Activity</CardTitle>
        </CardHeader>
        <CardContent>
          {alerts.length === 0 ? (
            <EmptyState
              title="No alerts"
              description="All systems running smoothly. You'll see notifications here when events occur."
            />
          ) : (
            <div className="space-y-4">
              {alerts.map((alert, i) => (
                <div key={i} className="flex items-start gap-4 p-4 rounded-lg border">
                  {alert.severity === 'critical' && (
                    <AlertTriangle className="h-5 w-5 text-amber-500 flex-shrink-0 mt-0.5" />
                  )}
                  {alert.severity === 'warning' && (
                    <Bell className="h-5 w-5 text-blue-500 flex-shrink-0 mt-0.5" />
                  )}
                  {alert.severity === 'info' && (
                    <CheckCircle className="h-5 w-5 text-green-500 flex-shrink-0 mt-0.5" />
                  )}
                  <div className="flex-1">
                    <p className="font-medium">{alert.title}</p>
                    <p className="text-sm text-muted-foreground mt-1">{alert.message}</p>
                    <p className="text-xs text-muted-foreground mt-2">{alert.timestamp}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card className="mt-6 bg-amber-50 dark:bg-amber-950 border-amber-200 dark:border-amber-800">
        <CardContent className="pt-6">
          <p className="text-sm text-amber-900 dark:text-amber-100">
            <strong>Coming Soon:</strong> This page will display real-time alerts from the optimization system, including plan updates, block request status changes, and system events. Integration with Kafka and Sonner toast notifications is planned for a future release.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
