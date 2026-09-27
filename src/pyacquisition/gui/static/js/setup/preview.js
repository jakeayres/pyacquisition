// The file as saving would write it, with the config's problems above it. Each
// problem is shown by its field too, where it has one on the page.
import { html } from "../html.js";
import { withCode } from "../forms.js";
import { highlighted } from "./toml.js";

// Where a problem is, as it reads in TOML: [rack] period.
function place(where) {
  if (!where.length) return "The file";
  const [section, ...rest] = where;
  return rest.length ? `[${section}] ${rest.join(".")}` : `[${section}]`;
}

export function Preview({ checked, stale }) {
  const problems = checked?.problems ?? [];
  return html`
    <aside class="setup-preview" aria-label="The file">
      <div class="setup-problems" role="status" aria-live="polite">
        ${checked === null
          ? html`<p class="setup-note">Checking…</p>`
          : problems.length === 0
            ? html`<p class="setup-ok">No problems${stale ? "…" : "."}</p>`
            : html`
                <h2 class="setup-problems-title">
                  ${problems.length} ${problems.length === 1 ? "problem" : "problems"}
                </h2>
                <ul aria-label="Problems">
                  ${problems.map(
                    (p) => html`<li><strong>${place(p.where)}</strong> ${withCode(p.message)}</li>`,
                  )}
                </ul>
              `}
      </div>
      <pre class="setup-toml" aria-label="TOML">${highlighted(checked?.toml ?? "")}</pre>
    </aside>
  `;
}
