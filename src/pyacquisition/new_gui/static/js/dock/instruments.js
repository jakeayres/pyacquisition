// The Instruments tab: every instrument, its queries and commands, a form for
// the one picked (forms.js), and the results of the calls made to it. Its
// recent results stay, per instrument, for as long as the page is open.
import { useEffect, useLayoutEffect, useState } from "preact/hooks";
import { html } from "../html.js";
import { get } from "../api.js";
import { EndpointForm, describeEndpoint, loadSchema, withCode } from "../forms.js";
import { load, save } from "../session.js";
import { Watched } from "../store.js";
import { useStore } from "../hooks.js";
import { SearchIcon } from "../icons.js";

const KEEP = 50; // results kept for each instrument

// The results of the calls made, by instrument, newest first. Kept outside the
// tab, so they outlast it being closed and opened again, and so calls made from
// the Ctrl+K palette are listed too.
class Results extends Watched {
  constructor() {
    super();
    this.byInstrument = new Map();
  }

  of(uid) {
    return this.byInstrument.get(uid) ?? [];
  }

  add(uid, entry) {
    this.byInstrument.set(uid, [entry, ...this.of(uid)].slice(0, KEEP));
    this.changed();
  }

  clear(uid) {
    this.byInstrument.delete(uid);
    this.changed();
  }
}

export const results = new Results();

// A result as it is shown: numbers in full, nothing as "Done", and anything
// else as text or JSON.
export function formatResult(value) {
  if (value === null || value === undefined) return "Done";
  if (typeof value === "number") return String(value);
  if (typeof value === "string") return value;
  if (typeof value === "boolean") return value ? "true" : "false";
  return JSON.stringify(value);
}

// The names an instrument's list endpoint gives, whichever shape it answers in
// (a hardware instrument gives a bare list, a software one {status, data}).
const names = (answer) => (Array.isArray(answer) ? answer : answer?.data ?? []);

// Each instrument, with its endpoints sorted into queries, commands and others.
export async function loadInstruments() {
  const [root, rack] = await Promise.all([loadSchema(), get("/rack/list_instruments")]);
  const instruments = await Promise.all(
    Object.entries(rack.instruments ?? {}).map(async ([uid, kind]) => {
      const lists = [`/${uid}/queries/`, `/${uid}/commands/`];
      const [queries, commands] = await Promise.all(
        lists.map((path) => get(path).then(names, () => [])),
      );
      const endpoints = Object.entries(root.paths ?? {})
        .filter(([path, methods]) => path.startsWith(`/${uid}/`) && !lists.includes(path) && methods.get)
        .map(([path, methods]) => {
          const endpoint = describeEndpoint(path, methods.get, root);
          const method = path.slice(uid.length + 2);
          const group = queries.includes(method) ? "query" : commands.includes(method) ? "command" : "other";
          return { ...endpoint, method, group };
        })
        .sort((a, b) => a.name.localeCompare(b.name));
      return { uid, kind, endpoints };
    }),
  );
  return instruments;
}

const GROUPS = [
  ["query", "Queries"],
  ["command", "Commands"],
  ["other", "Other"],
];

// Calls an instrument's endpoint (as described by loadInstruments) with the
// form's params, and records what came back in its results. Returns the
// result's entry, or throws what the call threw (after recording it).
export async function callInstrument(uid, endpoint, params) {
  const args = Object.entries(params)
    .map(([k, v]) => `${k}=${v}`)
    .join(", ");
  const entry = {
    id: `${Date.now()}-${Math.random()}`,
    time: new Date().toLocaleTimeString(),
    name: endpoint.method,
    args,
  };
  try {
    const answer = await get(endpoint.path, { params });
    entry.value = formatResult(answer && typeof answer === "object" && "data" in answer ? answer.data : answer);
    return entry;
  } catch (e) {
    entry.value = e.message;
    entry.failed = true;
    throw e;
  } finally {
    results.add(uid, entry);
  }
}

// The instrument's recent results, in a column of their own: each call on one
// line, with its time, and what came back under it.
function ResultList({ uid, entries, onClear }) {
  return html`
    <div class="instrument-results">
      <div class="instrument-results-head">
        <span class="popover-label">Recent results</span>
        ${entries.length > 0 &&
        html`<button class="link-button link-button-plain" onClick=${onClear}>Clear</button>`}
      </div>
      ${entries.length === 0
        ? html`<p class="placeholder instrument-results-empty">No calls yet.</p>`
        : html`
            <ol class="result-list" aria-label=${`Results from ${uid}`}>
              ${entries.map(
                (entry) => html`
                  <li class="result ${entry.failed ? "failed" : ""}" key=${entry.id}>
                    <div class="result-head">
                      <span class="result-call">
                        ${entry.name}${entry.args
                          ? html`<span class="result-args">(${entry.args})</span>`
                          : ""}
                      </span>
                      <time class="result-time">${entry.time}</time>
                    </div>
                    <div class="result-value">${entry.value}</div>
                  </li>
                `,
              )}
            </ol>
          `}
    </div>
  `;
}

export function InstrumentsTab() {
  const [instruments, setInstruments] = useState(null);
  const [failed, setFailed] = useState("");
  const [picked, setPicked] = useState(() => load("instruments", {}));
  const [query, setQuery] = useState("");
  useStore(results);

  useEffect(() => {
    loadInstruments().then(setInstruments, (e) => setFailed(e.message));
  }, []);
  useLayoutEffect(() => save("instruments", picked), [picked]);

  if (failed) return html`<p class="form-error" role="alert">Couldn't load the instruments: ${failed}</p>`;
  if (!instruments) return html`<p class="placeholder">Loading the instruments…</p>`;
  if (instruments.length === 0) return html`<p class="placeholder">This experiment has no instruments.</p>`;

  const instrument = instruments.find((i) => i.uid === picked.uid) ?? instruments[0];
  const needle = query.trim().toLowerCase();
  const shown = instrument.endpoints.filter(
    (e) => !needle || `${e.name} ${e.method} ${e.description}`.toLowerCase().includes(needle),
  );
  const endpoint =
    instrument.endpoints.find((e) => e.path === picked.path) ??
    null;
  const entries = results.of(instrument.uid);

  // A failure is thrown on, for the form to show by the field it names.
  const call = (params) => callInstrument(instrument.uid, endpoint, params);

  return html`
    <div class="instruments-tab">
      <ul class="instrument-list" aria-label="Instruments">
        ${instruments.map(
          (i) => html`
            <li key=${i.uid}>
              <button
                class="instrument-item"
                aria-pressed=${i === instrument}
                onClick=${() => setPicked({ uid: i.uid })}
              >
                <span class="instrument-uid">${i.uid}</span>
                <span class="instrument-kind">${i.kind}</span>
              </button>
            </li>
          `,
        )}
      </ul>
      <div class="method-pane">
        <label class="logs-search method-search">
          <${SearchIcon} />
          <input
            type="search"
            placeholder=${`Search ${instrument.uid}`}
            aria-label="Search the queries and commands"
            value=${query}
            onInput=${(e) => setQuery(e.currentTarget.value)}
          />
        </label>
        <div class="method-list">
          ${GROUPS.map(([group, label]) => {
            const items = shown.filter((e) => e.group === group);
            if (items.length === 0) return null;
            return html`
              <div class="method-group" key=${group}>
                <div class="popover-label">${label}</div>
                <ul aria-label=${label}>
                  ${items.map(
                    (e) => html`
                      <li key=${e.path}>
                        <button
                          class="method-item"
                          data-group=${e.group}
                          aria-pressed=${e === endpoint}
                          title=${e.description}
                          onClick=${() => setPicked({ uid: instrument.uid, path: e.path })}
                        >
                          ${e.method}
                        </button>
                      </li>
                    `,
                  )}
                </ul>
              </div>
            `;
          })}
          ${shown.length === 0 && html`<p class="placeholder">Nothing matches.</p>`}
        </div>
      </div>
      <div class="call-pane">
        ${endpoint
          ? html`
              <div class="call-head">
                <h3 class="call-title">${instrument.uid}.${endpoint.method}</h3>
                <span class="call-kind" data-group=${endpoint.group}>
                  ${{ query: "Query", command: "Command", other: "" }[endpoint.group]}
                </span>
              </div>
              ${endpoint.description && html`<p class="form-help call-description">${withCode(endpoint.description)}</p>`}
              <${EndpointForm}
                key=${endpoint.path}
                endpoint=${endpoint}
                submitLabel=${endpoint.group === "command" ? "Send" : "Read"}
                onSubmit=${call}
              />
            `
          : html`<p class="placeholder">Pick a query or a command.</p>`}
      </div>
      <div class="results-pane">
        <${ResultList}
          uid=${instrument.uid}
          entries=${entries}
          onClear=${() => results.clear(instrument.uid)}
        />
      </div>
    </div>
  `;
}
