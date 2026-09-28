// The Options section: a field for each of an experiment's options, grouped by
// the TOML section it sits in, from /setup/describe (core/settings.py). An
// option is only in the config, and so the file, once it is set: an empty field
// leaves the default, which it shows.
import { html } from "../html.js";
import { Field } from "../forms.js";

const WHOLE = /^[+-]?\d+$/;
const NUMBER = /^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$/;
const FLAGS = ["true", "false"];
const FLAG_LABELS = ["Yes", "No"];

// The form field for an option, from the kind of value it takes.
function field(option) {
  const base = {
    name: option.name,
    title: option.key,
    description: option.help,
    placeholder: text(option, option.default) ? `default: ${text(option, option.default)}` : undefined,
  };
  switch (option.kind) {
    case "port":
    case "count":
      return { ...base, type: "integer" };
    case "seconds":
    case "megabytes":
      return { ...base, type: "number" };
    case "level":
      return {
        ...base,
        type: "choice",
        choices: option.choices,
        labels: option.choices,
        placeholder: text(option, option.default), // shown as "Default (…)"
      };
    case "flag":
    case "gui":
      return {
        ...base,
        type: "choice",
        choices: FLAGS,
        labels: FLAG_LABELS,
        placeholder: FLAG_LABELS[FLAGS.indexOf(String(option.default))],
      };
    default: // path, text, ports
      return { ...base, type: "text" };
  }
}

// The text a field shows for a value in the config ("" for none).
export function text(option, value) {
  if (value === undefined || value === null) return "";
  if (option.kind === "ports") return Array.isArray(value) ? value.join(", ") : String(value);
  return String(value);
}

// The value a field's text puts in the config. Text that isn't what the option
// takes is kept as it is, so the check says what is wrong with it, by its field.
export function value(option, typed) {
  const t = typed.trim();
  switch (option.kind) {
    case "port":
    case "count":
      return WHOLE.test(t) ? Number(t) : typed;
    case "seconds":
    case "megabytes":
      return NUMBER.test(t) ? Number(t) : typed;
    case "ports": {
      const parts = t.split(/[\s,]+/).filter(Boolean);
      return parts.every((p) => WHOLE.test(p)) ? parts.map(Number) : typed;
    }
    case "flag":
    case "gui":
      return t === "true" ? true : t === "false" ? false : typed;
    default:
      return typed;
  }
}

// The config with an option set to what a field holds, or taken out if it is
// empty (and its section, if that leaves it empty).
export function setOption(config, option, typed) {
  const next = { ...config };
  const section = { ...(next[option.section] ?? {}) };
  if (typed.trim() === "") delete section[option.key];
  else section[option.key] = value(option, typed);
  if (Object.keys(section).length === 0) delete next[option.section];
  else next[option.section] = section;
  return next;
}

export function fieldId(option) {
  return `option-${option.section}-${option.key}`;
}

export function OptionsSection({ options, config, problems, onChange }) {
  const sections = [...new Set(options.map((o) => o.section))];
  const problemFor = (option) =>
    problems
      .filter((p) => p.where[0] === option.section && p.where[1] === option.key)
      .map((p) => p.message)
      .join(" ");
  return html`
    <section class="setup-section" aria-labelledby="setup-options-title">
      <h2 id="setup-options-title">Options</h2>
      <p class="setup-intro">
        Leave a field empty to keep its default. Only the options you set are written to the file.
      </p>
      ${sections.map(
        (section) => html`
          <fieldset class="setup-group" key=${section}>
            <legend><code>[${section}]</code></legend>
            ${options
              .filter((o) => o.section === section)
              .map(
                (option) => html`
                  <${Field}
                    key=${option.name}
                    id=${fieldId(option)}
                    field=${field(option)}
                    value=${text(option, config[option.section]?.[option.key])}
                    error=${problemFor(option)}
                    onChange=${(typed) => onChange(setOption(config, option, typed))}
                  />
                `,
              )}
          </fieldset>
        `,
      )}
    </section>
  `;
}
