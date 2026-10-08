# BidFactory web app

React 18 + TypeScript front end for BidFactory. See the [project README](../README.md) for the full picture.

- `npm run dev`: local dev server on port 3000; `/api` is proxied to the FastAPI backend on port 8000.
- `npm run build`: type-check and production build.
- `npm run lint`: ESLint.

The same source is deployed as the RocketRide app `team_hackher.bid-factory` (entry point `src/AppDescriptor.ts`), which calls the backend at the URL in `src/rocketride.config.ts`.
