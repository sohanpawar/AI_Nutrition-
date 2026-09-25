/**
 * Server-only backend base URL for Next.js API proxies.
 * Prefer BACKEND_API_URL / API_URL so the Railway host stays off the client bundle.
 */
export function getBackendBaseUrl(): string {
  const raw =
    process.env.BACKEND_API_URL?.trim() ||
    process.env.API_URL?.trim() ||
    process.env.NEXT_PUBLIC_API_URL?.trim() ||
    "";
  return raw.replace(/\/$/, "");
}
