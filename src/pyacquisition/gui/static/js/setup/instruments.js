// The Instruments section: each instrument in the config, with its driver and,
// for hardware, its adapter, address and the three common options, and a Test
// that asks it for *IDN?. Other `args` in the file are kept, and shown.
import { useState } from "preact/hooks";
import { html } from "../html.js";
import { Field, withCode } from "../forms.js";
import { PlusIcon } from "../icons.js";
import * as api from "./api.js";

const WHOLE = /^\d+$/;
// The options that have fields; any other `args` are kept as they are.
const COMMON = ["timeout", "read_termination", "write_termination"];

// A line ending as it is typed: "\n" is the two characters, not a new line.
const shown = (text) => text.replaceAll("\r", "\\r").replaceAll("\n", "\\n");
const typed = (text) => text.replaceAll("\\r", "\r").replaceAll("\\n", "\n");

// An object with one key renamed, in its place.
function renamed(object, from, to) {
  return Object.fromEntries(Object.entries(object).map(([k, v]) => [k === from ? to : k, v]));
}

// A name for a new instrument of a driver that no instrument has yet.
function freeName(driver, taken) {
  const base = driver.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "");
  if (!taken.includes(base)) return base;
  let n = 2;
  while (taken.includes(`${base}_${n}`)) n += 1;
  return `${base}_${n}`;
}

function problemsAt(problems, ...where) {
  return problems
    .filter((p) => where.every((w, i) => p.where[i] === w) && p.where.length === where.length)
    .map((p) => p.message);
}

function TestResult({ result, driver }) {
  if (!result) return null;
  if (result.busy) return html`<p class="setup-test" role="status">Asking it for *IDN?…</p>`;
  if (result.error) {
    return html`<p class="setup-test setup-test-bad" role="status">${result.error}</p>`;
  }
  const reply = html`<code>${result.reply}</code>`;
  if (result.matches === true) {
    return html`<p class="setup-test setup-test-good" role="status">It answered ${reply}, which is a ${driver}.</p>`;
  }
  if (result.matches === false) {
    return html`
      <p class="setup-test setup-test-warn" role="status">
        It answered ${reply}, which isn't a ${driver}: a ${driver}'s answer has ${result.missing.map(
          (w, i) => html`${i ? ", " : ""}<code>${w}</code>`,
        )}.
      </p>
    `;
  }
  return html`
    <p class="setup-test" role="status">
      It answered ${reply}. There's nothing known of a ${driver}'s answer to compare it with.
    </p>
  `;
}

function InstrumentCard({ name, entry, driver, adapters, names, problems, onChange, onRename, onRemove }) {
  const [draftName, setDraftName] = useState(name);
  const [nameProblem, setNameProblem] = useState("");
  const [result, setResult] = useState(null);
  const args = entry.args ?? {};
  const others = Object.entries(args).filter(([key]) => !COMMON.includes(key));
  const id = (key) => `instrument-${name}-${key}`;
  const hardware = driver?.hardware ?? true;

  const set = (key, value) => {
    const next = { ...entry };
    if (value === undefined) delete next[key];
    else next[key] = value;
    onChange(next);
  };
  const setArg = (key, value) => {
    const nextArgs = { ...args };
    if (value === undefined) delete nextArgs[key];
    else nextArgs[key] = value;
    set("args", Object.keys(nextArgs).length ? nextArgs : undefined);
  };

  const rename = () => {
    const to = draftName.trim();
    if (to === name) return setNameProblem("");
    if (!to) return setNameProblem("It needs a name.");
    if (names.includes(to)) return setNameProblem(`There is already an instrument called ${to}.`);
    setNameProblem("");
    onRename(to);
  };

  const test = async () => {
    setResult({ busy: true });
    try {
      setResult(await api.test({ instrument: entry.instrument, adapter: entry.adapter, resource: entry.resource, args }));
    } catch (e) {
      setResult({ error: e.message });
    }
  };

  const errorAt = (...where) => problemsAt(problems, "instruments", name, ...where).join(" ");
  const own = problemsAt(problems, "instruments", name);
  return html`
    <article class="setup-card" aria-label=${`Instrument ${name}`}>
      <header class="setup-card-header">
        <div class="setup-card-title">
          <input
            class="text-input setup-card-name"
            id=${id("name")}
            aria-label="Name"
            title="Its name in the experiment, and in the API"
            value=${draftName}
            aria-invalid=${!!nameProblem}
            onInput=${(e) => setDraftName(e.currentTarget.value)}
            onChange=${rename}
            onKeyDown=${(e) => e.key === "Enter" && e.currentTarget.blur()}
          />
          <span class="setup-card-kind">
            ${entry.instrument ?? "no driver"}${driver ? (hardware ? " · hardware" : " · software") : ""}
          </span>
        </div>
        <button class="button button-small button-danger-quiet" onClick=${onRemove}>Remove</button>
      </header>
      ${nameProblem && html`<p class="form-error" role="alert">${nameProblem}</p>`}
      ${[...own, ...problemsAt(problems, "instruments", name, "instrument")].map(
        (message) => html`<p class="form-error">${withCode(message)}</p>`,
      )}
      ${hardware &&
      html`
        <div class="setup-card-fields">
          <${Field}
            id=${id("adapter")}
            field=${{ name: "adapter", title: "adapter", type: "choice", choices: adapters, labels: adapters, required: true,
              description: "How it is reached: pyvisa for VISA, prologix for a Prologix GPIB-USB controller, mock with no device." }}
            value=${entry.adapter ?? ""}
            error=${errorAt("adapter")}
            onChange=${(value) => set("adapter", value || undefined)}
          />
          <${Field}
            id=${id("resource")}
            field=${{ name: "resource", title: "resource", type: "text", required: true,
              description: "Its address, such as GPIB0::7::INSTR, or COM3::7 through a Prologix controller." }}
            value=${entry.resource ?? ""}
            error=${errorAt("resource")}
            onChange=${(value) => set("resource", value || undefined)}
          />
          <${Field}
            id=${id("timeout")}
            field=${{ name: "timeout", title: "timeout", type: "integer", placeholder: "default: 5000",
              description: "How long to wait for it to answer, in milliseconds." }}
            value=${args.timeout === undefined ? "" : String(args.timeout)}
            error=${errorAt("args", "timeout")}
            onChange=${(value) => setArg("timeout", value.trim() === "" ? undefined : WHOLE.test(value.trim()) ? Number(value.trim()) : value)}
          />
          ${["read_termination", "write_termination"].map(
            (key) => html`
              <${Field}
                key=${key}
                id=${id(key)}
                field=${{ name: key, title: key, type: "text",
                  description: key === "read_termination"
                    ? "What ends its answers, such as \\n. Empty for the adapter's own."
                    : "What ends what is sent to it, such as \\n. Empty for the adapter's own." }}
                value=${args[key] === undefined ? "" : shown(String(args[key]))}
                error=${errorAt("args", key)}
                onChange=${(value) => setArg(key, value === "" ? undefined : typed(value))}
              />
            `,
          )}
        </div>
        ${others.length > 0 &&
        html`
          <div class="setup-others">
            <p class="form-help">Also given, kept as the file has them:</p>
            <ul aria-label="Other args">
              ${others.map(([key, value]) => html`<li><code>${key} = ${JSON.stringify(value)}</code></li>`)}
            </ul>
          </div>
        `}
        <div class="setup-card-test">
          <button class="button button-small" onClick=${test} disabled=${result?.busy}>Test</button>
          <${TestResult} result=${result} driver=${entry.instrument} />
        </div>
      `}
    </article>
  `;
}

// The drivers, filtered as their name is typed, in a list tall enough to see
// several at once (the browser's own list for an input showed three).
function DriverPicker({ drivers, value, onChange }) {
  const [active, setActive] = useState(0);
  const typed = value.trim().toLowerCase();
  const shown = drivers.filter((d) => d.name.toLowerCase().includes(typed));
  const pick = (name) => {
    onChange(name);
    setActive(0);
  };
  const onKeyDown = (event) => {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActive((i) => Math.min(i + 1, shown.length - 1));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActive((i) => Math.max(i - 1, 0));
    } else if (event.key === "Enter" && shown[active] && shown[active].name !== value) {
      event.preventDefault(); // picks it, rather than adding
      pick(shown[active].name);
    }
  };
  return html`
    <div class="form-field setup-picker">
      <label for="add-instrument-driver">Driver</label>
      <input
        class="text-input"
        id="add-instrument-driver"
        role="combobox"
        aria-expanded="true"
        aria-controls="add-instrument-drivers"
        aria-autocomplete="list"
        value=${value}
        autofocus
        placeholder="Type to search"
        onInput=${(e) => {
          onChange(e.currentTarget.value);
          setActive(0);
        }}
        onKeyDown=${onKeyDown}
      />
      <ul class="setup-picker-list" id="add-instrument-drivers" role="listbox" aria-label="Choices">
        ${shown.length === 0 && html`<li class="setup-picker-none">No driver matches.</li>`}
        ${shown.map(
          (d, i) => html`
            <li
              key=${d.name}
              role="option"
              aria-selected=${d.name === value}
              class=${i === active ? "setup-picker-active" : ""}
              onPointerDown=${(e) => {
                e.preventDefault(); // keeps the focus in the box
                pick(d.name);
              }}
            >
              <span class="setup-picker-name">${d.name}</span>
              <span class="setup-picker-kind">${d.hardware ? "hardware" : "software"}</span>
            </li>
          `,
        )}
      </ul>
    </div>
  `;
}

function AddInstrument({ drivers, names, onAdd }) {
  const [open, setOpen] = useState(false);
  const [driver, setDriver] = useState("");
  const [name, setName] = useState("");
  const [problem, setProblem] = useState("");
  const known = drivers.map((d) => d.name);

  const add = (event) => {
    event.preventDefault();
    if (!known.includes(driver)) return setProblem("Pick a driver from the list.");
    const chosen = name.trim() || freeName(driver, names);
    if (names.includes(chosen)) return setProblem(`There is already an instrument called ${chosen}.`);
    const hardware = drivers.find((d) => d.name === driver).hardware;
    onAdd(chosen, hardware ? { instrument: driver, adapter: "pyvisa", resource: "" } : { instrument: driver });
    setOpen(false);
    setDriver("");
    setName("");
    setProblem("");
  };

  if (!open) {
    return html`
      <button class="button button-small" onClick=${() => setOpen(true)}>
        <${PlusIcon} /> Add instrument
      </button>
    `;
  }
  return html`
    <form class="setup-add" onSubmit=${add} aria-label="Add instrument" noValidate>
      <${DriverPicker}
        drivers=${drivers}
        value=${driver}
        onChange=${(value) => {
          setDriver(value);
          setProblem("");
        }}
      />
      <div class="form-field">
        <label for="add-instrument-name">Name</label>
        <input
          class="text-input"
          id="add-instrument-name"
          value=${name}
          placeholder=${known.includes(driver) ? freeName(driver, names) : "Its name in the experiment"}
          onInput=${(e) => setName(e.currentTarget.value)}
        />
      </div>
      ${problem && html`<p class="form-error" role="alert">${problem}</p>`}
      <div class="form-buttons">
        <button type="button" class="button button-small" onClick=${() => setOpen(false)}>Cancel</button>
        <button type="submit" class="button button-small button-primary">Add</button>
      </div>
    </form>
  `;
}

export function InstrumentsSection({ described, config, problems, onChange }) {
  const instruments = config.instruments ?? {};
  const names = Object.keys(instruments);
  const drivers = Object.fromEntries(described.drivers.map((d) => [d.name, d]));

  const withInstruments = (next) => {
    const result = { ...config };
    if (Object.keys(next).length) result.instruments = next;
    else delete result.instruments;
    return result;
  };

  // Renaming an instrument renames it in the measurements that use it too.
  const rename = (from, to) => {
    const result = withInstruments(renamed(instruments, from, to));
    if (result.measurements) {
      result.measurements = Object.fromEntries(
        Object.entries(result.measurements).map(([key, m]) => [
          key,
          m && m.instrument === from ? { ...m, instrument: to } : m,
        ]),
      );
    }
    onChange(result);
  };
  const remove = (name) => {
    const next = { ...instruments };
    delete next[name];
    onChange(withInstruments(next));
  };

  return html`
    <section class="setup-section" aria-labelledby="setup-instruments-title">
      <h2 id="setup-instruments-title">Instruments</h2>
      <p class="setup-intro">
        The instruments the experiment talks to. Test asks one for <code>*IDN?</code> at its
        address, and says whether it is the instrument its driver is for.
      </p>
      ${problemsAt(problems, "instruments").map((m) => html`<p class="form-error">${withCode(m)}</p>`)}
      <div class="setup-cards">
        ${names.length === 0 && html`<p class="setup-note">No instruments yet.</p>`}
        ${names.map(
          (name) => html`
            <${InstrumentCard}
              key=${name}
              name=${name}
              entry=${instruments[name] ?? {}}
              driver=${drivers[instruments[name]?.instrument]}
              adapters=${described.adapters}
              names=${names}
              problems=${problems}
              onChange=${(entry) => onChange(withInstruments({ ...instruments, [name]: entry }))}
              onRename=${(to) => rename(name, to)}
              onRemove=${() => remove(name)}
            />
          `,
        )}
      </div>
      <${AddInstrument}
        drivers=${described.drivers}
        names=${names}
        onAdd=${(name, entry) => onChange(withInstruments({ ...instruments, [name]: entry }))}
      />
    </section>
  `;
}
