/**
 * AppDescriptor — the one module this app exposes to the RocketRide shell
 * (from the RocketRide app scaffold). The shell lazy-loads it on activation
 * and renders `app`. The standalone Vite entry is main.tsx.
 */

// HMR anchor: keeps the shared jsx runtime referenced even when the app's
// root component fails to compile (see ROCKETRIDE_APPS.md, scaffolded files).
import 'react/jsx-dev-runtime';

import './index.css';
import App from './App';
import { setApiBaseUrl } from './config';
import { PUBLIC_API_BASE_URL } from './rocketride.config';

// Inside RocketRide, same-origin /api is RocketRide's own API, so the backend
// must always be addressed absolutely.
setApiBaseUrl(PUBLIC_API_BASE_URL);

const descriptor = {
	id: 'team_hackher.bid-factory',
	name: 'Bid Factory',
	branding: { appName: 'Bid Factory' },
	app: App,
};

export default descriptor;
