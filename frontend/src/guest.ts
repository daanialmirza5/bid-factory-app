// Guest access lets a visitor try the public demo without creating an account.
const KEY = 'bidfactory_guest';

export function isGuest(): boolean {
  try {
    return localStorage.getItem(KEY) === '1';
  } catch {
    return false;
  }
}

export function enterGuest(): void {
  try {
    localStorage.setItem(KEY, '1');
  } catch {
    // Storage can be blocked in private windows; the visitor can still sign up instead.
  }
}

export function leaveGuest(): void {
  try {
    localStorage.removeItem(KEY);
  } catch {
    // Nothing to clear when storage is unavailable.
  }
}
