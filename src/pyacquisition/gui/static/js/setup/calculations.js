// The Calculations section: the built-in calculations a config can hold, each a
// new column made from the columns above it, in order after the measurements.
// What each kind takes comes from /setup/describe (`config_keys` in
// core/calculations.py): one column, a list of columns, or a whole number.
import { useState } from "preact/hooks";
import { html } from "../html.js";
import { Field, withCode } from "../forms.js";
import { ChevronDownIcon, ChevronUpIcon, PlusIcon } from "../icons.js";
import { columnNames } from "./measurements.js";

const WHOLE = /^\d+$/;

// What each kind of key is for, shown under its field.
const HELP = {
  inputs: "The columns added together.",
  column: "The column averaged.",
  window: "How many of its last values are averaged.",
};

const renamed = (object, from, to) =>
  Object.fromEntries(Object.entries(object).map(([k, v]) => [k === from ? to : k, v]));
function swapped(object, i, j) {
  const entries = Object.entries(object);
  [entries[i], entries[j]] = [entries[j], entries[i]];
  return Object.fromEntries(entries);
}

const at = (problems, ...where) =>
  problems
    .filter((p) => p.where.length === where.length && where.every((w, i) => p.where[i] === w))
    .map((p) => p.message);

// The columns a calculation can use: the measurements', and those of the
// calculations above it.
function columnsAbove(config, name) {
  const calculations = Object.keys(config.calculations ?? {});
  return [...Object.keys(config.measurements ?? {}), ...calculations.slice(0, calculations.indexOf(name))];
}

function Columns({ id, title, above, chosen, error, onChange }) {
  const toggle = (column, on) => {
    const next = on ? [...chosen, column] : chosen.filter((c) => c !== column);
    // Kept in the order of the columns, whatever order they were ticked in.
    onChange(above.filter((c) => next.includes(c)).concat(next.filter((c) => !above.includes(c))));
  };
  return html`
    <fieldset class="form-field setup-columns" data-field=${title} id=${id}>
      <legend>${title}<span class="form-required" aria-hidden="true"> *</span></legend>
      ${above.length === 0 && html`<p class="form-help">There are no columns above it yet.</p>`}
      <div class="setup-columns-list">
        ${above.map(
          (column) => html`
            <label class="check" key=${column}>
              <input type="checkbox" checked=${chosen.includes(column)} onChange=${(e) => toggle(column, e.currentTarget.checked)} />
              ${column}
            </label>
          `,
        )}
      </div>
      <p class="form-help">${HELP[title] ?? ""}</p>
      ${error && html`<p class="form-error">${withCode(error)}</p>`}
    </fieldset>
  `;
}

function CalculationCard({ name, index, count, first, entry, kinds, config, taken, problems, onChange, onRename, onMove, onRemove }) {
  const [draftName, setDraftName] = useState(name);
  const [nameProblem, setNameProblem] = useState("");
  const kind = kinds.find((k) => k.name === entry.calculation);
  const above = columnsAbove(config, name);
  const id = (key) => `calculation-${name}-${key}`;
  const error = (...where) => at(problems, "calculations", name, ...where).join(" ");

  const set = (key, value) => {
    const next = { ...entry };
    if (value === undefined) delete next[key];
    else next[key] = value;
    onChange(next);
  };
  const rename = () => {
    const to = draftName.trim();
    if (to === name) return setNameProblem("");
    if (!to) return setNameProblem("It needs a name.");
    if (taken.includes(to)) return setNameProblem(`There is already a column called ${to}.`);
    setNameProblem("");
    onRename(to);
  };
  const kindNames = kinds.map((k) => k.name);

  return html`
    <article class="setup-card" aria-label=${`Calculation ${name}`}>
      <header class="setup-card-header">
        <div class="setup-card-title">
          <input
            class="text-input setup-card-name"
            id=${id("name")}
            aria-label="Name"
            title="The new column's name in the data file"
            value=${draftName}
            aria-invalid=${!!nameProblem}
            onInput=${(e) => setDraftName(e.currentTarget.value)}
            onChange=${rename}
            onKeyDown=${(e) => e.key === "Enter" && e.currentTarget.blur()}
          />
          <span class="setup-card-kind">column ${first + index + 1}</span>
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
      ${at(problems, "calculations", name).map((m) => html`<p class="form-error">${withCode(m)}</p>`)}
      <div class="setup-card-fields">
        <${Field}
          id=${id("calculation")}
          field=${{ name: "calculation", title: "calculation", type: "choice", required: true,
            choices: kindNames, labels: kindNames }}
          value=${entry.calculation ?? ""}
          error=${error("calculation")}
          onChange=${(value) => onChange(entry.unit === undefined ? { calculation: value } : { calculation: value, unit: entry.unit })}
        />
        ${Object.entries(kind?.keys ?? {}).map(([key, valueKind]) => {
          if (valueKind === "columns") {
            return html`<${Columns}
              key=${key}
              id=${id(key)}
              title=${key}
              above=${above}
              chosen=${Array.isArray(entry[key]) ? entry[key] : []}
              error=${error(key)}
              onChange=${(chosen) => set(key, chosen.length ? chosen : undefined)}
            />`;
          }
          if (valueKind === "column") {
            const choices = above.includes(entry[key]) || entry[key] === undefined ? above : [...above, entry[key]];
            return html`<${Field}
              key=${key}
              id=${id(key)}
              field=${{ name: key, title: key, type: "choice", required: true, choices, labels: choices, description: HELP[key] }}
              value=${entry[key] ?? ""}
              error=${error(key)}
              onChange=${(value) => set(key, value || undefined)}
            />`;
          }
          return html`<${Field}
            key=${key}
            id=${id(key)}
            field=${{ name: key, title: key, type: "integer", required: true, description: HELP[key] }}
            value=${entry[key] === undefined ? "" : String(entry[key])}
            error=${error(key)}
            onChange=${(value) => set(key, value.trim() === "" ? undefined : WHOLE.test(value.trim()) ? Number(value.trim()) : value)}
          />`;
        })}
        <${Field}
          id=${id("unit")}
          field=${{ name: "unit", title: "unit", type: "text",
            description: "Shown beside its value, and on plot axes. It doesn't change the data." }}
          value=${entry.unit ?? ""}
          error=${error("unit")}
          onChange=${(value) => set("unit", value === "" ? undefined : value)}
        />
      </div>
    </article>
  `;
}

function AddCalculation({ kinds, taken, onAdd }) {
  const [open, setOpen] = useState(false);
  const [kind, setKind] = useState("");
  const [name, setName] = useState("");
  const [problem, setProblem] = useState("");

  const add = (event) => {
    event.preventDefault();
    if (!kind) return setProblem("Pick a calculation.");
    const chosen = name.trim();
    if (!chosen) return setProblem("It needs a name: the new column's.");
    if (taken.includes(chosen)) return setProblem(`There is already a column called ${chosen}.`);
    onAdd(chosen, { calculation: kind });
    setOpen(false);
    setKind("");
    setName("");
    setProblem("");
  };

  if (!open) {
    return html`
      <button class="button button-small" onClick=${() => setOpen(true)}>
        <${PlusIcon} /> Add calculation
      </button>
    `;
  }
  return html`
    <form class="setup-add" onSubmit=${add} aria-label="Add calculation" noValidate>
      <div class="form-field">
        <label for="add-calculation-kind">Calculation</label>
        <select class="text-input" id="add-calculation-kind" value=${kind}
          onChange=${(e) => { setKind(e.currentTarget.value); setProblem(""); }}>
          <option value="">Choose…</option>
          ${kinds.map((k) => html`<option value=${k.name}>${k.name}</option>`)}
        </select>
      </div>
      <div class="form-field">
        <label for="add-calculation-name">Name</label>
        <input class="text-input" id="add-calculation-name" value=${name}
          placeholder="The new column's name" onInput=${(e) => setName(e.currentTarget.value)} />
      </div>
      ${problem && html`<p class="form-error" role="alert">${problem}</p>`}
      <div class="form-buttons">
        <button type="button" class="button button-small" onClick=${() => setOpen(false)}>Cancel</button>
        <button type="submit" class="button button-small button-primary">Add</button>
      </div>
    </form>
  `;
}

export function CalculationsSection({ described, config, problems, onChange }) {
  const calculations = config.calculations ?? {};
  const names = Object.keys(calculations);
  const first = Object.keys(config.measurements ?? {}).length;
  const taken = columnNames(config);

  const withCalculations = (next) => {
    const result = { ...config };
    if (Object.keys(next).length) result.calculations = next;
    else delete result.calculations;
    return result;
  };
  // Renaming one renames it where the calculations below it use it too.
  const rename = (from, to) => {
    const next = Object.fromEntries(
      Object.entries(renamed(calculations, from, to)).map(([key, c]) => {
        if (!c || typeof c !== "object") return [key, c];
        const changed = { ...c };
        if (Array.isArray(changed.inputs)) changed.inputs = changed.inputs.map((i) => (i === from ? to : i));
        if (changed.column === from) changed.column = to;
        return [key, changed];
      }),
    );
    onChange(withCalculations(next));
  };
  const remove = (name) => {
    const next = { ...calculations };
    delete next[name];
    onChange(withCalculations(next));
  };

  return html`
    <section class="setup-section" aria-labelledby="setup-calculations-title">
      <h2 id="setup-calculations-title">Calculations</h2>
      <p class="setup-intro">
        New columns made from the ones above them, after the measurements, in this order.
        For anything else, such as <code>x / 1e-6</code>, write it in Python.
      </p>
      ${at(problems, "calculations").map((m) => html`<p class="form-error">${withCode(m)}</p>`)}
      <div class="setup-cards">
        ${names.length === 0 && html`<p class="setup-note">No calculations yet.</p>`}
        ${names.map(
          (name, index) => html`
            <${CalculationCard}
              key=${name}
              name=${name}
              index=${index}
              count=${names.length}
              first=${first}
              entry=${calculations[name] && typeof calculations[name] === "object" ? calculations[name] : {}}
              kinds=${described.calculations}
              config=${config}
              taken=${taken}
              problems=${problems}
              onChange=${(entry) => onChange(withCalculations({ ...calculations, [name]: entry }))}
              onRename=${(to) => rename(name, to)}
              onMove=${(step) => onChange(withCalculations(swapped(calculations, index, index + step)))}
              onRemove=${() => remove(name)}
            />
          `,
        )}
      </div>
      <${AddCalculation}
        kinds=${described.calculations}
        taken=${taken}
        onAdd=${(name, entry) => onChange(withCalculations({ ...calculations, [name]: entry }))}
      />
    </section>
  `;
}
