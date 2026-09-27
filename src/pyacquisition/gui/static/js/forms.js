// Forms built from the API schema (/openapi.json): a field for each of an
// endpoint's query parameters, with its default, what it is for, and a list of
// choices where the schema gives them (an enum). Used to queue tasks, and made
// to serve the instruments' queries and commands too (milestone 14).
//
// Values are checked here before anything is sent, and what the server says is
// wrong (FastAPI's list of problems, see api.js) is shown by the field it names.
import { useState } from "preact/hooks";
import { html } from "./html.js";
import { get } from "./api.js";

export const loadSchema = () => get("/openapi.json", { timeout: 10000 });

// Text from a docstring, with its `code` shown as code rather than backticks.
export function withCode(text) {
  if (!text || !text.includes("`")) return text;
  return text
    .split(/`([^`]+)`/)
    .map((part, i) => (i % 2 ? html`<code>${part}</code>` : part));
}

// A schema with any reference to a shared one (`$ref`, as an instrument's enum
// is given) replaced by what it refers to.
function resolve(schema, root) {
  if (!schema?.$ref) return schema ?? {};
  const name = schema.$ref.split("/").at(-1);
  const { $ref, ...rest } = schema;
  return { ...(root.components?.schemas?.[name] ?? {}), ...rest };
}

// One field: {name, title, type, required, default, description, choices, labels}.
// `type` is integer, number, boolean, text or choice.
// A parameter's name as a title: "output_channel" as "Output Channel".
const titled = (name) => name.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

export function describeField(parameter, root) {
  let schema = resolve(parameter.schema, root);
  // A shared schema (an instrument's enum) is titled after its class
  // ("OutputChannel"), not the input, so the input's own name is used.
  if (parameter.schema?.$ref) schema = { ...schema, title: titled(parameter.name) };
  if (schema.anyOf) {
    // An optional input is "this or null".
    const kind = schema.anyOf.map((s) => resolve(s, root)).find((s) => s.type !== "null");
    const { anyOf, ...rest } = schema;
    schema = { ...kind, ...rest };
  }
  const choices = schema.enum ?? null;
  const TYPES = { integer: "integer", number: "number", boolean: "boolean", string: "text" };
  return {
    name: parameter.name,
    title: schema.title ?? parameter.name,
    type: choices ? "choice" : (TYPES[schema.type] ?? "text"),
    required: !!parameter.required,
    default: schema.default,
    description: parameter.description ?? schema.description ?? "",
    choices,
    labels: schema["x-labels"] ?? choices,
  };
}

// An endpoint: {path, name, description, fields}.
export function describeEndpoint(path, method, root) {
  return {
    path,
    name: method.summary ?? path.split("/").at(-1),
    description: method.description ?? "",
    fields: (method.parameters ?? [])
      .filter((p) => (p.in ?? "query") === "query")
      .map((p) => describeField(p, root)),
  };
}

// The endpoints that queue a task on a task manager, by name: the main one's
// are under /tasks/, and the others' under /managers/<name>/tasks/.
export function taskEndpoints(root, manager) {
  const prefix = manager === "main" ? "/tasks/" : `/managers/${manager}/tasks/`;
  return Object.entries(root.paths ?? {})
    .filter(([path, methods]) => path.startsWith(prefix) && methods.get?.tags?.includes("tasks"))
    .map(([path, methods]) => describeEndpoint(path, methods.get, root))
    .sort((a, b) => a.name.localeCompare(b.name));
}

// Each field's starting value, as the form holds it: text for the inputs, and
// true or false for a checkbox.
export function startingValues(fields) {
  return Object.fromEntries(
    fields.map((field) => {
      if (field.type === "boolean") return [field.name, field.default === true];
      const none = field.default === undefined || field.default === null;
      return [field.name, none ? "" : String(field.default)];
    }),
  );
}

export const WHOLE = /^[+-]?\d+$/;
export const NUMBER = /^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$/;

// The values checked, as {params} to send, or {errors} by field name. A field
// left empty that isn't required is left out, so the server uses its default.
export function checkValues(fields, values) {
  const params = {};
  const errors = {};
  for (const field of fields) {
    const value = values[field.name];
    if (field.type === "boolean") {
      params[field.name] = value ? "true" : "false";
      continue;
    }
    const text = String(value ?? "").trim();
    if (text === "") {
      if (field.required) errors[field.name] = "Required.";
      continue;
    }
    if (field.type === "integer" && !WHOLE.test(text)) {
      errors[field.name] = "A whole number, such as 3.";
    } else if (field.type === "number" && !NUMBER.test(text)) {
      errors[field.name] = "A number, such as 1.5 or 2e-3.";
    } else if (field.type === "choice" && !field.choices.map(String).includes(text)) {
      errors[field.name] = "Pick one of the choices.";
    } else {
      // Text is sent as typed (spaces and all); numbers without their spaces.
      params[field.name] = field.type === "text" ? String(value) : text;
    }
  }
  return Object.keys(errors).length ? { errors } : { params };
}

// One field. The setup page's options use it too: a `placeholder` there is the
// default that an empty field leaves in place.
export function Field({ field, value, error, onChange, id }) {
  const help = field.description ? `${id}-help` : undefined;
  const problem = error ? `${id}-error` : undefined;
  const describedBy = [help, problem].filter(Boolean).join(" ") || undefined;

  if (field.type === "boolean") {
    return html`
      <div class="form-field form-field-check" data-field=${field.name}>
        <label class="check">
          <input
            type="checkbox"
            id=${id}
            checked=${value}
            aria-describedby=${describedBy}
            onChange=${(e) => onChange(e.currentTarget.checked)}
          />
          ${field.title}
        </label>
        ${field.description && html`<p class="form-help" id=${help}>${withCode(field.description)}</p>`}
        ${error && html`<p class="form-error" id=${problem}>${withCode(error)}</p>`}
      </div>
    `;
  }

  const input =
    field.type === "choice"
      ? html`
          <select
            class="text-input"
            id=${id}
            value=${value}
            aria-invalid=${!!error}
            aria-describedby=${describedBy}
            onChange=${(e) => onChange(e.currentTarget.value)}
          >
            ${value === "" &&
            html`<option value="">
              ${field.required ? "Choose…" : field.placeholder ? `Default (${field.placeholder})` : "Default"}
            </option>`}
            ${field.choices.map(
              (choice, i) => html`<option value=${String(choice)}>${field.labels[i]}</option>`,
            )}
          </select>
        `
      : html`
          <input
            class="text-input ${field.type === "text" ? "" : "number-input"}"
            id=${id}
            value=${value}
            placeholder=${field.placeholder}
            inputmode=${field.type === "integer" ? "numeric" : field.type === "number" ? "decimal" : undefined}
            aria-invalid=${!!error}
            aria-describedby=${describedBy}
            onInput=${(e) => onChange(e.currentTarget.value)}
          />
        `;
  return html`
    <div class="form-field" data-field=${field.name}>
      <label for=${id}>
        ${field.title}${field.required && html`<span class="form-required" aria-hidden="true"> *</span>`}
      </label>
      ${input}
      ${field.description && html`<p class="form-help" id=${help}>${withCode(field.description)}</p>`}
      ${error && html`<p class="form-error" id=${problem}>${withCode(error)}</p>`}
    </div>
  `;
}

// A form for an endpoint. `onSubmit(params)` sends it; if it throws, what the
// server said is shown, each problem by the field it names where it names one.
// Give it a `key` of the endpoint's path, so another endpoint starts afresh.
// `initialValues` start it with other values than the defaults (the palette's
// typed arguments), and `lineErrors` are shown by their fields until each is
// changed: give it a key that changes with them.
//
// `secondary` adds a second button, {label, onSubmit(params, choice), choices},
// checked as the first is; Shift+Enter in a field presses it. With more than one
// of `choices` (the task managers, for queueing an instrument's call), a list
// beside it picks one, the first to start with.
export function EndpointForm({
  endpoint,
  onSubmit,
  submitLabel,
  initialValues,
  lineErrors,
  secondary,
}) {
  const [choice, setChoice] = useState(() => secondary?.choices?.[0]);
  const [values, setValues] = useState(() => ({
    ...startingValues(endpoint.fields),
    ...(initialValues ?? {}),
  }));
  const [errors, setErrors] = useState({});
  const [edited, setEdited] = useState(() => new Set());
  const [problem, setProblem] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (event) => {
    event.preventDefault();
    const second = !!secondary && event.submitter?.dataset.secondary === "true";
    setProblem("");
    const checked = checkValues(endpoint.fields, values);
    if (checked.errors) return setErrors(checked.errors);
    setErrors({});
    setBusy(true);
    try {
      if (second) await secondary.onSubmit(checked.params, choice);
      else await onSubmit(checked.params);
    } catch (e) {
      const byField = {};
      const general = [];
      for (const p of e.problems ?? []) {
        if (p.name && endpoint.fields.some((f) => f.name === p.name)) byField[p.name] = p.message;
        else general.push(p.message);
      }
      setErrors(byField);
      setProblem(e.problems ? general.join(" ") : e.message);
    } finally {
      setBusy(false);
    }
  };

  const id = (name) => `field-${endpoint.path.replaceAll("/", "-")}-${name}`;
  return html`
    <form
      class="endpoint-form"
      onSubmit=${submit}
      onKeyDown=${(event) => {
        if (secondary && event.key === "Enter" && event.shiftKey && event.target.tagName === "INPUT") {
          event.preventDefault();
          event.currentTarget.requestSubmit(event.currentTarget.querySelector("[data-secondary]"));
        }
      }}
      noValidate
    >
      ${endpoint.fields.length === 0 &&
      html`<p class="form-help">This takes no inputs.</p>`}
      ${endpoint.fields.map(
        (field) => html`
          <${Field}
            key=${field.name}
            id=${id(field.name)}
            field=${field}
            value=${values[field.name]}
            error=${errors[field.name] ?? (edited.has(field.name) ? undefined : lineErrors?.[field.name])}
            onChange=${(value) => {
              setValues((current) => ({ ...current, [field.name]: value }));
              setErrors((current) => ({ ...current, [field.name]: undefined }));
              setEdited((current) => new Set(current).add(field.name));
            }}
          />
        `,
      )}
      ${problem && html`<p class="form-error form-problem" role="alert">${problem}</p>`}
      <div class="form-buttons">
        <button type="submit" class="button button-primary" disabled=${busy}>
          ${busy ? "Sending…" : submitLabel}
        </button>
        ${secondary &&
        html`
          <button type="submit" class="button" data-secondary="true" disabled=${busy}>
            ${secondary.label}
          </button>
          ${secondary.choices?.length > 1 &&
          html`
            <select
              class="text-input form-choice"
              aria-label=${secondary.choiceLabel ?? "Queue on"}
              value=${choice}
              onChange=${(e) => setChoice(e.currentTarget.value)}
            >
              ${secondary.choices.map(
                (c) => html`<option value=${c}>${c.charAt(0).toUpperCase() + c.slice(1)}</option>`,
              )}
            </select>
          `}
        `}
      </div>
    </form>
  `;
}
