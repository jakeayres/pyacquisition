// Saving a task manager's queue as a sequence, and loading one onto it (see
// core/sequences.py). Sequences are kept as files by the experiment, so they
// last from one run to the next.
import { useEffect, useLayoutEffect, useRef, useState } from "preact/hooks";
import { html } from "../html.js";
import { deleteSequence, loadSequence, saveSequence, sequences } from "../api.js";

// Escape closes a dialog, from the moment it opens.
function useEscape(onClose) {
  useLayoutEffect(() => {
    const onKey = (event) => event.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
}

function Dialog({ id, title, onClose, wide = false, children }) {
  return html`
    <div class="overlay" onPointerDown=${(e) => e.target === e.currentTarget && onClose()}>
      <div
        class="dialog sequence-dialog ${wide ? "sequence-dialog-wide" : ""}"
        role="dialog"
        aria-modal="true"
        aria-labelledby=${id}
      >
        <h2 id=${id}>${title}</h2>
        ${children}
      </div>
    </div>
  `;
}

// When a sequence was saved, as the list shows it.
export function savedWhen(saved) {
  const date = saved ? new Date(saved) : null;
  if (!date || Number.isNaN(date.getTime())) return "";
  return date.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

export function SaveSequenceDialog({ manager, label, running, count, onClose }) {
  const [name, setName] = useState("");
  const [includeRunning, setIncludeRunning] = useState(true);
  const [error, setError] = useState("");
  const [taken, setTaken] = useState(false); // a sequence has that name already
  const [done, setDone] = useState(null); // {saved, skipped}
  const [busy, setBusy] = useState(false);
  const box = useRef(null);
  useEscape(onClose);
  useEffect(() => box.current?.focus(), []);

  const save = async (overwrite = false) => {
    setError("");
    setBusy(true);
    try {
      const result = await saveSequence(name, manager, { includeRunning, overwrite });
      if (result.skipped.length === 0) return onClose();
      setDone(result);
    } catch (e) {
      if (e.status === 409) setTaken(true);
      else setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const total = count + (running && includeRunning ? 1 : 0);
  if (done) {
    return html`
      <${Dialog} id="save-sequence-title" title="Sequence saved" onClose=${onClose}>
        <p>${`Saved ${done.saved} ${done.saved === 1 ? "task" : "tasks"} as ${name.trim()}.`}</p>
        <p class="sequence-skipped" role="status">
          ${`Not saved, because they weren't queued from the interface or the API: ` +
          `${done.skipped.join(", ")}.`}
        </p>
        <div class="dialog-buttons">
          <button class="button button-primary" onClick=${onClose}>Done</button>
        </div>
      <//>
    `;
  }
  return html`
    <${Dialog}
      id="save-sequence-title"
      title=${`Save ${label ? `the ${label} queue` : "the queue"} as a sequence`}
      onClose=${onClose}
    >
      <form
        class="endpoint-form"
        onSubmit=${(event) => {
          event.preventDefault();
          save(false);
        }}
      >
        <label class="field">
          <span>Name</span>
          <input
            class="text-input"
            ref=${box}
            value=${name}
            placeholder="cooldown"
            onInput=${(event) => {
              setName(event.currentTarget.value);
              setTaken(false);
              setError("");
            }}
          />
        </label>
        ${running &&
        html`
          <label class="check">
            <input
              type="checkbox"
              checked=${includeRunning}
              onChange=${(event) => setIncludeRunning(event.currentTarget.checked)}
            />
            ${`Start with the running task (${running})`}
          </label>
        `}
        <p class="form-help">
          ${`${total} ${total === 1 ? "task" : "tasks"}, kept in the experiment's sequences folder.`}
        </p>
        ${taken &&
        html`
          <p class="form-error" role="alert">
            ${`There is already a sequence called ${name.trim()}.`}
            <button type="button" class="link-button sequence-replace" onClick=${() => save(true)}>
              Replace it
            </button>
          </p>
        `}
        ${error && html`<p class="form-error" role="alert">${error}</p>`}
        <div class="dialog-buttons">
          <button type="button" class="button" onClick=${onClose}>Cancel</button>
          <button type="submit" class="button button-primary" disabled=${busy || !name.trim()}>
            Save
          </button>
        </div>
      </form>
    <//>
  `;
}

export function LoadSequenceDialog({ manager, label, onLoaded, onClose }) {
  const [list, setList] = useState(null);
  const [error, setError] = useState("");
  const [deleting, setDeleting] = useState(null); // the name being asked about
  const first = useRef(null);
  useEscape(onClose);

  const refresh = () => sequences().then(setList, (e) => setError(e.message));
  useEffect(() => {
    refresh();
  }, []);
  useEffect(() => {
    if (list) first.current?.focus();
  }, [list !== null]);

  const load = async (name) => {
    setError("");
    try {
      await loadSequence(name, manager);
      onLoaded();
      onClose();
    } catch (e) {
      setError(`Couldn't load ${name}:\n${e.message}`);
    }
  };

  const remove = async (name) => {
    setDeleting(null);
    try {
      await deleteSequence(name);
    } catch (e) {
      setError(e.message);
    }
    refresh();
  };

  return html`
    <${Dialog}
      id="load-sequence-title"
      title=${`Load a sequence${label ? ` onto ${label}` : ""}`}
      onClose=${onClose}
      wide
    >
      ${!list && !error && html`<p class="placeholder">Loading the sequences…</p>`}
      ${list?.length === 0 &&
      html`<p class="placeholder">No sequences yet. Save a queue to make one.</p>`}
      ${list?.length > 0 &&
      html`
        <ul class="sequence-list" aria-label="Sequences">
          ${list.map(
            (sequence, index) => html`
              <li class="sequence" key=${sequence.name} data-sequence=${sequence.name}>
                <div class="sequence-head">
                  <span class="sequence-name">${sequence.name}</span>
                  <span class="sequence-meta">
                    ${`${sequence.tasks.length} ${sequence.tasks.length === 1 ? "task" : "tasks"}`}
                    ${savedWhen(sequence.saved) && ` · saved ${savedWhen(sequence.saved)}`}
                  </span>
                  <div class="sequence-actions">
                    ${deleting === sequence.name
                      ? html`
                          <span class="sequence-ask">Delete it?</span>
                          <button class="button button-small button-danger-quiet" onClick=${() => remove(sequence.name)}>
                            Delete
                          </button>
                          <button class="button button-small" onClick=${() => setDeleting(null)}>
                            Keep
                          </button>
                        `
                      : html`
                          <button
                            class="link-button"
                            aria-label=${`Delete ${sequence.name}`}
                            onClick=${() => setDeleting(sequence.name)}
                          >
                            Delete
                          </button>
                          <button
                            class="button button-small button-primary"
                            ref=${index === 0 ? first : undefined}
                            aria-label=${`Load ${sequence.name}`}
                            onClick=${() => load(sequence.name)}
                          >
                            Load
                          </button>
                        `}
                  </div>
                </div>
                <ol class="sequence-tasks">
                  ${sequence.tasks.map((task, i) => html`<li key=${i}>${task}</li>`)}
                </ol>
              </li>
            `,
          )}
        </ul>
      `}
      ${error && html`<p class="form-error sequence-error" role="alert">${error}</p>`}
      <div class="dialog-buttons">
        <button class="button" onClick=${onClose}>Close</button>
      </div>
    <//>
  `;
}
