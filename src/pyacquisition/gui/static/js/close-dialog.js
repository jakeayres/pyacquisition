// The warning shown before the experiment stops: when the window's close button
// is pressed (the window asks for it through `window.pyacquisition.requestClose()`,
// see window.py), or the top bar's stop button. Closing the window stops the
// experiment, so it is never left running with no window.
import { useEffect, useState } from "preact/hooks";
import { html } from "./html.js";
import { runningTasks, shutdownExperiment } from "./api.js";

const REASONS = {
  window: "Closing this window stops the experiment and all of its tasks.",
  button: "This stops the experiment and all of its tasks.",
};

export function CloseDialog() {
  const [reason, setReason] = useState(null); // open while there is one
  const [tasks, setTasks] = useState([]);
  const [stopping, setStopping] = useState(false);
  const [stopped, setStopped] = useState(false);

  useEffect(() => {
    window.pyacquisition = {
      ...window.pyacquisition,
      requestClose(why = "window") {
        setReason(why in REASONS ? why : "window");
        runningTasks().then(setTasks, () => setTasks([]));
        return true;
      },
    };
  }, []);

  useEffect(() => {
    if (!reason) return;
    const onKey = (event) => {
      if (event.key === "Escape" && !stopping && !stopped) setReason(null);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [reason, stopping, stopped]);

  if (!reason) return null;

  const stop = async () => {
    setStopping(true);
    // The connection dropping now is expected, so it raises no alert (alerts.js).
    window.pyacquisition.stopping = true;
    try {
      await shutdownExperiment();
    } catch {
      // It has gone already, which is what was asked for.
    }
    if (window.pywebview?.api) {
      window.pywebview.api.close();
    } else {
      setStopped(true); // a browser tab, which only its user can close
    }
  };

  if (stopped) {
    return html`
      <div class="overlay">
        <div class="dialog" role="alertdialog" aria-labelledby="close-title">
          <h2 id="close-title">The experiment has stopped</h2>
          <p>You can close this tab.</p>
        </div>
      </div>
    `;
  }

  return html`
    <div class="overlay">
      <div class="dialog" role="alertdialog" aria-labelledby="close-title">
        <h2 id="close-title">Stop the experiment?</h2>
        <p>${REASONS[reason]}</p>
        ${tasks.length > 0 &&
        html`<p>Still running: <strong>${tasks.join(", ")}</strong>.</p>`}
        <div class="dialog-buttons">
          <button
            class="button"
            autofocus
            disabled=${stopping}
            onClick=${() => setReason(null)}
          >
            Keep running
          </button>
          <button class="button button-danger" disabled=${stopping} onClick=${stop}>
            ${stopping ? "Stopping…" : "Stop experiment"}
          </button>
        </div>
      </div>
    </div>
  `;
}
