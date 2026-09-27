// A plot's matplotlib script, shown before it is saved: its text, coloured as
// Python, with Copy (to the clipboard) and Save… (as a file, as the other
// exports are). The script is written by the server (/experiment/plot_script).
import { useEffect, useLayoutEffect, useRef, useState } from "preact/hooks";
import { html } from "../html.js";

const KEYWORDS = new Set([
  "and", "as", "def", "elif", "else", "False", "for", "from", "if", "import", "in", "is",
  "None", "not", "or", "raise", "return", "True", "while", "with",
]);

// Python, piece by piece: each piece is [kind, text], the kind being a CSS
// class's ending (comment, string, keyword, number) or null for plain text.
// A string may run over several lines (the docstring).
const PIECE = new RegExp(
  [
    String.raw`(#[^\n]*)`, // a comment
    String.raw`([rRfFbBuU]{0,2}(?:"""[\s\S]*?(?:"""|$)|'''[\s\S]*?(?:'''|$)|"(?:[^"\\\n]|\\.)*"?|'(?:[^'\\\n]|\\.)*'?))`, // a string
    String.raw`(\b[A-Za-z_][A-Za-z0-9_]*\b)`, // a name, or a keyword
    String.raw`(\b\d[\d_]*(?:\.\d*)?(?:[eE][+-]?\d+)?\b)`, // a number
  ].join("|"),
  "g",
);

export function pythonPieces(text) {
  const pieces = [];
  let at = 0;
  for (const match of text.matchAll(PIECE)) {
    if (match.index > at) pieces.push([null, text.slice(at, match.index)]);
    const [whole, comment, string, name, number] = match;
    const kind = comment ? "comment" : string ? "string" : number ? "number" : KEYWORDS.has(name) ? "keyword" : null;
    pieces.push([kind, whole]);
    at = match.index + whole.length;
  }
  if (at < text.length) pieces.push([null, text.slice(at)]);
  return pieces;
}

const highlighted = (text) =>
  pythonPieces(text).map(([kind, piece]) =>
    kind ? html`<span class=${`code-${kind}`}>${piece}</span>` : piece,
  );

// `title` heads it, `name` is the file it is saved as, and `onSave` saves it
// (and closes the dialog).
export function ScriptDialog({ title, name, script, onSave, onClose }) {
  const [copied, setCopied] = useState(null); // true, or false if it couldn't be
  const copyButton = useRef(null);
  useLayoutEffect(() => {
    copyButton.current?.focus();
    const onKey = (event) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
  useEffect(() => {
    if (copied === null) return;
    const timer = setTimeout(() => setCopied(null), 2000);
    return () => clearTimeout(timer);
  }, [copied]);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(script);
      setCopied(true);
    } catch {
      setCopied(false); // not allowed here: it can still be selected and copied by hand
    }
  };
  return html`
    <div class="overlay" onPointerDown=${(e) => e.target === e.currentTarget && onClose()}>
      <div class="dialog script-dialog" role="dialog" aria-modal="true" aria-labelledby="script-title">
        <h2 id="script-title">${title}</h2>
        <p>
          Run it with Python (it needs pandas and matplotlib) to draw the plot from the data
          files. Saved, it is <strong>${name}</strong>.
        </p>
        <pre class="script-code" aria-label="Script" tabindex="0">${highlighted(script)}</pre>
        <div class="dialog-buttons">
          ${copied !== null &&
          html`<span class="script-copied ${copied ? "" : "failed"}" role="status">
            ${copied ? "Copied to the clipboard" : "Couldn't copy: select the text and press Ctrl+C"}
          </span>`}
          <button class="button" ref=${copyButton} onClick=${copy}>Copy</button>
          <button class="button" onClick=${onSave}>Save…</button>
          <button class="button button-primary" onClick=${onClose}>Close</button>
        </div>
      </div>
    </div>
  `;
}
