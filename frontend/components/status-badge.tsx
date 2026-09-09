import { Badge, type BadgeProps } from "@/components/ui/badge";

/**
 * Maps a backend status string to a colored Badge.
 * One source of truth for the status color convention (frontend-plan.md §2).
 * Color is never the only signal — the label text is always shown.
 */

type StatusVariant = NonNullable<BadgeProps["variant"]>;

const STATUS_MAP: Record<string, { label: string; variant: StatusVariant }> = {
  // Request / Plan lifecycle
  draft: { label: "Draft", variant: "secondary" },
  submitted: { label: "Submitted", variant: "info" },
  scheduled: { label: "Scheduled", variant: "info" },
  merged: { label: "Merged", variant: "info" },
  proposed: { label: "Proposed", variant: "warning" },
  approved: { label: "Approved", variant: "info" },
  active: { label: "Active", variant: "success" },
  completed: { label: "Completed", variant: "secondary" },
  superseded: { label: "Superseded", variant: "destructive" },
  cancelled: { label: "Cancelled", variant: "destructive" },
  // Optimization run
  pending: { label: "Pending", variant: "secondary" },
  running: { label: "Running", variant: "info" },
  succeeded: { label: "Succeeded", variant: "success" },
  failed: { label: "Failed", variant: "destructive" },
};

export function StatusBadge({
  status,
  className,
}: {
  status: string;
  className?: string;
}) {
  const key = status?.toLowerCase() ?? "";
  const match = STATUS_MAP[key] ?? {
    label: status ?? "Unknown",
    variant: "secondary" as StatusVariant,
  };

  return (
    <Badge variant={match.variant} className={className}>
      {match.label}
    </Badge>
  );
}
