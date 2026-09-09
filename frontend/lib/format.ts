/**
 * Date/time/duration formatting helpers.
 * Railway operations are timezone-sensitive; we centralize formatting here.
 * Uses plain Intl APIs to avoid a date-fns dependency in Phase 9A.
 * (date-fns will be added in Phase 9B when real date math is needed.)
 */

const IST = "Asia/Kolkata";

export function formatDateTime(iso: string): string {
  try {
    return new Intl.DateTimeFormat("en-IN", {
      timeZone: IST,
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

export function formatTime(iso: string): string {
  try {
    return new Intl.DateTimeFormat("en-IN", {
      timeZone: IST,
      timeStyle: "short",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

export function formatDuration(minutes: number): string {
  if (minutes < 60) return `${minutes}m`;
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return m === 0 ? `${h}h` : `${h}h ${m}m`;
}

export function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const secs = Math.floor(diff / 1000);
  if (secs < 60) return "just now";
  const mins = Math.floor(secs / 60);
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}
