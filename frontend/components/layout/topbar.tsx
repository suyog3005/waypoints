"use client";

import { usePathname } from "next/navigation";
import { ThemeToggle } from "@/components/theme-toggle";
import { CorrelationIdBadge } from "@/components/correlation-id-badge";

const titles: Record<string, string> = {
  "/dashboard": "Dashboard",
  "/requests": "Block Requests",
  "/plans": "Plans",
  "/network": "Track Network",
  "/trains": "Trains",
  "/alerts": "Alerts",
  "/settings": "Settings",
};

export function Topbar() {
  const pathname = usePathname();
  const title =
    titles[pathname] ??
    (pathname.startsWith("/requests")
      ? "Block Requests"
      : pathname.startsWith("/plans")
        ? "Plans"
        : pathname.startsWith("/trains")
          ? "Trains"
          : "Block Planner");

  return (
    <header className="flex h-14 items-center justify-between border-b bg-background px-4">
      <h1 className="text-base font-semibold">{title}</h1>
      <div className="flex items-center gap-2">
        <CorrelationIdBadge />
        <ThemeToggle />
      </div>
    </header>
  );
}
