// The layout that comes back on the next run: the plots (panels, axes, series),
// the dock (its height, open tab, and whether it is collapsed) and the theme
// chosen. The experiment keeps it in a file (core/layout.py), since the app's
// window starts with nothing each run.
//
// Before the page first draws, whatever this session hasn't got is filled in from
// the server (this session's own, after a reload, is newer). Afterwards, each
// change to one of them is sent back, a moment after the last.
import { get } from "./api.js";
import { has, load, onSave, save } from "./session.js";

export const LAYOUT_KEYS = ["plots", "dock", "theme"];
const SEND_AFTER = 500; // milliseconds after the last change
const WAIT_AT_START = 1500; // at most, for the server's layout, before drawing anyway

// Set before the page loads (the browser tests do, as their rigs are shared),
// the saved layout is neither restored nor kept.
const off = () => globalThis.pyacquisitionLayoutOff === true;

export async function restoreLayout() {
  if (off()) return;
  try {
    const { data } = await get("/experiment/layout", { timeout: WAIT_AT_START });
    for (const key of LAYOUT_KEYS) {
      if (!has(key) && data && data[key] !== undefined) save(key, data[key]);
    }
  } catch {
    // Not there (an older experiment, or not answering yet): the defaults do.
  }
}

// The layout as this session has it now.
export function currentLayout() {
  const layout = {};
  for (const key of LAYOUT_KEYS) {
    if (has(key)) layout[key] = load(key, null);
  }
  return layout;
}

async function send() {
  try {
    await fetch("/experiment/layout", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(currentLayout()),
      signal: AbortSignal.timeout(5000),
      keepalive: true, // so a change made as the window closes still goes
    });
  } catch {
    // Kept for the session anyway, and sent with the next change.
  }
}

// Sends the layout back whenever part of it changes, a moment after the last
// change. Call once, after `restoreLayout`.
export function keepLayout() {
  if (off()) return () => {};
  let timer = null;
  return onSave((key) => {
    if (!LAYOUT_KEYS.includes(key)) return;
    clearTimeout(timer);
    timer = setTimeout(send, SEND_AFTER);
  });
}
