// The Measurements section: each measurement, with its instrument, the query it
// calls every period (any of the driver's), that query's arguments, and a unit.
// The argument form is built from the schema of the query's route on the setup
// server (/setup/drivers/<driver>/<query>), as forms are for a running
// instrument. Their order is the order of the data file's columns.
import { useEffect, useState } from "preact/hooks";
import { html } from "../html.js";
import { describeEndpoint, Field, loadSchema, withCode } from "../forms.js";
import { ChevronDownIcon, ChevronUpIcon, PlusIcon } from "../icons.js";

const WHOLE = /^[+-]?\d+$/;
const NUMBER = /^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$/;

// The API schema, fetched once, for the argument forms.
let schemaPromise = null;
export function useSchema() {
  const [schema, setSchema] = useState(null);
  useEffect(() => {
    schemaPromise ??= loadSchema();
    schemaPromise.then(setSchema, () => (schemaPromise = null));
  }, []);
  return schema;
}

// The fields of a driver's query's arguments.
function argumentFields(schema, driver, method) {
  const path = `/setup/drivers/${driver}/${method}`;
  const endpoint = schema?.paths?.[path]?.get;
  if (!endpoint) return [];
  return describeEndpoint(path, endpoint, schema).fields.map((field) => ({
    ...field,
    title: field.name,
    placeholder: field.default === undefined || field.default === null ? undefined : String(field.default),
  }));
}

// A value in the config as its field holds it, and back.
function fieldValue(field, value) {
  if (field.type === "boolean") return value === true;
  return value === undefined || value === null ? "" : String(value);
}
function configValue(field, typed) {
  if (field.type === "boolean") return typed;
  const t = String(typed).trim();
  if (field.type === "integer") return WHOLE.test(t) ? Number(t) : typed;
  if (field.type === "number") return NUMBER.test(t) ? Number(t) : typed;
  return typed;
}

// An object with one key renamed, in its place, and with two keys swapped.
const renamed = (object, from, to) =>
  Object.fromEntries(Object.entries(object).map(([k, v]) => [k === from ? to : k, v]));
function swapped(object, i, j) {
  const entries = Object.entries(object);
  [entries[i], entries[j]] = [entries[j], entries[i]];
  return Object.fromEntries(entries);
}

// The columns' names: the measurements', then the calculations'.
export function columnNames(config) {
  return [...Object.keys(config.measurements ?? {}), ...Object.keys(config.calculations ?? {})];
}

// A name for a new measurement of a query: `get_x` gives `x`.
function freeName(method, taken) {
  const base = method.replace(/^get_/, "") || "value";
  if (!taken.includes(base)) return base;
  let n = 2;
  while (taken.includes(`${base}_${n}`)) n += 1;
  return `${base}_${n}`;
}

const at = (problems, ...where) =>
  problems
    .filter((p) => p.where.length === where.length && where.every((w, i) => p.where[i] === w))
    .map((p) => p.message);

function MeasurementCard({ name, index, count, entry, instruments, drivers, schema, taken, problems, onChange, onRename, onMove, onRemove }) {
  const [draftName, setDraftName] = useState(name);
  const [nameProblem, setNameProblem] = useState("");
  const driverName = instruments[entry.instrument]?.instrument;
  const driver = drivers[driverName];
  const queries = driver?.queries ?? [];
  const query = queries.find((q) => q.name === entry.method);
  const fields = query ? argumentFields(schema, driverName, entry.method) : [];
  const args = entry.args ?? {};
  const id = (key) => `measurement-${name}-${key}`;
  const error = (...where) => at(problems, "measurements", name, ...where).join(" ");

  const set = (changes) => {
    const next = { ...entry, ...changes };
    for (const key of Object.keys(next)) if (next[key] === undefined) delete next[key];
    onChange(next);
  };
  const setArg = (field, typed) => {
    const next = { ...args };
    if (typed === "" || (field.type === "boolean" && typed === (field.default ?? false))) delete next[field.name];
    else next[field.name] = configValue(field, typed);
    set({ args: Object.keys(next).length ? next : undefined });
  };
  const rename = () => {
    const to = draftName.trim();
    if (to === name) return setNameProblem("");
    if (!to) return setNameProblem("It needs a name.");
    if (taken.includes(to)) return setNameProblem(`There is already a column called ${to}.`);
    setNameProblem("");
    onRename(to);
  };

  const instrumentChoices = Object.keys(instruments);
  if (entry.instrument && !instrumentChoices.includes(entry.instrument)) instrumentChoices.push(entry.instrument);
  const methodChoices = queries.map((q) => q.name);
  if (entry.method && !methodChoices.includes(entry.method)) methodChoices.push(entry.method);

  return html`
    <article class="setup-card" aria-label=${`Measurement ${name}`}>
      <header class="setup-card-header">
        <div class="setup-card-title">
          <input
            class="text-input setup-card-name"
            id=${id("name")}
            aria-label="Name"
            title="The column's name in the data file"
            value=${draftName}
            aria-invalid=${!!nameProblem}
            onInput=${(e) => setDraftName(e.currentTarget.value)}
            onChange=${rename}
            onKeyDown=${(e) => e.key === "Enter" && e.currentTarget.blur()}
          />
          <span class="setup-card-kind">column ${index + 1}</span>
        </div>
        <div class="setup-card-actions">
          <button class="icon-button" aria-label=${`Move ${name} up`} title="Move up" disabled=${index === 0} onClick=${() => onMove(-1)}>
            <${ChevronUpIcon} />
          </button>
          <button class="icon-button" aria-label=${`Move ${name} down`} title="Move down" disabled=${index === count - 1} onClick=${() => onMove(1)}>
            <${ChevronDownIcon} />
          </button>
          <button class="button button-small button-danger-quiet" onClick=${onRemove}>Remove</button>
        </div>
      </header>
      ${nameProblem && html`<p class="form-error" role="alert">${nameProblem}</p>`}
      ${at(problems, "measurements", name).map((m) => html`<p class="form-error">${withCode(m)}</p>`)}
      <div class="setup-card-fields">
        <${Field}
          id=${id("instrument")}
          field=${{ name: "instrument", title: "instrument", type: "choice", required: true,
            choices: instrumentChoices, labels: instrumentChoices }}
          value=${entry.instrument ?? ""}
          error=${error("instrument")}
          onChange=${(value) => {
            const nextDriver = drivers[instruments[value]?.instrument];
            const keeps = nextDriver?.queries.some((q) => q.name === entry.method);
            set({ instrument: value || undefined, ...(keeps ? {} : { method: undefined, args: undefined }) });
          }}
        />
        <${Field}
          id=${id("method")}
          field=${{ name: "method", title: "method", type: "choice", required: true,
            choices: methodChoices, labels: methodChoices, description: query?.doc ?? "" }}
          value=${entry.method ?? ""}
          error=${error("method")}
          onChange=${(value) => set({ method: value || undefined, args: undefined })}
        />
        ${fields.map(
          (field) => html`
            <${Field}
              key=${field.name}
              id=${id(`arg-${field.name}`)}
              field=${field}
              value=${fieldValue(field, args[field.name])}
              error=${error("args", field.name)}
              onChange=${(typed) => setArg(field, typed)}
            />
          `,
        )}
        <${Field}
          id=${id("unit")}
          field=${{ name: "unit", title: "unit", type: "text",
            description: "Shown beside its value, and on plot axes. It doesn't change the data." }}
          value=${entry.unit ?? ""}
          error=${error("unit")}
          onChange=${(value) => set({ unit: value === "" ? undefined : value })}
        />
      </div>
      ${Object.keys(args)
        .filter((key) => !fields.some((f) => f.name === key))
        .map((key) => html`<p class="form-error">${withCode(error("args", key))}</p>`)}
    </article>
  `;
}

function AddMeasurement({ instruments, drivers, taken, onAdd }) {
  const [open, setOpen] = useState(false);
  const [instrument, setInstrument] = useState("");
  const [method, setMethod] = useState("");
  const [name, setName] = useState("");
  const [problem, setProblem] = useState("");
  const names = Object.keys(instruments);
  const queries = drivers[instruments[instrument]?.instrument]?.queries ?? [];

  const add = (event) => {
    event.preventDefault();
    if (!instrument) return setProblem("Pick an instrument.");
    if (!method) return setProblem("Pick what to measure.");
    const chosen = name.trim() || freeName(method, taken);
    if (taken.includes(chosen)) return setProblem(`There is already a column called ${chosen}.`);
    onAdd(chosen, { instrument, method });
    setOpen(false);
    setMethod("");
    setName("");
    setProblem("");
  };

  if (!open) {
    return html`
      <button class="button button-small" disabled=${names.length === 0} onClick=${() => setOpen(true)}
        title=${names.length ? "" : "Add an instrument first"}>
        <${PlusIcon} /> Add measurement
      </button>
    `;
  }
  return html`
    <form class="setup-add" onSubmit=${add} aria-label="Add measurement" noValidate>
      <div class="form-field">
        <label for="add-measurement-instrument">Instrument</label>
        <select class="text-input" id="add-measurement-instrument" value=${instrument}
          onChange=${(e) => { setInstrument(e.currentTarget.value); setMethod(""); setProblem(""); }}>
          <option value="">Choose…</option>
          ${names.map((n) => html`<option value=${n}>${n}</option>`)}
        </select>
      </div>
      <div class="form-field">
        <label for="add-measurement-method">Query</label>
        <select class="text-input" id="add-measurement-method" value=${method} disabled=${!instrument}
          onChange=${(e) => { setMethod(e.currentTarget.value); setProblem(""); }}>
          <option value="">Choose…</option>
          ${queries.map((q) => html`<option value=${q.name} title=${q.doc}>${q.name}</option>`)}
        </select>
      </div>
      <div class="form-field">
        <label for="add-measurement-name">Name</label>
        <input class="text-input" id="add-measurement-name" value=${name}
          placeholder=${method ? freeName(method, taken) : "The column's name"}
          onInput=${(e) => setName(e.currentTarget.value)} />
      </div>
      ${problem && html`<p class="form-error" role="alert">${problem}</p>`}
      <div class="form-buttons">
        <button type="button" class="button button-small" onClick=${() => setOpen(false)}>Cancel</button>
        <button type="submit" class="button button-small button-primary">Add</button>
      </div>
    </form>
  `;
}

export function MeasurementsSection({ described, config, problems, onChange }) {
  const schema = useSchema();
  const measurements = config.measurements ?? {};
  const names = Object.keys(measurements);
  const instruments = config.instruments ?? {};
  const drivers = Object.fromEntries(described.drivers.map((d) => [d.name, d]));
  const taken = columnNames(config);

  const withMeasurements = (next, base = config) => {
    const result = { ...base };
    if (Object.keys(next).length) result.measurements = next;
    else delete result.measurements;
    return result;
  };
  // Renaming a column renames it where a calculation uses it too.
  const rename = (from, to) => {
    const result = withMeasurements(renamed(measurements, from, to));
    if (result.calculations) {
      result.calculations = Object.fromEntries(
        Object.entries(result.calculations).map(([key, c]) => {
          if (!c || typeof c !== "object") return [key, c];
          const next = { ...c };
          if (Array.isArray(next.inputs)) next.inputs = next.inputs.map((i) => (i === from ? to : i));
          if (next.column === from) next.column = to;
          return [key, next];
        }),
      );
    }
    onChange(result);
  };
  const remove = (name) => {
    const next = { ...measurements };
    delete next[name];
    onChange(withMeasurements(next));
  };

  return html`
    <section class="setup-section" aria-labelledby="setup-measurements-title">
      <h2 id="setup-measurements-title">Measurements</h2>
      <p class="setup-intro">
        What is read every period, each into a column of the data file, in this order.
      </p>
      ${at(problems, "measurements").map((m) => html`<p class="form-error">${withCode(m)}</p>`)}
      <div class="setup-cards">
        ${names.length === 0 && html`<p class="setup-note">No measurements yet.</p>`}
        ${names.map(
          (name, index) => html`
            <${MeasurementCard}
              key=${name}
              name=${name}
              index=${index}
              count=${names.length}
              entry=${measurements[name] && typeof measurements[name] === "object" ? measurements[name] : {}}
              instruments=${instruments}
              drivers=${drivers}
              schema=${schema}
              taken=${taken}
              problems=${problems}
              onChange=${(entry) => onChange(withMeasurements({ ...measurements, [name]: entry }))}
              onRename=${(to) => rename(name, to)}
              onMove=${(step) => onChange(withMeasurements(swapped(measurements, index, index + step)))}
              onRemove=${() => remove(name)}
            />
          `,
        )}
      </div>
      <${AddMeasurement}
        instruments=${instruments}
        drivers=${drivers}
        taken=${taken}
        onAdd=${(name, entry) => onChange(withMeasurements({ ...measurements, [name]: entry }))}
      />
    </section>
  `;
}
