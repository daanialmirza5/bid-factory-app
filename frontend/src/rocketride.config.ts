// Public (non-secret) URL of the FastAPI backend used by the RocketRide-hosted app.
// RocketRide builds apps server-side with its own build config and no build-time
// environment injection, so the value lives in source. PUBLIC_API_BASE_URL, when
// a build does provide it, takes precedence.
const env = import.meta.env as Record<string, string | undefined>;

export const PUBLIC_API_BASE_URL = env.PUBLIC_API_BASE_URL || 'https://bid-factory-app-production.up.railway.app';
