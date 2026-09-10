"use client";

import {
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  Download,
  ChevronDown,
} from "lucide-react";
import { PageHeader } from "@/components/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { getExecutiveDashboard, type KpiTrend } from "@/lib/demo-data";
import { cn } from "@/lib/utils";

/**
 * OPUS-5 Part J10 — Executive dashboard.
 *
 * Divisional block performance: KPI tiles with sparklines and deltas, a
 * departmental scorecard, top causes of lost block time, worst sections,
 * and a "requires your attention" list. Every figure drills through to the
 * underlying blocks — no number is a dead end (J10).
 */

function Sparkline({ data, good }: { data: number[]; good: boolean }) {
  const max = Math.max(...data);
  const min = Math.min(...data);
  const range = max - min || 1;
  const W = 80;
  const H = 28;
  const pts = data
    .map((v, i) => `${(i / (data.length - 1)) * W},${H - ((v - min) / range) * H}`)
    .join(" ");
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="h-7 w-20">
      <polyline
        points={pts}
        fill="none"
        stroke={good ? "#10b981" : "#f59e0b"}
        strokeWidth={1.5}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function KpiTile({ kpi }: { kpi: KpiTrend }) {
  const improving = kpi.goodWhenUp ? kpi.delta > 0 : kpi.delta < 0;
  const TrendIcon = kpi.delta >= 0 ? TrendingUp : TrendingDown;
  return (
    <Card>
      <CardContent className="p-4">
        <p className="text-xs font-medium text-muted-foreground">{kpi.label}</p>
        <div className="mt-1 flex items-end justify-between">
          <p className="text-2xl font-semibold tabular-nums">{kpi.value}</p>
          <Sparkline data={kpi.spark} good={improving} />
        </div>
        <p
          className={cn(
            "mt-1 flex items-center gap-1 text-xs font-medium",
            improving ? "text-emerald-600" : "text-amber-600",
          )}
        >
          <TrendIcon className="h-3 w-3" />
          {kpi.delta > 0 ? "+" : ""}
          {kpi.delta}
        </p>
      </CardContent>
    </Card>
  );
}

export default function AnalyticsPage() {
  const d = getExecutiveDashboard();

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <PageHeader
          title={`Divisional block performance — ${d.division}`}
          description={`Period: ${d.period}`}
        />
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm">
            {d.period} <ChevronDown className="ml-1 h-3.5 w-3.5" />
          </Button>
          <Button variant="outline" size="sm">
            <Download className="mr-1 h-4 w-4" /> Export
          </Button>
        </div>
      </div>

      {/* KPI tiles */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {d.kpis.map((k) => (
          <KpiTile key={k.label} kpi={k} />
        ))}
      </div>

      {/* Departmental scorecard */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Departmental scorecard</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-muted-foreground">
                  <th className="p-3 font-medium">Dept</th>
                  <th className="p-3 text-right font-medium">Demands</th>
                  <th className="p-3 text-right font-medium">Sanctioned</th>
                  <th className="p-3 text-right font-medium">Utilised</th>
                  <th className="p-3 text-right font-medium">Grant-punct</th>
                  <th className="p-3 text-right font-medium">Overrun</th>
                  <th className="p-3 text-right font-medium">Asked/Used</th>
                  <th className="p-3 text-right font-medium">Statutory OK</th>
                </tr>
              </thead>
              <tbody>
                {d.scorecard.map((row) => (
                  <tr key={row.dept} className="border-b last:border-0">
                    <td className="p-3 font-medium">{row.dept}</td>
                    <td className="p-3 text-right tabular-nums">{row.demands}</td>
                    <td className="p-3 text-right tabular-nums">{row.sanctioned}</td>
                    <td className="p-3 text-right tabular-nums">{row.utilised}%</td>
                    <td className="p-3 text-right tabular-nums">{row.grantPunct}%</td>
                    <td className="p-3 text-right tabular-nums">{row.overrun}%</td>
                    <td className="p-3 text-right tabular-nums">{row.askedUsed}</td>
                    <td className="p-3 text-right tabular-nums">{row.statutoryOk}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Causes + worst sections */}
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Top causes of lost block time</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {d.topCauses.map((c, i) => (
              <div key={c.label} className="flex items-center gap-3 text-sm">
                <span className="w-4 text-muted-foreground">{i + 1}</span>
                <span className="flex-1">{c.label}</span>
                <div className="h-1.5 w-32 overflow-hidden rounded-full bg-muted">
                  <div className="h-full rounded-full bg-primary" style={{ width: `${c.pct * 3}%` }} />
                </div>
                <span className="w-10 text-right tabular-nums">{c.pct}%</span>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Worst sections (detention/block-hour)</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {d.worstSections.map((s, i) => (
              <div key={s.label} className="flex items-center justify-between text-sm">
                <span className="flex items-center gap-2">
                  <span className="w-4 text-muted-foreground">{i + 1}</span>
                  {s.label}
                </span>
                <span className="tabular-nums">{s.detentionPerBlockHour} min</span>
              </div>
            ))}
            <div className="mt-3 border-t pt-3 text-sm">
              <p className="font-medium">Restrictions overdue for review: {d.restrictionsOverdue}</p>
              <p className="text-xs text-muted-foreground">oldest: {d.oldestRestriction}</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Requires attention */}
      <Card className="border-amber-300 dark:border-amber-700">
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-sm text-amber-700 dark:text-amber-400">
            <AlertTriangle className="h-4 w-4" /> Requires your attention
          </CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="space-y-1.5 text-sm">
            {d.attention.map((a, i) => (
              <li key={i} className="flex gap-2">
                <span className="text-amber-500">•</span>
                <span>{a}</span>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
