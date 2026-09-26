// Small bits of interface state (the dock's height, the open tab, the theme) that
// last for the session, so a reload keeps them. Storage can be unavailable, so a
// failure is ignored and the default is used. Layouts that last between runs are
// kept on the server instead (milestone 15).

const PREFIX = "pyacquisition:";

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
}
