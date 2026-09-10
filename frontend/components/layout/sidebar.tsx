"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  CalendarRange,
  FilePlus2,
  ClipboardCheck,
  Wrench,
  Network,
  BarChart3,
  Settings,
  Train,
  Map,
  type LucideIcon,
} from "lucide-react";

import { cn } from "@/lib/utils";

/**
 * OPUS-5 Part J3 — Information architecture.
 *
 * Eight top-level areas, each with its own sub-items. The map is the home
 * page (J1 principle 1): SITUATION is the default landing for controllers
 * and officers.
 */
interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
}

interface NavGroup {
  area: string;
  icon: LucideIcon;
  items: NavItem[];
}

const NAV: NavGroup[] = [
  {
    area: "Situation",
    icon: LayoutDashboard,
    items: [{ href: "/situation", label: "Live situation", icon: LayoutDashboard }],
  },
  {
    area: "Plan",
    icon: CalendarRange,
    items: [
      { href: "/plans", label: "Forward calendar", icon: CalendarRange },
      { href: "/plans/new", label: "Planning workspace", icon: CalendarRange },
    ],
  },
  {
    area: "Demands",
    icon: FilePlus2,
    items: [
      { href: "/requests", label: "All demands", icon: FilePlus2 },
      { href: "/requests/new/wizard", label: "New demand", icon: FilePlus2 },
    ],
  },
  {
    area: "Execution",
    icon: ClipboardCheck,
    items: [
      { href: "/execution", label: "Today's blocks", icon: ClipboardCheck },
      { href: "/execution/console", label: "Live block console", icon: ClipboardCheck },
    ],
  },
  {
    area: "Resources",
    icon: Wrench,
    items: [{ href: "/resources", label: "Machines & gangs", icon: Wrench }],
  },
  {
    area: "Network",
    icon: Network,
    items: [
      { href: "/infrastructure/map", label: "Map", icon: Map },
      { href: "/network", label: "Topology", icon: Network },
      { href: "/trains", label: "Trains", icon: Train },
    ],
  },
  {
    area: "Analytics",
    icon: BarChart3,
    items: [{ href: "/analytics", label: "Executive dashboard", icon: BarChart3 }],
  },
  {
    area: "Admin",
    icon: Settings,
    items: [
      { href: "/settings", label: "Users & rules", icon: Settings },
      { href: "/alerts", label: "Alerts", icon: Settings },
    ],
  },
];

export function Sidebar() {
  const pathname = usePathname();

  const isActive = (href: string) =>
    pathname === href || pathname.startsWith(`${href}/`);

  return (
    <aside className="hidden w-64 shrink-0 border-r bg-card md:flex md:flex-col">
      <div className="flex h-14 items-center gap-2 border-b px-4">
        <Train className="h-6 w-6 text-primary" />
        <div className="leading-tight">
          <p className="text-sm font-semibold">Railway Access &amp; Block Mgmt</p>
          <p className="text-xs text-muted-foreground">Division: DLI</p>
        </div>
      </div>

      <nav className="flex-1 space-y-4 overflow-y-auto p-3">
        {NAV.map((group) => {
          const GroupIcon = group.icon;
          const anyActive = group.items.some((i) => isActive(i.href));
          return (
            <div key={group.area}>
              <div className="mb-1 flex items-center gap-2 px-2 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                <GroupIcon className="h-3.5 w-3.5" />
                {group.area}
              </div>
              <div className="space-y-0.5">
                {group.items.map((item) => {
                  const active = isActive(item.href);
                  const Icon = item.icon;
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      className={cn(
                        "flex items-center gap-2.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
                        active
                          ? "bg-primary text-primary-foreground"
                          : anyActive
                            ? "text-foreground hover:bg-accent hover:text-accent-foreground"
                            : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
                      )}
                    >
                      <Icon className="h-4 w-4" />
                      {item.label}
                    </Link>
                  );
                })}
              </div>
            </div>
          );
        })}
      </nav>
    </aside>
  );
}
