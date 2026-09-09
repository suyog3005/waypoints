const BASE_URL =
  process.env.NEXT_PUBLIC_API_GATEWAY_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public body?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/**
 * Typed fetch wrapper pointed at the API Gateway.
 * The gateway generates the X-Correlation-Id; we read it back from the
 * response header so the dev CorrelationIdBadge can display it.
 */
export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<{ data: T; correlationId: string | null }> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  const correlationId =
    res.headers.get("X-Correlation-Id") ??
    res.headers.get("x-correlation-id") ??
    null;

  if (!res.ok) {
    let body: unknown;
    try {
      body = await res.json();
    } catch {
      body = await res.text().catch(() => null);
    }
    const message =
      (body as { detail?: string })?.detail ?? `Request failed: ${res.status}`;
    throw new ApiError(res.status, message, body);
  }

  const data = (await res.json()) as T;

  // Surface the correlation ID to the dev CorrelationIdBadge (client-only).
  if (typeof window !== "undefined" && correlationId) {
    window.dispatchEvent(
      new CustomEvent("api:correlation-id", { detail: { correlationId } }),
    );
  }

  return { data, correlationId };
}
