// A question to confirm before doing something that can't be undone, such as
// aborting a task: a dialog over the page, answered with its buttons, or Escape
// to cancel.
import { useLayoutEffect, useRef } from "preact/hooks";
import { html } from "./html.js";

export function ConfirmDialog({ title, children, confirmLabel, danger = false, onConfirm, onCancel }) {
  const cancel = useRef(null);
  // A layout effect, so an Escape pressed as soon as it opens is heard.
  useLayoutEffect(() => {
    cancel.current?.focus(); // the safe answer is the one Enter gives
    const onKey = (event) => event.key === "Escape" && onCancel();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
  return html`
    <div class="overlay" onPointerDown=${(e) => e.target === e.currentTarget && onCancel()}>
      <div class="dialog" role="alertdialog" aria-labelledby="confirm-title" aria-modal="true">
        <h2 id="confirm-title">${title}</h2>
        ${children}
        <div class="dialog-buttons">
          <button class="button" ref=${cancel} onClick=${onCancel}>Cancel</button>
          <button
            class="button ${danger ? "button-danger" : "button-primary"}"
            onClick=${onConfirm}
          >
            ${confirmLabel}
          </button>
        </div>
      </div>
    </div>
  `;
}
