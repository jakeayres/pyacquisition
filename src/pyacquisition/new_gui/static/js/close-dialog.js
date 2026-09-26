// The warning shown when the window's close button is pressed. The window asks
// for it through `window.pyacquisition.requestClose()` (see window.py), and
// closing the window stops the experiment, so it is never left running with no
// window.
import { useEffect, useState } from "preact/hooks";
import { html } from "./html.js";
import { runningTasks, shutdownExperiment } from "./api.js";

export function CloseDialog() {
  const [open, setOpen] = useState(false);
  const [tasks, setTasks] = useState([]);
  const [stopping, setStopping] = useState(false);

  useEffect(() => {
    window.pyacquisition = {
      ...window.pyacquisition,
      requestClose() {
        setOpen(true);
        runningTasks().then(setTasks, () => setTasks([]));
        return true;
      },
    };
  }, []);

  useEffect(() => {
    if (!open) return;
    const onKey = (event) => {
      if (event.key === "Escape" && !stopping) setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, stopping]);

  if (!open) return null;

  const stop = async () => {
    setStopping(true);
    try {
      await shutdownExperiment();
    } catch {
      // It has gone already, which is what was asked for.
    }
    window.pywebview?.api?.close();
  };

  return html`
    <div class="overlay">
      <div class="dialog" role="alertdialog" aria-labelledby="close-title">
        <h2 id="close-title">Stop the experiment?</h2>
        <p>Closing this window stops the experiment and all of its tasks.</p>
        ${tasks.length > 0 &&
        html`<p>Still running: <strong>${tasks.join(", ")}</strong>.</p>`}
        <div class="dialog-buttons">
          <button
            class="button"
            autofocus
            disabled=${stopping}
            onClick=${() => setOpen(false)}
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
