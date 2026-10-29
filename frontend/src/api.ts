/**
 * Client HTTP centralisé pour l'API Maison Connectée.
 *
 * En développement, les chemins /api sont relayés par Vite vers FastAPI
 * (voir vite.config.ts). Une URL de base peut être fournie via
 * VITE_API_BASE_URL si le frontend et l'API sont hébergés séparément.
 */
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/+$/, "");

export function apiFetch(path: string, init?: RequestInit): Promise<Response> {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return fetch(`${API_BASE_URL}${normalizedPath}`, init);
}
