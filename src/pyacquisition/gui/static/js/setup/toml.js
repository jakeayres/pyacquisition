// TOML with its parts marked for colouring: comments, table headers, keys,
// strings, numbers and true/false. A line at a time, which is all the setup page's
// files need (it writes no multi-line strings). The text itself is unchanged.
import { html } from "../html.js";

const PATTERNS = [
  ["comment", /^#.*/],
  // A key is a bare or quoted name followed by `=`.
  ["key", /^(?:[A-Za-z0-9_.-]+|"(?:[^"\\]|\\.)*")(?=\s*=)/],
  ["string", /^"(?:[^"\\]|\\.)*"?/],
  ["string", /^'[^']*'?/],
  ["bool", /^(?:true|false)\b/],
  ["number", /^[+-]?(?:inf|nan|0x[0-9a-fA-F_]+|\d[\d_]*(?:\.\d[\d_]*)?(?:[eE][+-]?\d+)?)\b/],
];

// A line in pieces: [kind or null, text].
function tokens(line) {
  const header = line.match(/^(\s*)(\[\[?[^\]#]*\]\]?)(.*)$/);
  if (header) {
    return [[null, header[1]], ["header", header[2]], ...tokens(header[3])];
  }
  const found = [];
  let rest = line;
  while (rest) {
    const space = rest.match(/^\s+/);
    if (space) {
      found.push([null, space[0]]);
      rest = rest.slice(space[0].length);
      continue;
    }
    const match = PATTERNS.map(([kind, re]) => [kind, rest.match(re)]).find(([, m]) => m);
    const [kind, text] = match ? [match[0], match[1][0]] : [null, rest[0]];
    found.push([kind, text]);
    rest = rest.slice(text.length);
  }
  return found;
}

// The TOML as elements, each part in a `toml-<kind>` span.
export function highlighted(text) {
  return text.split(/(\r?\n)/).map((part) =>
    /\r?\n/.test(part)
      ? part
      : tokens(part).map(([kind, piece]) =>
          kind ? html`<span class=${`toml-${kind}`}>${piece}</span>` : piece,
        ),
  );
}
