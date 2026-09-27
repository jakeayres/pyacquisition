// Small bits of interface state (the dock's height, the open tab, the theme) that
// last for the session, so a reload keeps them. Storage can be unavailable, so a
// failure is ignored and the default is used. The layout that lasts between runs
// is kept on the server too (layout.js), which listens here for changes to it.

const PREFIX = "pyacquisition:";
const listeners = new Set();

// Calls `listener(key, value)` after each save. Returns a function to stop.
export function onSave(listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function load(key, fallback) {
  try {
    const raw = sessionStorage.getItem(PREFIX + key);
    return raw === null ? fallback : JSON.parse(raw);
  } catch {
    return fallback;
  }
}

export function save(key, value) {
  try {
    sessionStorage.setItem(PREFIX + key, JSON.stringify(value));
  } catch {
    // Not kept, which only costs a default next time.
  }
  for (const listener of listeners) listener(key, value);
}

// Whether anything is kept for this key this session.
export function has(key) {
  try {
    return sessionStorage.getItem(PREFIX + key) !== null;
  } catch {
    return false;
  }
}
