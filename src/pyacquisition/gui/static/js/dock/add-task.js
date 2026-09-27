// Adding a task to a task manager's queue: every task it can queue, in a list
// that a search narrows, and a form for the one picked (forms.js). It stays
// open after adding, so several can be queued in turn.
import { useEffect, useLayoutEffect, useRef, useState } from "preact/hooks";
import { html } from "../html.js";
import { get } from "../api.js";
import { EndpointForm, loadSchema, taskEndpoints, withCode } from "../forms.js";
import { SearchIcon } from "../icons.js";

const words = (query) => query.toLowerCase().split(/\s+/).filter(Boolean);
const hasAll = (text, query) => words(query).every((w) => text.toLowerCase().includes(w));

// Whether a task matches the search: every word of it, in its name or
// description, whatever the case.
export function matches(endpoint, query) {
  return hasAll(`${endpoint.name} ${endpoint.description}`, query);
}

// The tasks that match, those whose name does first (in the order given).
export function search(endpoints, query) {
  const found = endpoints.filter((endpoint) => matches(endpoint, query));
  const byName = found.filter((endpoint) => hasAll(endpoint.name, query));
  return [...byName, ...found.filter((endpoint) => !byName.includes(endpoint))];
}

export function AddTaskDialog({ manager, label, onAdded, onClose }) {
  const [endpoints, setEndpoints] = useState(null);
  const [failed, setFailed] = useState("");
  const [query, setQuery] = useState("");
  const [picked, setPicked] = useState(null); // the path of the task picked
  const [added, setAdded] = useState("");
  const searchBox = useRef(null);
  const dialog = useRef(null);

  useEffect(() => {
    loadSchema().then(
      (root) => setEndpoints(taskEndpoints(root, manager)),
      (e) => setFailed(e.message),
    );
  }, [manager]);

  // The search takes the focus once there is a list to search.
  useEffect(() => {
    if (endpoints) searchBox.current?.focus();
  }, [endpoints]);

  // Escape closes it, from the moment it opens.
  useLayoutEffect(() => {
    const onKey = (event) => event.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const shown = search(endpoints ?? [], query);
  const current = shown.find((e) => e.path === picked) ?? shown[0] ?? null;

  const pick = (endpoint) => {
    setPicked(endpoint.path);
    setAdded("");
  };

  // Up and down in the search move through the list; Enter goes to the form.
  const onSearchKey = (event) => {
    const index = shown.indexOf(current);
    if (event.key === "ArrowDown" && index < shown.length - 1) {
      event.preventDefault();
      pick(shown[index + 1]);
    } else if (event.key === "ArrowUp" && index > 0) {
      event.preventDefault();
      pick(shown[index - 1]);
    } else if (event.key === "Enter" && current) {
      event.preventDefault();
      dialog.current?.querySelector(".endpoint-form input, .endpoint-form select, .endpoint-form button")?.focus();
    }
  };

  const add = async (params) => {
    await get(current.path, { params });
    setAdded(`${current.name} added to the queue.`);
    onAdded();
  };

  let body;
  if (failed) {
    body = html`<p class="form-error" role="alert">Couldn't load the tasks: ${failed}</p>`;
  } else if (!endpoints) {
    body = html`<p class="placeholder">Loading the tasks…</p>`;
  } else if (endpoints.length === 0) {
    body = html`<p class="placeholder">No tasks can be queued here.</p>`;
  } else {
    body = html`
      <div class="task-picker">
        <div class="task-list-pane">
          <label class="logs-search task-search">
            <${SearchIcon} />
            <input
              ref=${searchBox}
              type="search"
              placeholder="Search tasks"
              aria-label="Search tasks"
              value=${query}
              onInput=${(e) => {
                setQuery(e.currentTarget.value);
                setAdded("");
              }}
              onKeyDown=${onSearchKey}
            />
          </label>
          <ul class="task-list" role="listbox" aria-label="Tasks">
            ${shown.map(
              (endpoint) => html`
                <li
                  key=${endpoint.path}
                  role="option"
                  aria-selected=${endpoint === current}
                  class="task-option"
                  onClick=${() => pick(endpoint)}
                >
                  <span class="task-option-name">${endpoint.name}</span>
                  ${endpoint.description &&
                  html`<span class="task-option-description">${withCode(endpoint.description)}</span>`}
                </li>
              `,
            )}
            ${shown.length === 0 && html`<li class="placeholder task-none">No task matches.</li>`}
          </ul>
        </div>
        <div class="task-form-pane">
          ${current &&
          html`
            <h3 class="task-form-title">${current.name}</h3>
            ${current.description &&
            html`<p class="task-form-description">${withCode(current.description)}</p>`}
            <${EndpointForm}
              key=${current.path}
              endpoint=${current}
              submitLabel="Add to queue"
              onSubmit=${add}
            />
            ${added && html`<p class="form-added" role="status">${added}</p>`}
          `}
        </div>
      </div>
    `;
  }

  return html`
    <div class="overlay" onPointerDown=${(e) => e.target === e.currentTarget && onClose()}>
      <div
        class="dialog task-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="add-task-title"
        ref=${dialog}
      >
        <div class="task-dialog-head">
          <h2 id="add-task-title">Add a task${label ? ` to ${label}` : ""}</h2>
          <button class="button button-small" onClick=${onClose}>Done</button>
        </div>
        ${body}
      </div>
    </div>
  `;
}
