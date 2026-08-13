const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "/api/v1";

export class ApiError extends Error {
  constructor(
    public code: string,
    message: string,
    public correlationId?: string,
  ) {
    super(message);
  }
}

export function apiUrl(path: string) {
  if (path.startsWith("http")) return path;
  if (path.startsWith("/api/")) return path;
  return `${API_BASE}${path.startsWith("/") ? path : `/${path}`}`;
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(apiUrl(path), { cache: "no-store", ...init });
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as
      | { error?: { code?: string; message?: string; correlation_id?: string } }
      | null;
    throw new ApiError(
      payload?.error?.code ?? "REQUEST_FAILED",
      payload?.error?.message ?? "İstek tamamlanamadı.",
      payload?.error?.correlation_id,
    );
  }
  return response.json() as Promise<T>;
}

export const idempotencyKey = () => crypto.randomUUID();
