// Keyboard shortcuts. The single keys never fire while typing in a field, while
// a dialog is open, or with Ctrl, Alt or the Windows key held; Space also leaves
// a focused button, tab or checkbox to do what Space does to it. Ctrl+K works
// in a field too, though not over another dialog. Each shortcut sends an event that the part of the page it's for
// listens for (as the top bar's running task opens the Queue tab).
import { useEffect, useLayoutEffect, useRef } from "preact/hooks";
import { html } from "./html.js";

export const TAB_KEYS = ["values", "queue", "instruments", "logs"]; // 1 to 4

export const SHORTCUTS = [
  ["Space", "Hold the plots where they are, or follow the data again"],
  ["1 – 4", "Open the Values, Queue, Instruments or Logs tab"],
  ["`", "Hide or show the dock"],
  ["T", "Switch between the light and dark themes"],
  ["Ctrl + K", "Search tasks, instruments and actions, to queue, call or run one"],
  ["?", "Show these shortcuts"],
];

const send = (name, detail) => window.dispatchEvent(new CustomEvent(name, { detail }));

// Whether keys go into what has the focus: a field, a list of choices, or
// anything editable.
export function typing(target) {
  if (!(target instanceof Element)) return false;
  if (target.isContentEditable) return true;
  if (target.tagName === "TEXTAREA" || target.tagName === "SELECT") return true;
  if (target.tagName !== "INPUT") return false;
  return !["checkbox", "radio", "button", "submit", "reset", "range", "color"].includes(target.type);
}

// Whether Space does something to what has the focus (presses it, ticks it).
function spaceActs(target) {
  if (!(target instanceof Element)) return false;
  return (
    ["BUTTON", "A", "SUMMARY"].includes(target.tagName) ||
    target.tagName === "INPUT" ||
    ["button", "tab", "menuitem", "checkbox", "switch", "option", "link"].includes(
      target.getAttribute("role"),
    )
  );
}

export function useShortcuts({ onToggleTheme, onPalette, onHelp }) {
  // The latest handlers, for the one listener.
  const handlers = useRef({});
  handlers.current = { onToggleTheme, onPalette, onHelp };
  useEffect(() => {
    const onKey = (event) => {
      const { key } = event;
      if ((event.ctrlKey || event.metaKey) && !event.altKey && key.toLowerCase() === "k") {
        event.preventDefault();
        // Not over another dialog (it opens the palette, or closes it).
        if (!document.querySelector("[aria-modal='true']:not(.palette)")) handlers.current.onPalette();
        return;
      }
      if (event.defaultPrevented || event.ctrlKey || event.altKey || event.metaKey) return;
      if (typing(event.target)) return;
      if (document.querySelector("[aria-modal='true'], .overlay")) return;
      if (key === " ") {
        if (spaceActs(event.target)) return;
        event.preventDefault();
        send("pyacquisition:toggle-hold");
      } else if (key >= "1" && key <= "4") {
        send("pyacquisition:open-tab", TAB_KEYS[Number(key) - 1]);
      } else if (key === "`") {
        send("pyacquisition:toggle-dock");
      } else if (key === "t" || key === "T") {
        handlers.current.onToggleTheme();
      } else if (key === "?") {
        handlers.current.onHelp();
      } else {
        return;
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
}

// The list of shortcuts, from ? (or the top bar's keyboard button).
export function ShortcutHelp({ onClose }) {
  const close = useRef(null);
  useLayoutEffect(() => {
    close.current?.focus();
    const onKey = (event) => {
      if (event.key === "Escape" || event.key === "?") {
        event.preventDefault();
        onClose();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
  return html`
    <div class="overlay" onPointerDown=${(e) => e.target === e.currentTarget && onClose()}>
      <div class="dialog shortcut-help" role="dialog" aria-modal="true" aria-labelledby="shortcuts-title">
        <h2 id="shortcuts-title">Keyboard shortcuts</h2>
        <dl class="shortcut-list">
          ${SHORTCUTS.map(
            ([keys, does]) => html`
              <div class="shortcut" key=${keys}>
                <dt>${keys.split(" ").map((part) =>
                  ["–", "+"].includes(part) ? html`<span class="shortcut-join">${part}</span>` : html`<kbd>${part}</kbd>`,
                )}</dt>
                <dd>${does}</dd>
              </div>
            `,
          )}
        </dl>
        <p class="form-help">They don't work while typing in a field.</p>
        <div class="dialog-buttons">
          <button class="button" ref=${close} onClick=${onClose}>Close</button>
        </div>
      </div>
    </div>
  `;
}
