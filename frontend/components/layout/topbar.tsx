"use client";

import { usePathname } from "next/navigation";
import { Bell, ChevronDown, User } from "lucide-react";
import { ThemeToggle } from "@/components/theme-toggle";
import { CorrelationIdBadge } from "@/components/correlation-id-badge";

/**
 * OPUS-5 Part J4 — top bar. Division selector, notifications, and the
 * signed-in officer. The page title is derived from the current area.
 */
const TITLES: Record<string, string> = {
  "/situation": "Situation",
  "/plans": "Plan",
  "/plans/new": "Planning workspace",
  "/requests": "Demands",
  "/requests/new": "New demand",
  "/execution": "Execution",
  "/execution/console": "Live block console",
  "/resources": "Resources",
  "/infrastructure/map": "Map",
  "/network": "Network",
  "/trains": "Trains",
  "/analytics": "Analytics",
  "/settings": "Admin",
  "/alerts": "Alerts",
};

function titleFor(pathname: string): string {
  if (TITLES[pathname]) return TITLES[pathname];
  if (pathname.startsWith("/requests")) return "Demands";
  if (pathname.startsWith("/plans")) return "Plan";
  if (pathname.startsWith("/execution")) return "Execution";
  if (pathname.startsWith("/trains")) return "Trains";
  return "Block Planner";
}

export function Topbar() {
  const pathname = usePathname();
  const title = titleFor(pathname);

  return (
    <header className="flex h-14 items-center justify-between border-b bg-background px-4">
      <div className="flex items-center gap-3">
        <h1 className="text-base font-semibold">{title}</h1>
        <button className="flex items-center gap-1 rounded-md border px-2 py-1 text-xs text-muted-foreground hover:bg-accent">
          Division: DLI <ChevronDown className="h-3 w-3" />
        </button>
      </div>
      <div className="flex items-center gap-2">
        <button className="relative rounded-md p-1.5 text-muted-foreground hover:bg-accent" aria-label="Notifications">
          <Bell className="h-4 w-4" />
          <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-destructive px-1 text-[10px] font-semibold text-destructive-foreground">
            4
          </span>
        </button>
        <div className="flex items-center gap-1.5 rounded-md border px-2 py-1 text-xs">
          <User className="h-3.5 w-3.5 text-muted-foreground" />
          <span className="font-medium">Sr.DOM</span>
        </div>
        <CorrelationIdBadge />
        <ThemeToggle />
      </div>
    </header>
  );
}
