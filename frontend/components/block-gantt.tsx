'use client';

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { formatDateTime } from '@/lib/format';
import type { BlockOut } from '@/lib/hooks';

interface BlockGanttProps {
  blocks: BlockOut[];
  planId: string;
}

export function BlockGantt({ blocks, planId }: BlockGanttProps) {
  if (blocks.length === 0) {
    return <div className="text-sm text-muted-foreground p-4">No blocks to display.</div>;
  }

  // Transform blocks into chart data (duration in minutes)
  const data = blocks.map((block) => {
    const start = new Date(block.start_time);
    const end = new Date(block.end_time);
    const duration = (end.getTime() - start.getTime()) / 60000; // minutes

    return {
      track: block.track_code,
      duration,
      merged: block.is_merged ? 1 : 0,
      start: start.getTime(),
      end: end.getTime(),
      requests: block.request_count,
    };
  });

  return (
    <div className="w-full h-96">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ top: 5, right: 30, left: 120, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis type="number" label={{ value: 'Duration (minutes)', position: 'bottom' }} />
          <YAxis dataKey="track" type="category" width={100} />
          <Tooltip
            formatter={(value: any, name: string) => {
              if (name === 'duration') return `${Math.round(value as number)}m`;
              if (name === 'merged') return (value as number) > 0 ? 'Yes' : 'No';
              return value;
            }}
            labelFormatter={(label) => `Track: ${label}`}
          />
          <Legend />
          <Bar dataKey="duration" fill="#3b82f6" name="Block Duration (min)" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
