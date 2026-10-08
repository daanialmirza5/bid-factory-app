// Base URL of the FastAPI backend. Empty means same origin: the Vite dev proxy
// locally, or FastAPI serving the built SPA. Set it when the UI is hosted
// elsewhere (e.g. inside RocketRide, where same-origin /api is RocketRide's own API).
// VITE_ is read by Vite builds, PUBLIC_ by Rsbuild; the RocketRide entry
// (AppDescriptor.ts) sets it explicitly via setApiBaseUrl.
const env = import.meta.env as Record<string, string | undefined>;

const normalise = (url: string): string => url.replace(/\/+$/, '');

let apiBaseUrl = normalise(env.VITE_API_BASE_URL ?? env.PUBLIC_API_BASE_URL ?? '');

export const setApiBaseUrl = (url: string): void => {
    apiBaseUrl = normalise(url);
};

export const apiUrl = (path: string): string => `${apiBaseUrl}${path}`;
