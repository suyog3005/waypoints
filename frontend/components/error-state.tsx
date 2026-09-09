import { AlertTriangle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";

export function ErrorState({
  title = "Something went wrong",
  message,
  onRetry,
}: {
  title?: string;
  message?: string;
  onRetry?: () => void;
}) {
  return (
    <div className="flex flex-col items-center justify-center rounded-lg border border-destructive/30 bg-destructive/5 p-10 text-center">
      <AlertTriangle className="mb-3 h-10 w-10 text-destructive" />
      <p className="text-sm font-medium">{title}</p>
      {message && (
        <p className="mt-1 max-w-sm text-sm text-muted-foreground">{message}</p>
      )}
      {onRetry && (
        <Button size="sm" variant="outline" className="mt-4" onClick={onRetry}>
          <RefreshCw className="mr-1 h-4 w-4" />
          Retry
        </Button>
      )}
    </div>
  );
}
