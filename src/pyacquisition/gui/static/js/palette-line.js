// The palette's search line: where the search ends and the arguments begin,
// and the arguments matched to an item's inputs, so `wait 0 5` or
// `ramp temp 300 5 output_1` fills the form as it is typed. Pure functions, with
// no page to draw, so the browser tests call them directly.
//
// The search is the longest run of leading words that still matches an item. It
// stops at the first number, quoted text or name=value, and everything from
// there on is an argument. After Tab (a `locked` item), everything after the
// item's label is.
import { NUMBER, WHOLE, checkValues, startingValues } from "./forms.js";

export const words = (query) => query.toLowerCase().split(/\s+/).filter(Boolean);
const hasAll = (text, query) => words(query).every((w) => text.toLowerCase().includes(w));

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

// The line's tokens, split on spaces: [{text, quoted, name, value}]. Quotes (" or ')
// hold spaces, and are dropped. A token with an `=` before any quote, after a
// name, is a named one: `seconds=30`, `file_name="cold run"`.
export function tokens(line) {
  const found = [];
  let i = 0;
  while (i < line.length) {
    if (/\s/.test(line[i])) {
      i += 1;
      continue;
    }
    let text = "";
    let quoted = false;
    let equals = -1;
    while (i < line.length && !/\s/.test(line[i])) {
      const c = line[i];
      if (c === '"' || c === "'") {
        const end = line.indexOf(c, i + 1);
        text += line.slice(i + 1, end === -1 ? line.length : end);
        quoted = true;
        i = end === -1 ? line.length : end + 1;
        continue;
      }
      if (c === "=" && equals === -1 && !quoted) equals = text.length;
      text += c;
      i += 1;
    }
    const name = equals > 0 ? text.slice(0, equals) : null;
    const named = name !== null && /^[A-Za-z_][A-Za-z0-9_]*$/.test(name);
    found.push({
      text,
      quoted,
      name: named ? name : null,
      value: named ? text.slice(equals + 1) : null,
    });
  }
  return found;
}

// Whether a token can only be an argument: a number, quoted text, or name=value.
const isArgument = (token) => token.quoted || token.name !== null || NUMBER.test(token.text);

// An item's text in lower case, with its camel case split ("WaitFor" as
// "wait for"), for finding where its words start.
const spaced = (item) =>
  `${item.label} ${item.text}`.replace(/([a-z])([A-Z])/g, "$1 $2").toLowerCase();
const escaped = (text) => text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

// Whether some item has each of `wanted` at the start of one of its words. The
// line's search only takes a word that does, so a timer called `lap` is an
// argument even where an item's description says "elapsed".
function someStartWith(items, wanted) {
  const patterns = wanted.map((w) => new RegExp(`(^|[^a-z0-9])${escaped(w.toLowerCase())}`));
  return items.some((item) => {
    const text = spaced(item);
    return patterns.every((p) => p.test(text));
  });
}

// The line as {search, arguments, locked}: the words to search with, and the
// argument tokens. `locked` is the item Tab locked in, if any: while the line
// still starts with its label and a space, every token after that is an
// argument, and `locked` in the answer is true.
export function splitLine(line, items, locked = null) {
  if (locked) {
    const head = `${locked.label} `;
    if (line.toLowerCase().startsWith(head.toLowerCase())) {
      return { search: locked.label, arguments: tokens(line.slice(head.length)), locked: true };
    }
  }
  const all = tokens(line);
  const first = all.findIndex(isArgument);
  const leading = all.slice(0, first === -1 ? all.length : first);
  // The longest run of leading words that still matches an item, each at the
  // start of one of its words; if even the first matches nothing, they are all
  // the search (and the list says nothing matches).
  const texts = leading.map((t) => t.text);
  let take = leading.length;
  while (take > 1 && !someStartWith(items, texts.slice(0, take))) take -= 1;
  if (take === 1 && !someStartWith(items, texts.slice(0, 1))) take = leading.length;
  return {
    search: leading.slice(0, take).map((t) => t.text).join(" "),
    arguments: all.slice(take),
    locked: false,
  };
}

const BOOLEANS = { true: true, yes: true, on: true, 1: true, false: false, no: false, off: false, 0: false };

// What an input takes, in words: for the hint's and the form's messages.
function takes(field) {
  switch (field.type) {
    case "boolean":
      return "yes or no";
    case "integer":
      return "a whole number";
    case "number":
      return "a number";
    case "choice":
      return `one of ${field.labels.map(String).join(", ")}`;
    default:
      return "text";
  }
}

// `text` as the form holds it for `field`: {value}, or {refused} saying what
// the field takes instead. Booleans as true or false (yes, no, on, off, 1, 0);
// choices by their value or their label, ignoring case.
export function typedValue(field, text) {
  const t = String(text).trim();
  const lower = t.toLowerCase();
  const refused = { refused: takes(field) };
  switch (field.type) {
    case "boolean":
      return lower in BOOLEANS ? { value: BOOLEANS[lower] } : refused;
    case "choice": {
      // As the server does: spaces, underscores and case don't matter, so
      // `output_1` is the choice labelled "Output 1".
      const loose = (x) => String(x).toLowerCase().replace(/[\s_]+/g, "");
      let i = field.choices.findIndex((c) => loose(c) === loose(t));
      if (i === -1) i = (field.labels ?? []).findIndex((l) => loose(l) === loose(t));
      return i === -1 ? refused : { value: String(field.choices[i]) };
    }
    case "integer":
      return WHOLE.test(t) ? { value: t } : refused;
    case "number":
      return NUMBER.test(t) ? { value: t } : refused;
    default:
      return { value: String(text) };
  }
}

const code = (text) => `\`${text}\``;
const listed = (names) =>
  names.length > 1 ? `${names.slice(0, -1).join(", ")} and ${names.at(-1)}` : names.join("");

// The argument tokens matched to `fields`:
// - `values`: the form's values, as `startingValues` gives them, with the
//   arguments in;
// - `given`: [[name, text]] for each input an argument filled, in the order
//   typed;
// - `errors`: a problem by input's name, the parser's own and `checkValues`';
// - `problems`: those that belong to no input (an unknown name);
// - `ok`: whether it can be sent as it is.
//
// A choice with exactly one choice is filled first, then each name=value, then
// each positional token goes to the next input not yet filled that can take it.
// A word that no input left can take joins the text input just before it, so
// `cold run` fills one text input with both words.
export function matchArguments(fields, argumentTokens) {
  const values = startingValues(fields);
  const filled = new Set();
  const given = [];
  const errors = {};
  const problems = [];
  const put = (field, value, text) => {
    values[field.name] = value;
    filled.add(field.name);
    given.push([field.name, text]);
  };

  for (const field of fields) {
    if (field.type === "choice" && field.choices.length === 1) {
      values[field.name] = String(field.choices[0]);
      filled.add(field.name);
    }
  }

  for (const token of argumentTokens.filter((t) => t.name !== null)) {
    const field = fields.find((f) => f.name.toLowerCase() === token.name.toLowerCase());
    if (!field) {
      const names = fields.map((f) => code(f.name));
      problems.push(
        names.length
          ? `No input called ${code(token.name)}. Its inputs are ${listed(names)}.`
          : `No input called ${code(token.name)}: this takes none.`,
      );
      continue;
    }
    if (given.some(([name]) => name === field.name)) {
      errors[field.name] = `${code(field.name)} is given twice.`;
      continue;
    }
    const typed = typedValue(field, token.value);
    if (typed.refused) {
      errors[field.name] = `${code(token.value)} isn't ${typed.refused}.`;
      if (field.type !== "boolean") values[field.name] = token.value;
      filled.add(field.name);
      given.push([field.name, token.value]);
    } else {
      put(field, typed.value, token.value);
    }
  }

  let last = null; // the input the last positional token went to
  for (const token of argumentTokens.filter((t) => t.name === null)) {
    const open = fields.filter((f) => !filled.has(f.name));
    const field = open.find((f) => !typedValue(f, token.text).refused);
    if (field) {
      put(field, typedValue(field, token.text).value, token.text);
      last = field;
    } else if (last?.type === "text") {
      values[last.name] = `${values[last.name]} ${token.text}`;
      const entry = given.find(([name]) => name === last.name);
      entry[1] = values[last.name];
    } else if (open.length) {
      const wants = open.map((f) => `${code(f.name)} takes ${takes(f)}`);
      errors[open[0].name] ??= `Nothing left here takes ${code(token.text)}: ${listed(wants)}.`;
    } else {
      const at = fields.at(-1);
      if (at) errors[at.name] ??= `${code(token.text)} has nowhere to go: every input is filled.`;
      else problems.push(`${code(token.text)} has nowhere to go: this takes no inputs.`);
    }
  }

  const checked = checkValues(fields, values);
  for (const [name, message] of Object.entries(checked.errors ?? {})) errors[name] ??= message;
  return {
    values,
    given,
    errors,
    problems,
    ok: Object.keys(errors).length === 0 && problems.length === 0,
  };
}
