'use client';

/**
 * OPUS-5 map shell — SIDEBAR overlay panels (full-content, cover the map).
 *
 * Each left-rail area opens one of these full-width panels over the map:
 *   situation, plan, blocks, execution, resources, network, analytics, settings.
 *
 * These reuse the Part J demo data + the Part K map data so the numbers on
 * the map and in the panels always agree.
 */

import { useOverlayStore } from '@/stores/overlay.store';
import { BLOCKS, STATIONS, LINES, ASSETS, TRACTION } from '@/lib/map-data';
import { getSemantic } from '@/lib/palette';
import {
  getPlanningRun,
  getExecutiveDashboard,
  getNowPanel,
} from '@/lib/demo-data';
import { X, ArrowRight } from 'lucide-react';

function FullShell({ title, subtitle, children }: { title: string; subtitle?: string; children: React.ReactNode }) {
  const close = useOverlayStore((s) => s.close);
  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b border-slate-200 px-5 py-3 dark:border-slate-800">
        <div>
          <h2 className="text-base font-semibold text-slate-800 dark:text-slate-100">{title}</h2>
          {subtitle && <p className="text-xs text-slate-400">{subtitle}</p>}
        </div>
        <button type="button" onClick={close} className="rounded p-1.5 text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800">
          <X className="h-5 w-5" />
        </button>
      </div>
      <div className="flex-1 overflow-y-auto p-5">{children}</div>
    </div>
  );
}

function StateChip({ state }: { state: string }) {
  const sem = getSemantic(state);
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${sem.chip}`}>
      <span className="h-2 w-2 rounded-full" style={{ background: sem.color }} />
      {sem.label}
    </span>
  );
}

// ── Situation ──────────────────────────────────────────────────────────
export function SituationPanel() {
  const now = getNowPanel();
  return (
    <FullShell title="Situation" subtitle="DLI corridor · live">
      <div className="grid gap-4 md:grid-cols-3">
        <div className="rounded-xl border border-slate-200 p-4 dark:border-slate-800">
          <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-400">Extensions pending</h3>
          <div className="space-y-2">
            {now.extensionsPending.map((e) => (
              <div key={e.id} className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2 dark:bg-slate-800/50">
                <span className="text-sm font-medium text-slate-700 dark:text-slate-200">{e.id}</span>
                <span className="text-xs text-slate-500">+{e.minutes}m · impact {e.impactMin}m</span>
              </div>
            ))}
          </div>
        </div>
        <div className="rounded-xl border border-slate-200 p-4 dark:border-slate-800">
          <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-400">Active blocks</h3>
          <div className="space-y-2">
            {now.activeBlocks.map((b) => (
              <div key={b.id} className="rounded-lg bg-slate-50 px-3 py-2 dark:bg-slate-800/50">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-slate-700 dark:text-slate-200">{b.id}</span>
                  <span className="text-xs text-slate-400">{b.endsAt}</span>
                </div>
                <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700">
                  <div className="h-full rounded-full bg-red-500" style={{ width: `${b.progress}%` }} />
                </div>
              </div>
            ))}
          </div>
        </div>
        <div className="rounded-xl border border-slate-200 p-4 dark:border-slate-800">
          <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-400">Alerts</h3>
          <div className="space-y-2">
            {now.alerts.map((a) => (
              <div key={a.id} className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:border-amber-900/50 dark:bg-amber-950/30 dark:text-amber-300">
                {a.text}
              </div>
            ))}
          </div>
        </div>
      </div>
    </FullShell>
  );
}

// ── Plan ───────────────────────────────────────────────────────────────
export function PlanPanel() {
  const run = getPlanningRun();
  return (
    <FullShell title="Plan" subtitle={`${run.runId} · ${run.horizon}`}>
      <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-800">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-400 dark:bg-slate-800/50">
            <tr>
              <th className="px-4 py-2.5">Option</th>
              <th className="px-4 py-2.5 text-right">Scheduled</th>
              <th className="px-4 py-2.5 text-right">Detention</th>
              <th className="px-4 py-2.5 text-right">Cancels</th>
              <th className="px-4 py-2.5 text-right">Bundles</th>
              <th className="px-4 py-2.5 text-right">Score</th>
            </tr>
          </thead>
          <tbody>
            {run.options.map((o) => (
              <tr key={o.id} className={`border-t border-slate-100 dark:border-slate-800 ${o.recommended ? 'bg-blue-50/50 dark:bg-blue-950/20' : ''}`}>
                <td className="px-4 py-2.5 font-medium text-slate-700 dark:text-slate-200">
                  {o.name} {o.recommended && <span className="ml-1 text-xs text-blue-600">★ recommended</span>}
                </td>
                <td className="px-4 py-2.5 text-right tabular-nums text-slate-600 dark:text-slate-300">{o.demandsScheduled}/{o.totalDemands}</td>
                <td className="px-4 py-2.5 text-right tabular-nums text-slate-600 dark:text-slate-300">{o.detentionMin}m</td>
                <td className="px-4 py-2.5 text-right tabular-nums text-slate-600 dark:text-slate-300">{o.cancellations}</td>
                <td className="px-4 py-2.5 text-right tabular-nums text-slate-600 dark:text-slate-300">{o.bundlesFormed}</td>
                <td className="px-4 py-2.5 text-right tabular-nums font-semibold text-slate-700 dark:text-slate-200">{o.objectiveScore}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </FullShell>
  );
}

// ── Blocks ─────────────────────────────────────────────────────────────
export function BlocksPanel() {
  return (
    <FullShell title="Blocks" subtitle={`${BLOCKS.length} blocks on the DLI corridor`}>
      <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-800">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-400 dark:bg-slate-800/50">
            <tr>
              <th className="px-4 py-2.5">ID</th>
              <th className="px-4 py-2.5">Line</th>
              <th className="px-4 py-2.5">Chainage</th>
              <th className="px-4 py-2.5">State</th>
              <th className="px-4 py-2.5">Window</th>
              <th className="px-4 py-2.5">Note</th>
            </tr>
          </thead>
          <tbody>
            {BLOCKS.map((b) => (
              <tr key={b.id} className="border-t border-slate-100 dark:border-slate-800">
                <td className="px-4 py-2.5 font-medium text-slate-700 dark:text-slate-200">{b.id}</td>
                <td className="px-4 py-2.5 text-slate-500 dark:text-slate-400">{LINES.find((l) => l.id === b.lineId)?.name}</td>
                <td className="px-4 py-2.5 tabular-nums text-slate-500 dark:text-slate-400">{b.fromKm}–{b.toKm}</td>
                <td className="px-4 py-2.5"><StateChip state={b.state} /></td>
                <td className="px-4 py-2.5 tabular-nums text-slate-500 dark:text-slate-400">{b.window}</td>
                <td className="px-4 py-2.5 text-slate-500 dark:text-slate-400">{b.note}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </FullShell>
  );
}

// ── Execution ──────────────────────────────────────────────────────────
export function ExecutionPanel() {
  const active = BLOCKS.filter((b) => b.state === 'active' || b.state === 'emergency');
  return (
    <FullShell title="Execution" subtitle="Live block console">
      <div className="grid gap-4 md:grid-cols-2">
        {active.map((b) => (
          <div key={b.id} className="rounded-xl border border-slate-200 p-4 dark:border-slate-800">
            <div className="flex items-center justify-between">
              <span className="text-sm font-semibold text-slate-700 dark:text-slate-200">{b.id}</span>
              <StateChip state={b.state} />
            </div>
            <p className="mt-1 text-xs text-slate-400">{b.note} · {b.window}</p>
            <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700">
              <div className="h-full rounded-full bg-red-500" style={{ width: `${b.progress}%` }} />
            </div>
            <p className="mt-1 text-right text-xs tabular-nums text-slate-400">{b.progress}% complete</p>
          </div>
        ))}
      </div>
    </FullShell>
  );
}

// ── Resources ──────────────────────────────────────────────────────────
export function ResourcesPanel() {
  const machines = [
    { id: 'TM-07', name: 'Tamper TM-07', util: 61, status: 'idle' },
    { id: 'MOW-3', name: 'MOW 3', util: 84, status: 'on-block' },
    { id: 'OHE-12', name: 'OHE 12', util: 47, status: 'idle' },
    { id: 'BRC-2', name: 'Bridge 2', util: 72, status: 'on-block' },
  ];
  return (
    <FullShell title="Resources" subtitle="Machines, gangs & materials">
      <div className="grid gap-3 md:grid-cols-2">
        {machines.map((m) => (
          <div key={m.id} className="rounded-xl border border-slate-200 p-4 dark:border-slate-800">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-slate-700 dark:text-slate-200">{m.name}</span>
              <span className={`rounded-full px-2 py-0.5 text-xs ${m.status === 'on-block' ? 'bg-red-50 text-red-700 dark:bg-red-950/40 dark:text-red-300' : 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400'}`}>{m.status}</span>
            </div>
            <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700">
              <div className="h-full rounded-full bg-blue-500" style={{ width: `${m.util}%` }} />
            </div>
            <p className="mt-1 text-right text-xs tabular-nums text-slate-400">{m.util}% utilisation</p>
          </div>
        ))}
      </div>
    </FullShell>
  );
}

// ── Network ────────────────────────────────────────────────────────────
export function NetworkPanel() {
  return (
    <FullShell title="Network" subtitle="DLI corridor infrastructure">
      <div className="grid gap-4 md:grid-cols-2">
        <div className="rounded-xl border border-slate-200 p-4 dark:border-slate-800">
          <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-400">Stations</h3>
          <div className="space-y-1.5">
            {STATIONS.map((s) => (
              <div key={s.id} className="flex items-center justify-between text-sm">
                <span className="text-slate-700 dark:text-slate-200">{s.name}</span>
                <span className="tabular-nums text-slate-400">{s.km} km</span>
              </div>
            ))}
          </div>
        </div>
        <div className="rounded-xl border border-slate-200 p-4 dark:border-slate-800">
          <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-400">Traction sections</h3>
          <div className="space-y-1.5">
            {TRACTION.map((t) => (
              <div key={t.id} className="flex items-center justify-between text-sm">
                <span className="text-slate-700 dark:text-slate-200">{t.id}</span>
                <span className={`rounded-full px-2 py-0.5 text-xs ${t.state === 'energised' ? 'bg-green-50 text-green-700 dark:bg-green-950/40 dark:text-green-300' : t.state === 'isolated' ? 'bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300' : 'bg-red-50 text-red-700 dark:bg-red-950/40 dark:text-red-300'}`}>{t.state}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="rounded-xl border border-slate-200 p-4 dark:border-slate-800 md:col-span-2">
          <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-400">Assets ({ASSETS.length})</h3>
          <div className="flex flex-wrap gap-2">
            {ASSETS.filter((a) => a.condition !== 'good').map((a) => (
              <span key={a.id} className={`rounded-full px-2.5 py-1 text-xs ${a.condition === 'failed' ? 'bg-red-50 text-red-700 dark:bg-red-950/40 dark:text-red-300' : a.condition === 'defective' ? 'bg-orange-50 text-orange-700 dark:bg-orange-950/40 dark:text-orange-300' : 'bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300'}`}>
                {a.id} · {a.kind} · {a.condition}
              </span>
            ))}
          </div>
        </div>
      </div>
    </FullShell>
  );
}

// ── Analytics ──────────────────────────────────────────────────────────
export function AnalyticsPanel() {
  const dash = getExecutiveDashboard();
  return (
    <FullShell title="Analytics" subtitle={`${dash.period} · ${dash.division}`}>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {dash.kpis.map((k) => (
          <div key={k.label} className="rounded-xl border border-slate-200 p-4 dark:border-slate-800">
            <p className="text-xs text-slate-400">{k.label}</p>
            <p className="mt-1 text-2xl font-semibold tabular-nums text-slate-800 dark:text-slate-100">{k.value}</p>
            <p className={`mt-0.5 text-xs ${k.delta >= 0 === k.goodWhenUp ? 'text-green-600' : 'text-red-600'}`}>
              {k.delta >= 0 ? '+' : ''}{k.delta}
            </p>
          </div>
        ))}
      </div>
      <div className="mt-4 rounded-xl border border-slate-200 p-4 dark:border-slate-800">
        <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-400">Requires attention</h3>
        <ul className="space-y-2">
          {dash.attention.map((a, i) => (
            <li key={i} className="flex items-start gap-2 text-sm text-slate-600 dark:text-slate-300">
              <ArrowRight className="mt-0.5 h-4 w-4 shrink-0 text-amber-500" />
              {a}
            </li>
          ))}
        </ul>
      </div>
    </FullShell>
  );
}

// ── Settings ───────────────────────────────────────────────────────────
export function SettingsPanel() {
  return (
    <FullShell title="Settings" subtitle="Division & preferences">
      <div className="max-w-md space-y-4">
        <div className="rounded-xl border border-slate-200 p-4 dark:border-slate-800">
          <label className="text-xs font-semibold uppercase tracking-wide text-slate-400">Division</label>
          <select className="mt-2 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100">
            <option>DLI</option>
            <option>ALD</option>
            <option>PRYJ</option>
          </select>
        </div>
        <div className="rounded-xl border border-slate-200 p-4 dark:border-slate-800">
          <label className="text-xs font-semibold uppercase tracking-wide text-slate-400">Officer</label>
          <select className="mt-2 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100">
            <option>Sr.DOM</option>
            <option>DOM</option>
            <option>Asst. DOM</option>
          </select>
        </div>
      </div>
    </FullShell>
  );
}
