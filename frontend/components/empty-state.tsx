import { Inbox } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function EmptyState({
  title = "Nothing here yet",
  description,
  action,
  className,
}: {
  title?: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center rounded-lg border border-dashed p-10 text-center",
        className,
      )}
    >
      <Inbox className="mb-3 h-10 w-10 text-muted-foreground" />
      <p className="text-sm font-medium">{title}</p>
      {description && (
        <p className="mt-1 max-w-sm text-sm text-muted-foreground">
          {description}
        </p>
      )}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function EmptyStateWithCta({
  title,
  description,
  ctaLabel,
  onCta,
}: {
  title?: string;
  description?: string;
  ctaLabel: string;
  onCta: () => void;
}) {
  return (
    <EmptyState
      title={title}
      description={description}
      action={
        <Button size="sm" onClick={onCta}>
          {ctaLabel}
        </Button>
      }
    />
  );
}
