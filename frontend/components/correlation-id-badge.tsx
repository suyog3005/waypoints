"use client";

import { useEffect, useState } from "react";
import { Hash } from "lucide-react";
import { Badge } from "@/components/ui/badge";

/**
 * Dev-only chip showing the X-Correlation-Id of the last API response.
 * Huge help when debugging the write -> Kafka -> optimizer -> read loop.
 * Only renders in development.
 */
export function CorrelationIdBadge() {
  const [id, setId] = useState<string | null>(null);

  useEffect(() => {
    if (process.env.NODE_ENV !== "development") return;
    const handler = (e: Event) => {
      const detail = (e as CustomEvent<{ correlationId: string | null }>)
        .detail;
      if (detail?.correlationId) setId(detail.correlationId);
    };
    window.addEventListener("api:correlation-id", handler);
    return () => window.removeEventListener("api:correlation-id", handler);
  }, []);

  if (!id) return null;

  return (
    <Badge
      variant="outline"
      className="hidden font-mono text-[10px] lg:inline-flex"
      title="Last X-Correlation-Id"
    >
      <Hash className="mr-1 h-3 w-3" />
      {id.slice(0, 8)}
    </Badge>
  );
}
