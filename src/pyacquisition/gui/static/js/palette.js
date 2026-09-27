// The palette (Ctrl+K): one search over every task that can be queued, on each
// task manager, and every instrument's queries and commands, with the form for
// the one picked (forms.js). A task is queued and the palette closes; an
// instrument's answer is shown here, and in the Instruments tab's results.
import { useEffect, useLayoutEffect, useRef, useState } from "preact/hooks";
import { html } from "./html.js";
import { get } from "./api.js";
import { EndpointForm, loadSchema, taskEndpoints, withCode } from "./forms.js";
import { CopyResult, ResultValue, callInstrument, loadInstruments } from "./dock/instruments.js";
import { SearchIcon } from "./icons.js";

const words = (query) => query.toLowerCase().split(/\s+/).filter(Boolean);
const hasAll = (text, query) => words(query).every((w) => text.toLowerCase().includes(w));
const title = (name) => name.charAt(0).toUpperCase() + name.slice(1);
const KINDS = { query: "Query", command: "Command", other: "Instrument" };

// Everything the palette offers: {id, kind, label, tag, text, endpoint, ...}.
// `text` is what the search looks in.
export function paletteItems(root, managerNames, instruments) {
  const single = managerNames.length === 1;
  const tasks = managerNames.flatMap((manager) =>
    taskEndpoints(root, manager).map((endpoint) => ({
      id: endpoint.path,
      kind: "task",
      manager,
      endpoint,
      label: endpoint.name,
      tag: single ? "Task" : `Task · ${title(manager)}`,
      text: `${endpoint.name} ${endpoint.description} task ${single ? "" : manager}`,
    })),
  );
  const calls = instruments.flatMap(({ uid, endpoints }) =>
    endpoints.map((endpoint) => ({
      id: endpoint.path,
      kind: "instrument",
      uid,
      endpoint,
      label: `${uid}.${endpoint.method}`,
      tag: KINDS[endpoint.group],
      text: `${uid} ${endpoint.method} ${endpoint.name} ${endpoint.description} ${KINDS[endpoint.group]}`,
    })),
  );
  return [...tasks, ...calls];
}

// The words of a label: "clock.read_timer" and "WaitFor" as clock, read, timer
// and wait, for.
const labelWords = (label) =>
  label
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .toLowerCase()
    .split(/[^a-z0-9]+/)
    .filter(Boolean);

// How well an item's label matches the search: every word a word of it (3),
// the start of one (2), in it anywhere (1), or only in the rest of its text (0).
function rank(item, query) {
  const wanted = words(query);
  const own = labelWords(item.label);
  if (wanted.every((w) => own.includes(w))) return 3;
  if (wanted.every((w) => own.some((o) => o.startsWith(w)))) return 2;
  return hasAll(item.label, query) ? 1 : 0;
}

// What matches every word of the search, best first (and otherwise in the
// order given).
export function searchItems(items, query) {
  return items
    .filter((item) => hasAll(item.text, query))
    .map((item, index) => ({ item, index, rank: rank(item, query) }))
    .sort((a, b) => b.rank - a.rank || a.index - b.index)
    .map(({ item }) => item);
}

// `managers` is the task managers' states (polled), and `onQueued` is told
// when a task has been queued.
export function Palette({ managers, onQueued, onClose }) {
  const [items, setItems] = useState(null);
  const [failed, setFailed] = useState("");
  const [query, setQuery] = useState("");
  const [picked, setPicked] = useState(null); // the id of the item picked
  const [answer, setAnswer] = useState(null); // an instrument's, as a result entry
  const searchBox = useRef(null);
  const dialog = useRef(null);
  const list = useRef(null);
  const names = Object.keys(managers ?? { main: null });

  useEffect(() => {
    Promise.all([loadSchema(), loadInstruments().catch(() => [])]).then(
      ([root, instruments]) => setItems(paletteItems(root, names, instruments)),
      (e) => setFailed(e.message),
    );
  }, [names.join()]);

  // The search has the focus from the start; it goes back where it was after.
  useLayoutEffect(() => {
    const before = document.activeElement;
    searchBox.current?.focus();
    const onKey = (event) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("keydown", onKey);
      if (before instanceof HTMLElement && before.isConnected) before.focus();
    };
  }, []);

  const shown = searchItems(items ?? [], query);
  const current = shown.find((item) => item.id === picked) ?? shown[0] ?? null;

  // The item picked stays in view as the arrow keys move through the list.
  useEffect(() => {
    list.current?.querySelector("[aria-selected='true']")?.scrollIntoView({ block: "nearest" });
  }, [current?.id]);

  const pick = (item) => {
    setPicked(item.id);
    setAnswer(null);
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
      dialog.current
        ?.querySelector(".endpoint-form input, .endpoint-form select, .endpoint-form button")
        ?.focus();
    }
  };

  const submit = async (params) => {
    if (current.kind === "task") {
      await get(current.endpoint.path, { params });
      onQueued();
      onClose();
    } else {
      setAnswer(null);
      setAnswer(await callInstrument(current.uid, current.endpoint, params));
    }
  };

  let body;
  if (failed) {
    body = html`<p class="form-error" role="alert">Couldn't load the tasks and instruments: ${failed}</p>`;
  } else if (!items) {
    body = html`<p class="placeholder">Loading…</p>`;
  } else {
    body = html`
      <div class="palette-body">
        <ul class="task-list palette-list" role="listbox" aria-label="Tasks and instruments" ref=${list}>
          ${shown.map(
            (item) => html`
              <li
                key=${item.id}
                role="option"
                aria-selected=${item === current}
                class="task-option palette-option"
                onClick=${() => pick(item)}
              >
                <span class="palette-option-head">
                  <span class="task-option-name">${item.label}</span>
                  <span class="palette-tag" data-kind=${item.kind}>${item.tag}</span>
                </span>
                ${item.endpoint.description &&
                html`<span class="task-option-description">${withCode(item.endpoint.description)}</span>`}
              </li>
            `,
          )}
          ${shown.length === 0 && html`<li class="placeholder task-none">Nothing matches.</li>`}
        </ul>
        <div class="task-form-pane palette-form">
          ${current &&
          html`
            <h3 class="task-form-title">${current.label}</h3>
            ${current.endpoint.description &&
            html`<p class="task-form-description">${withCode(current.endpoint.description)}</p>`}
            <${EndpointForm}
              key=${current.id}
              endpoint=${current.endpoint}
              submitLabel=${current.kind === "task"
                ? "Add to queue"
                : current.endpoint.group === "command"
                  ? "Send"
                  : "Read"}
              onSubmit=${submit}
            />
            ${answer &&
            html`
              <div class="palette-answer" role="status">
                <div class="result-head">
                  <span class="popover-label">${answer.took} · ${answer.time}</span>
                  <${CopyResult} entry=${answer} />
                </div>
                <${ResultValue} entry=${answer} />
              </div>
            `}
          `}
        </div>
      </div>
    `;
  }

  return html`
    <div class="overlay palette-overlay" onPointerDown=${(e) => e.target === e.currentTarget && onClose()}>
      <div
        class="dialog palette"
        role="dialog"
        aria-modal="true"
        aria-label="Queue a task or call an instrument"
        ref=${dialog}
      >
        <label class="logs-search palette-search">
          <${SearchIcon} />
          <input
            ref=${searchBox}
            type="search"
            placeholder="Queue a task or call an instrument…"
            aria-label="Search tasks and instruments"
            value=${query}
            onInput=${(e) => {
              setQuery(e.currentTarget.value);
              setAnswer(null);
            }}
            onKeyDown=${onSearchKey}
          />
          <kbd class="palette-hint">Esc</kbd>
        </label>
        ${body}
      </div>
    </div>
  `;
}
