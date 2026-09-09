"use client";

import { useSearchParams, useRouter, usePathname } from "next/navigation";
import { RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export interface FilterOption {
  value: string;
  label: string;
}

/**
 * URL-search-param-backed filter controls. Filters live in the query string so
 * they are shareable/bookmarkable and map 1:1 to Query Service query params.
 * Phase 9A: a generic status select + free-text search + reset.
 */
export function FilterBar({
  statusKey = "status",
  statusOptions,
  searchKey = "q",
  searchPlaceholder = "Search…",
}: {
  statusKey?: string;
  statusOptions?: FilterOption[];
  searchKey?: string;
  searchPlaceholder?: string;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const status = searchParams.get(statusKey) ?? "";
  const q = searchParams.get(searchKey) ?? "";

  function update(key: string, value: string) {
    const params = new URLSearchParams(searchParams.toString());
    if (value) params.set(key, value);
    else params.delete(key);
    router.replace(`${pathname}?${params.toString()}`, { scroll: false });
  }

  function reset() {
    router.replace(pathname, { scroll: false });
  }

  const hasFilters = status || q;

  return (
    <div className="flex flex-wrap items-center gap-2">
      {statusOptions && statusOptions.length > 0 && (
        <select
          value={status}
          onChange={(e) => update(statusKey, e.target.value)}
          className="h-9 rounded-md border border-input bg-background px-3 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
        >
          <option value="">All statuses</option>
          {statusOptions.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      )}
      <Input
        value={q}
        onChange={(e) => update(searchKey, e.target.value)}
        placeholder={searchPlaceholder}
        className="w-56"
      />
      {hasFilters && (
        <Button variant="ghost" size="sm" onClick={reset}>
          <RefreshCw className="mr-1 h-4 w-4" />
          Reset
        </Button>
      )}
    </div>
  );
}
