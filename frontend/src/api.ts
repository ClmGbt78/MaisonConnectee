/**
 * Client HTTP centralisé pour l'API Maison Connectée.
 *
 * Le jeton reste uniquement en mémoire : il n'est pas conservé dans
 * localStorage ni sessionStorage. Un rechargement nécessite donc une nouvelle
 * connexion.
 */
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/+$/, "");

let accessToken: string | null = null;

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

export function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  const headers = new Headers(init.headers);

  if (accessToken) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  } else {
    headers.delete("Authorization");
  }

  return fetch(`${API_BASE_URL}${normalizedPath}`, {
    ...init,
    headers,
  });
}
