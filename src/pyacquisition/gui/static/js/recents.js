// What was run from the palette lately, newest first, so an empty palette offers
// it again: {id, label, values, queued, at}. `values` are the form's, as
// `startingValues` gives them (text, and true or false for a checkbox), and
// `queued` says it was queued (Shift+Enter, Add to queue) rather than run.
//
// Kept with the session's state (session.js) under "recents", which the saved
// layout sends to the experiment (layout.js), so they come back next run.
import { load, save } from "./session.js";
import { startingValues } from "./forms.js";

export const KEPT = 20; // recents kept
export const SHOWN = 8; // shown above the rest in an empty palette

export function recents() {
  const list = load("recents", []);
  return Array.isArray(list) ? list.filter((r) => r && typeof r.id === "string") : [];
}

// The form's values for the params a run sent (as checkValues gives them):
// each input left out has its starting value.
export function valuesOf(fields, params) {
  const values = startingValues(fields);
  for (const field of fields) {
    if (!(field.name in params)) continue;
    const sent = params[field.name];
    values[field.name] = field.type === "boolean" ? sent === true || sent === "true" : String(sent);
  }
  return values;
}

// Puts a run first, drops an older one of the same item with the same values
// (run the same way), and keeps KEPT. Returns the list.
export function recordRun(item, values, queued = false) {
  const same = (r) =>
    r.id === item.id && !!r.queued === queued && JSON.stringify(r.values) === JSON.stringify(values);
  const entry = { id: item.id, label: item.label, values, queued, at: Date.now() };
  const list = [entry, ...recents().filter((r) => !same(r))].slice(0, KEPT);
  save("recents", list);
  return list;
}

// A recent's inputs, to show beside its label: "hours=0, minutes=5".
export function inputsText(fields, values) {
  return fields
    .filter((f) => (f.type === "boolean" ? values[f.name] === true : `${values[f.name] ?? ""}` !== ""))
    .map((f) => (f.type === "boolean" ? f.name : `${f.name}=${values[f.name]}`))
    .join(", ");
}
