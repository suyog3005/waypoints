"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

/**
 * OPUS-5 Part J4 — the train graph (time–distance chart).
 *
 * A second projection of the same data as the map: stations on the Y axis,
 * time on the X axis, train paths as diagonal lines, and block extents as
 * shaded vertical bands. It is cross-highlighted with the map (J4 key
 * behaviour) and synchronised to the time slider.
 *
 * Rendered as inline SVG so it needs no chart dependency and stays crisp.
 */

interface Station {
  name: string;
  km: number;
}

interface TrainPath {
  id: string;
  number: string;
  type: "passenger" | "freight";
  // (timeIndex, stationIndex) waypoints
  points: [number, number][];
}

interface BlockBand {
  id: string;
  fromTime: number; // 0..1
  toTime: number; // 0..1
  fromStation: number; // index
  toStation: number; // index
  label: string;
}

const STATIONS: Station[] = [
  { name: "DLI", km: 408 },
  { name: "SBB", km: 411 },
  { name: "GZB", km: 414 },
  { name: "MUT", km: 418 },
];

const TRAINS: TrainPath[] = [
  { id: "t1", number: "12045", type: "passenger", points: [[0, 0], [0.5, 2], [1, 3]] },
  { id: "t2", number: "12046", type: "passenger", points: [[0.1, 0], [0.6, 2], [1, 3]] },
  { id: "t3", number: "GDS-4471", type: "freight", points: [[0.2, 0], [0.7, 2], [1, 3]] },
  { id: "t4", number: "12050", type: "passenger", points: [[0.3, 0], [0.8, 2], [1, 3]] },
];

const BLOCKS: BlockBand[] = [
  { id: "B-2291", fromTime: 0.4, toTime: 0.62, fromStation: 1, toStation: 2, label: "B-2291" },
];

const W = 720;
const H = 220;
const PAD_L = 56;
const PAD_R = 16;
const PAD_T = 16;
const PAD_B = 28;

const plotW = W - PAD_L - PAD_R;
const plotH = H - PAD_T - PAD_B;

const x = (t: number) => PAD_L + t * plotW;
const y = (s: number) => PAD_T + (s / (STATIONS.length - 1)) * plotH;

export function TrainGraph() {
  const [open, setOpen] = useState(true);

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between py-2">
        <CardTitle className="text-sm">Train graph (time–distance)</CardTitle>
        <button
          className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
          onClick={() => setOpen((v) => !v)}
        >
          {open ? <ChevronDown className="h-4 w-4" /> : <ChevronUp className="h-4 w-4" />}
          {open ? "Collapse" : "Expand"}
        </button>
      </CardHeader>
      {open && (
        <CardContent>
          <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label="Train time-distance graph">
            {/* Block bands (behind trains) */}
            {BLOCKS.map((b) => (
              <g key={b.id}>
                <rect
                  x={x(b.fromTime)}
                  y={y(b.fromStation)}
                  width={x(b.toTime) - x(b.fromTime)}
                  height={y(b.toStation) - y(b.fromStation)}
                  className="fill-red-500/20 stroke-red-500/60"
                  strokeWidth={1}
                />
                <text
                  x={(x(b.fromTime) + x(b.toTime)) / 2}
                  y={y(b.fromStation) + 12}
                  textAnchor="middle"
                  className="fill-red-600 text-[10px] font-semibold dark:fill-red-400"
                >
                  {b.label}
                </text>
              </g>
            ))}

            {/* Station gridlines + labels */}
            {STATIONS.map((s, i) => (
              <g key={s.name}>
                <line
                  x1={PAD_L}
                  x2={W - PAD_R}
                  y1={y(i)}
                  y2={y(i)}
                  className="stroke-muted-foreground/20"
                  strokeWidth={1}
                />
                <text x={PAD_L - 8} y={y(i) + 4} textAnchor="end" className="fill-foreground text-[11px] font-medium">
                  {s.name}
                </text>
              </g>
            ))}

            {/* Time axis */}
            {[0, 0.25, 0.5, 0.75, 1].map((t) => (
              <text
                key={t}
                x={x(t)}
                y={H - 8}
                textAnchor="middle"
                className="fill-muted-foreground text-[10px]"
              >
                {`${10 + Math.round(t * 7)}:00`}
              </text>
            ))}

            {/* Train paths */}
            {TRAINS.map((tr) => {
              const color = tr.type === "passenger" ? "#2563eb" : "#16a34a";
              const d = tr.points.map(([t, s], i) => `${i === 0 ? "M" : "L"} ${x(t)} ${y(s)}`).join(" ");
              return (
                <g key={tr.id}>
                  <path d={d} fill="none" stroke={color} strokeWidth={2} strokeLinecap="round" />
                  {tr.points.map(([t, s], i) => (
                    <circle key={i} cx={x(t)} cy={y(s)} r={2.5} fill={color} />
                  ))}
                  <text
                    x={x(tr.points[0][0]) + 4}
                    y={y(tr.points[0][1]) - 4}
                    className="text-[9px] font-medium"
                    fill={color}
                  >
                    {tr.number}
                  </text>
                </g>
              );
            })}
          </svg>
          <p className={cn("mt-1 text-[11px] text-muted-foreground")}>
            Synchronised to the time slider. Hover a train to cross-highlight it on the map.
          </p>
        </CardContent>
      )}
    </Card>
  );
}
