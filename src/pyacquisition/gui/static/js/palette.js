// The palette (Ctrl+K): one search over every task that can be queued, on each
// task manager, and every instrument's queries and commands, with the form for
// the one picked (forms.js). A task is queued and the palette closes; an
// instrument's answer is shown here, and in the Instruments tab's results.
//
// The inputs can be typed on the search line after the search (palette-line.js):
// `wait 0 5` fills WaitFor's form with hours 0 and minutes 5 as it is typed, and
// Enter then queues it. Tab locks in the item picked, so everything typed after
// its label is an argument.
import { useEffect, useLayoutEffect, useRef, useState } from "preact/hooks";
import { html } from "./html.js";
import { get } from "./api.js";
import { EndpointForm, loadSchema, taskEndpoints, withCode } from "./forms.js";
import { matchArguments, searchItems, splitLine } from "./palette-line.js";
import { CopyResult, ResultValue, callInstrument, loadInstruments } from "./dock/instruments.js";
import { SearchIcon } from "./icons.js";

export { searchItems } from "./palette-line.js";

const title = (name) => name.charAt(0).toUpperCase() + name.slice(1);
const KINDS = { query: "Query", command: "Command", other: "Instrument" };

// Everything the palette offers. Each item is {id, kind, label, tag, text,
// description, fields, submitLabel, run, closes}, with the `endpoint` its form
// is for. `text` is what the search looks in, and `run(params)` does what the
// form's button does, giving an answer to show (or nothing).
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
      description: endpoint.description,
      fields: endpoint.fields,
      submitLabel: "Add to queue",
      run: async (params) => {
        await get(endpoint.path, { params });
      },
      closes: true,
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
      description: endpoint.description,
      fields: endpoint.fields,
      submitLabel: endpoint.group === "command" ? "Send" : "Read",
      run: (params) => callInstrument(uid, endpoint, params),
      closes: false,
    })),
  );
  return [...tasks, ...calls];
}

// What Enter does, in the hint, by the form's button.
const ENTER = { "Add to queue": "Enter to queue", Send: "Enter to send", Read: "Enter to read" };

// Under the search box, while arguments are typed: each input given, with its
// value, those left to their defaults, and each problem.
function ArgumentHint({ item, match }) {
  const given = new Set(match.given.map(([name]) => name));
  const left = item.fields.filter((f) => !given.has(f.name) && !match.errors[f.name]);
  return html`
    <p class="palette-args" aria-live="polite">
      ${match.given.map(
        ([name, text]) => html`<span class="palette-arg" key=${name}>${name}=${text}</span>`,
      )}
      ${left.map((f) => html`<span class="palette-arg palette-arg-left" key=${f.name}>${f.name}: default</span>`)}
      ${Object.values(match.errors)
        .concat(match.problems)
        .map((problem) => html`<span class="palette-arg palette-arg-problem">${withCode(problem)}</span>`)}
      ${match.ok &&
      html`<span class="palette-arg palette-arg-ready">✓ ${ENTER[item.submitLabel] ?? "Enter to run"}</span>`}
    </p>
  `;
}

// `managers` is the task managers' states (polled), and `onQueued` is told
// when a task has been queued.
export function Palette({ managers, onQueued, onClose }) {
  const [items, setItems] = useState(null);
  const [failed, setFailed] = useState("");
  const [query, setQuery] = useState("");
  const [picked, setPicked] = useState(null); // the id of the item picked
  const [locked, setLocked] = useState(null); // the id of the item Tab locked in
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

  const all = items ?? [];
  const lockedItem = all.find((item) => item.id === locked) ?? null;
  const line = splitLine(query, all, lockedItem);
  const shown = searchItems(all, line.search);
  const current = line.locked
    ? lockedItem
    : (shown.find((item) => item.id === picked) ?? shown[0] ?? null);
  const typed = line.arguments.length > 0;
  const match = current && typed ? matchArguments(current.fields, line.arguments) : null;

  // The item picked stays in view as the arrow keys move through the list.
  useEffect(() => {
    list.current?.querySelector("[aria-selected='true']")?.scrollIntoView({ block: "nearest" });
  }, [current?.id]);

  const pick = (item) => {
    setPicked(item.id);
    setAnswer(null);
  };

  const form = () => dialog.current?.querySelector(".endpoint-form");

  // Up and down in the search move through the list. Tab locks in the item
  // picked, so what follows its label is its inputs. Enter runs it when it
  // takes no inputs, or when those typed are complete and right; otherwise it
  // goes to the form (to the first input that is wrong, if any).
  const onSearchKey = (event) => {
    const index = shown.indexOf(current);
    if (event.key === "ArrowDown" && index < shown.length - 1 && !line.locked) {
      event.preventDefault();
      pick(shown[index + 1]);
    } else if (event.key === "ArrowUp" && index > 0 && !line.locked) {
      event.preventDefault();
      pick(shown[index - 1]);
    } else if (event.key === "Tab" && !event.shiftKey && current && query.trim() && !line.locked) {
      event.preventDefault();
      setLocked(current.id);
      setQuery(`${current.label} `);
      setAnswer(null);
    } else if (event.key === "Enter" && current) {
      event.preventDefault();
      if (current.fields.length === 0 || match?.ok) {
        form()?.requestSubmit();
      } else if (match) {
        form()?.querySelector("[aria-invalid='true']")?.focus();
      } else {
        form()?.querySelector("input, select, button")?.focus();
      }
    }
  };

  const submit = async (params) => {
    const item = current;
    setAnswer(null);
    const result = await item.run(params);
    if (item.kind === "task") onQueued();
    if (item.closes) onClose();
    else if (result) setAnswer(result);
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
                ${item.description &&
                html`<span class="task-option-description">${withCode(item.description)}</span>`}
              </li>
            `,
          )}
          ${shown.length === 0 && html`<li class="placeholder task-none">Nothing matches.</li>`}
        </ul>
        <div class="task-form-pane palette-form">
          ${current &&
          html`
            <h3 class="task-form-title">${current.label}</h3>
            ${current.description &&
            html`<p class="task-form-description">${withCode(current.description)}</p>`}
            <${EndpointForm}
              key=${match ? `${current.id} ${JSON.stringify(match.values)} ${JSON.stringify(match.errors)}` : current.id}
              endpoint=${{ path: current.id, fields: current.fields }}
              submitLabel=${current.submitLabel}
              initialValues=${match?.values}
              lineErrors=${match?.errors}
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
              const value = e.currentTarget.value;
              setQuery(value);
              setAnswer(null);
              // Deleting into the locked label lets it go.
              if (lockedItem && !value.toLowerCase().startsWith(`${lockedItem.label} `.toLowerCase())) {
                setLocked(null);
              }
            }}
            onKeyDown=${onSearchKey}
          />
          <kbd class="palette-hint">Esc</kbd>
        </label>
        ${current && match && html`<${ArgumentHint} item=${current} match=${match} />`}
        ${body}
      </div>
    </div>
  `;
}
