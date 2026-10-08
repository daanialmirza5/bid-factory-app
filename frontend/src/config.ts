// Base URL of the FastAPI backend. Empty means same origin: the Vite dev proxy
// locally, or FastAPI serving the built SPA. Set it when the UI is hosted
// elsewhere (e.g. inside RocketRide, where same-origin /api is RocketRide's own API).
// VITE_ is read by Vite builds, PUBLIC_ by Rsbuild (the RocketRide app build).
const env = import.meta.env as Record<string, string | undefined>;

export const API_BASE_URL = (env.VITE_API_BASE_URL ?? env.PUBLIC_API_BASE_URL ?? '').replace(/\/+$/, '');

export const apiUrl = (path: string): string => `${API_BASE_URL}${path}`;
