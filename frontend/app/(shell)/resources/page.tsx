"use client";

import { Wrench, Users, Package, HardHat } from "lucide-react";
import { PageHeader } from "@/components/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

/**
 * OPUS-5 Part J3 (RESOURCES) — Machines, gangs & competencies, materials,
 * contractors. A resource-awareness surface (A1.1 item 4).
 */

const MACHINES = [
  { id: "TM-07", type: "Tamper", status: "available", utilisation: 61, note: "14 idle days next month" },
  { id: "TM-03", type: "Tamper", status: "committed", utilisation: 88, note: "Programme P-11" },
  { id: "BRC-12", type: "Ballast regulator", status: "available", utilisation: 44, note: "" },
  { id: "TW-05", type: "Tower wagon", status: "maintenance", utilisation: 0, note: "due 18 Sep" },
];

const GANGS = [
  { id: "Gang-14", base: "SBB", competency: "Packing, OHE", rested: true },
  { id: "Gang-09", base: "GZB", competency: "S&T, axle counter", rested: true },
  { id: "Gang-21", base: "MUT", competency: "Electrification", rested: false },
];

const MATERIALS = [
  { item: "Sleepers (concrete)", qty: 420, atSite: true },
  { item: "OHE insulators", qty: 60, atSite: false },
  { item: "Axle counter units", qty: 4, atSite: true },
];

const STATUS_VARIANT: Record<string, "success" | "warning" | "secondary"> = {
  available: "success",
  committed: "warning",
  maintenance: "secondary",
};

export default function ResourcesPage() {
  return (
    <div className="space-y-4">
      <PageHeader
        title="Resources"
        description="Machines, gangs & competencies, materials and contractors."
      />

      <div className="grid gap-4 lg:grid-cols-2">
        {/* Machines */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm">
              <Wrench className="h-4 w-4" /> Machines
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {MACHINES.map((m) => (
              <div key={m.id} className="flex items-center justify-between rounded-md border p-2.5 text-sm">
                <div>
                  <p className="font-medium">
                    {m.id} <span className="text-muted-foreground">· {m.type}</span>
                  </p>
                  {m.note && <p className="text-xs text-muted-foreground">{m.note}</p>}
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-20">
                    <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
                      <div className="h-full rounded-full bg-primary" style={{ width: `${m.utilisation}%` }} />
                    </div>
                    <p className="mt-0.5 text-right text-[10px] text-muted-foreground">{m.utilisation}%</p>
                  </div>
                  <Badge variant={STATUS_VARIANT[m.status]}>{m.status}</Badge>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Gangs */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm">
              <Users className="h-4 w-4" /> Gangs & competencies
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {GANGS.map((g) => (
              <div key={g.id} className="flex items-center justify-between rounded-md border p-2.5 text-sm">
                <div>
                  <p className="font-medium">{g.id}</p>
                  <p className="text-xs text-muted-foreground">
                    {g.base} · {g.competency}
                  </p>
                </div>
                <Badge variant={g.rested ? "success" : "warning"}>
                  {g.rested ? "rested" : "not rested"}
                </Badge>
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Materials */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm">
              <Package className="h-4 w-4" /> Materials
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {MATERIALS.map((m) => (
              <div key={m.item} className="flex items-center justify-between rounded-md border p-2.5 text-sm">
                <span>{m.item}</span>
                <div className="flex items-center gap-3">
                  <span className="tabular-nums text-muted-foreground">{m.qty} units</span>
                  <Badge variant={m.atSite ? "success" : "warning"}>
                    {m.atSite ? "at site" : "in transit"}
                  </Badge>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Contractors */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm">
              <HardHat className="h-4 w-4" /> Contractors
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {[
              { name: "RailTech Services", scope: "OHE third-party", status: "active" },
              { name: "SignalWorks Ltd", scope: "Axle counter", status: "active" },
              { name: "BridgeCo", scope: "Girder renewal", status: "standby" },
            ].map((c) => (
              <div key={c.name} className="flex items-center justify-between rounded-md border p-2.5 text-sm">
                <div>
                  <p className="font-medium">{c.name}</p>
                  <p className="text-xs text-muted-foreground">{c.scope}</p>
                </div>
                <Badge variant={c.status === "active" ? "success" : "secondary"}>{c.status}</Badge>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
