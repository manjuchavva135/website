type FetchParams = Record<string, string | number | boolean | null | undefined>;

const LOCAL_API_ORIGIN = "http://localhost:8000";
const LOCAL_HOSTS = new Set(["localhost", "127.0.0.1", "::1"]);

function explicitApiBaseUrl(): string | undefined {
  const value = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();
  return value ? value.replace(/\/$/, "") : undefined;
}

function isBrowserLocalhost(): boolean {
  return typeof window !== "undefined" && LOCAL_HOSTS.has(window.location.hostname);
}

function usesSameOriginApiService(): boolean {
  if (explicitApiBaseUrl()) return false;
  // The Next.js server rewrites /api/v1/:path* to the FastAPI backend in dev
  // and production alike, so the client should always call same-origin when no
  // explicit base URL is set. This makes the site work identically over
  // localhost, ngrok, and Vercel without per-environment CORS surprises.
  if (typeof window !== "undefined") return true;
  return Boolean(process.env.VERCEL_URL);
}

function runtimeOrigin(): string {
  if (typeof window !== "undefined") return window.location.origin;
  if (process.env.VERCEL_URL) return `https://${process.env.VERCEL_URL}`;
  return "http://localhost:3000";
}

export function apiBaseUrl(): string {
  const explicit = explicitApiBaseUrl();
  if (explicit) return explicit;
  if (usesSameOriginApiService()) return runtimeOrigin();
  return LOCAL_API_ORIGIN;
}

export function buildApiUrl(path: string, params: FetchParams = {}): string {
  const base = apiBaseUrl();
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  const relativePath = normalizedPath.startsWith(`${base}/`)
    ? normalizedPath
    : `${base}${normalizedPath}`;
  const url = /^https?:\/\//.test(base)
    ? new URL(normalizedPath, base)
    : new URL(relativePath, runtimeOrigin());

  for (const [key, value] of Object.entries(params)) {
    if (value !== null && value !== undefined && value !== "") {
      url.searchParams.set(key, String(value));
    }
  }

  return url.toString();
}

export function buildApiServiceUrl(path: string, params: FetchParams = {}): string {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  const servicePath = usesSameOriginApiService() ? `/api${normalizedPath}` : normalizedPath;
  return buildApiUrl(servicePath, params);
}
