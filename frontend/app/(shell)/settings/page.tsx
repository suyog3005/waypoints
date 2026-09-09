'use client';

import { Settings as SettingsIcon, Moon, Sun, Bell } from 'lucide-react';
import { useTheme } from 'next-themes';
import { PageHeader } from '@/components/page-header';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

export default function SettingsPage() {
  const { theme, setTheme } = useTheme();

  return (
    <div>
      <PageHeader
        title="Settings"
        description="Configure your preferences and account settings."
      />

      <div className="grid gap-6 max-w-2xl">
        {/* Theme Settings */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Appearance</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <p className="text-sm font-medium mb-3">Theme</p>
              <div className="flex gap-2">
                <Button
                  variant={theme === 'light' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setTheme('light')}
                  className="flex items-center gap-2"
                >
                  <Sun className="h-4 w-4" />
                  Light
                </Button>
                <Button
                  variant={theme === 'dark' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setTheme('dark')}
                  className="flex items-center gap-2"
                >
                  <Moon className="h-4 w-4" />
                  Dark
                </Button>
                <Button
                  variant={theme === 'system' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setTheme('system')}
                >
                  System
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Department Settings */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Department</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2">Active Department</label>
              <select className="w-full border rounded px-3 py-2">
                <option value="">Select department...</option>
                <option value="dept1">Infrastructure Division</option>
                <option value="dept2">Operations Division</option>
                <option value="dept3">Maintenance Division</option>
              </select>
            </div>
          </CardContent>
        </Card>

        {/* Notification Settings */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Notifications</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-3">
              <label className="flex items-center gap-3 cursor-pointer">
                <input type="checkbox" defaultChecked className="rounded" />
                <span className="text-sm font-medium">Plan updates</span>
              </label>
              <label className="flex items-center gap-3 cursor-pointer">
                <input type="checkbox" defaultChecked className="rounded" />
                <span className="text-sm font-medium">Block request approvals</span>
              </label>
              <label className="flex items-center gap-3 cursor-pointer">
                <input type="checkbox" defaultChecked className="rounded" />
                <span className="text-sm font-medium">Optimization results</span>
              </label>
              <label className="flex items-center gap-3 cursor-pointer">
                <input type="checkbox" className="rounded" />
                <span className="text-sm font-medium">System alerts</span>
              </label>
            </div>
          </CardContent>
        </Card>

        {/* API Settings */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">API Configuration</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2">API Gateway URL</label>
              <input
                type="text"
                value={process.env.NEXT_PUBLIC_API_GATEWAY_URL || 'http://localhost:8000'}
                readOnly
                className="w-full border rounded px-3 py-2 bg-muted text-muted-foreground"
              />
              <p className="text-xs text-muted-foreground mt-2">
                This is configured via NEXT_PUBLIC_API_GATEWAY_URL environment variable.
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Info Section */}
        <Card className="bg-blue-50 dark:bg-blue-950 border-blue-200 dark:border-blue-800">
          <CardContent className="pt-6">
            <p className="text-sm text-blue-900 dark:text-blue-100">
              <strong>Note:</strong> User authentication (RBAC, organization hierarchy, approval workflows) is planned for future releases. For now, this is a stub showing the settings interface.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
