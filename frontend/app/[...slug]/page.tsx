import Link from "next/link";
import { Button } from "@/components/ui/button";

/**
 * Catch-all for routes not yet implemented.
 * Static routes (e.g. /dashboard) take precedence over this catch-all in
 * Next.js, so as pages are built in Phase 9B/9C they automatically override
 * this page — no stub files to delete.
 */
export default function NotBuiltPage({
  params,
}: {
  params: { slug: string[] };
}) {
  const path = "/" + params.slug.join("/");

  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center text-center">
      <p className="text-sm font-medium text-muted-foreground">
        {path}
      </p>
      <h2 className="mt-2 text-xl font-semibold">Not built yet</h2>
      <p className="mt-2 max-w-sm text-sm text-muted-foreground">
        This page is part of the Phase 9 routing skeleton. It will be
        implemented in Phase 9B (core read + write features) or Phase 9C
        (visualization &amp; polish).
      </p>
      <Button asChild variant="outline" className="mt-6">
        <Link href="/dashboard">Back to Dashboard</Link>
      </Button>
    </div>
  );
}
