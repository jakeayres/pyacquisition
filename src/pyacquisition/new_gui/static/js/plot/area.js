// The plot area: one or more plot panels in an automatic grid, a way to add
// more, an option to link their x axes, and a key to the current and previous
// data files (for every panel).
import { useLayoutEffect, useState } from "preact/hooks";
import { html } from "../html.js";
import { useStore } from "../hooks.js";
import { load, save } from "../session.js";
import { ChartIcon, EyeIcon, EyeOffIcon } from "../icons.js";
import { colourSlots, isTimeColumn } from "../colours.js";
import { PlotPanel, defaultX, defaultY, resolve } from "./panel.js";

export const MAX_PANELS = 6;

// The grid for some panels: as square as it can be, filled row by row, with
// the last panel stretched across what is left of its row.
export function gridShape(count) {
  const columns = Math.ceil(Math.sqrt(count));
  const rows = Math.ceil(count / columns);
  return { columns, rows, lastSpan: columns * rows - count + 1 };
}

// What was chosen this session, from an older single plot too.
function savedPlots() {
  const saved = load("plots", null);
  if (saved?.panels?.length) return saved;
  const old = load("plot", {});
  const series = old.series ?? (old.y ? [{ name: old.y }] : undefined);
  return {
    panels: [{ id: 1, x: old.x, series, logX: old.logX, logY: old.logY }],
    link: false,
    showPrevious: old.showPrevious ?? true,
  };
}

// A new panel: against the same x as the first, plotting the first column no
// panel plots yet.
export function newPanel(panels, names, id) {
  const x = panels[0]?.x ?? defaultX(names);
  const plotted = new Set(panels.flatMap((p) => p.series.map((s) => s.name)));
  const name =
    names.find((n) => n !== x && !plotted.has(n) && !isTimeColumn(n)) ?? defaultY(names, x);
  return { id, x, series: [{ name }], logX: false, logY: false };
}

function FileKey({ store, showPrevious, onTogglePrevious }) {
  const previous = store.previous;
  return html`
    <div class="file-keys">
      <span class="file-key" title="The current data file">
        <span class="key-line key-line-file"></span>
        <span class="file-key-name">${store.current.file ?? "Current file"}</span>
      </span>
      ${previous &&
      html`
        <button
          class="file-key file-key-previous ${showPrevious ? "" : "hidden"}"
          aria-pressed=${showPrevious}
          title=${showPrevious ? "Hide the previous file" : "Show the previous file"}
          onClick=${onTogglePrevious}
        >
          <span class="key-line key-line-file key-line-previous"></span>
          <span class="file-key-name">Previous: ${previous.file}</span>
          ${showPrevious ? html`<${EyeIcon} />` : html`<${EyeOffIcon} />`}
        </button>
      `}
    </div>
  `;
}

export function PlotArea({ store, columns, theme }) {
  useStore(store);
  const names = store.columns;
  const units = Object.fromEntries(
    (columns ?? []).filter((c) => c.unit).map((c) => [c.name, c.unit]),
  );
  const [state, setState] = useState(savedPlots);
  const [views, setViews] = useState({}); // zooms, by panel id; none: autoscaling
  useLayoutEffect(() => save("plots", state), [state]);

  if (names.length === 0) {
    return html`
      <main class="plot-area">
        <div class="empty-state">
          <${ChartIcon} />
          <h2>Waiting for data</h2>
          <p>The plot starts with the first measurement.</p>
        </div>
      </main>
    `;
  }

  const panels = state.panels.map((p) => resolve(p, names));
  const slots = colourSlots(names); // each quantity's colour, as in the Values tab
  const update = (change) => setState((s) => ({ ...s, ...change }));
  const nextId = () => Math.max(0, ...panels.map((p) => p.id)) + 1;

  const add = () => update({ panels: [...panels, newPanel(panels, names, nextId())] });
  const duplicate = (id) => {
    const at = panels.findIndex((p) => p.id === id);
    const copy = { ...panels[at], id: nextId() };
    update({ panels: [...panels.slice(0, at + 1), copy, ...panels.slice(at + 1)] });
    setViews((v) => ({ ...v, [copy.id]: v[id] ?? null }));
  };
  const remove = (id) => update({ panels: panels.filter((p) => p.id !== id) });
  const change = (id, delta) =>
    update({ panels: panels.map((p) => (p.id === id ? { ...p, ...delta } : p)) });

  // With the x axes linked, a panel's x range goes to every panel plotting
  // against the same x (each fitting its own y to it), and autoscaling goes
  // to them all.
  const setView = (id, next) =>
    setViews((current) => {
      const out = { ...current, [id]: next };
      if (!state.link) return out;
      const source = panels.find((p) => p.id === id);
      for (const p of panels) {
        if (p.id === id || p.x !== source.x || p.logX !== source.logX) continue;
        out[p.id] = next ? { x: next.x, y: null } : null;
      }
      return out;
    });

  const { columns: gridColumns, rows, lastSpan } = gridShape(panels.length);
  const showPrevious = state.showPrevious ?? true;

  return html`
    <main class="plot-area plot-area-panels">
      <div class="plot-area-bar">
        <button
          class="bar-button"
          disabled=${panels.length >= MAX_PANELS}
          title=${panels.length >= MAX_PANELS ? `At most ${MAX_PANELS} plots` : "Add a plot"}
          onClick=${add}
        >
          + Add plot
        </button>
        ${panels.length > 1 &&
        html`
          <button
            class="toggle"
            aria-pressed=${!!state.link}
            title="Zoom and pan the x axes of plots against the same column together"
            onClick=${() => update({ link: !state.link })}
          >
            Link x-axes
          </button>
        `}
        <${FileKey}
          store=${store}
          showPrevious=${showPrevious}
          onTogglePrevious=${() => update({ showPrevious: !showPrevious })}
        />
      </div>
      <div
        class="plot-grid"
        style=${{
          gridTemplateColumns: `repeat(${gridColumns}, minmax(0, 1fr))`,
          gridTemplateRows: `repeat(${rows}, minmax(0, 1fr))`,
        }}
      >
        ${panels.map(
          (panel, index) => html`
            <div
              key=${panel.id}
              class="plot-cell"
              style=${index === panels.length - 1 ? { gridColumn: `span ${lastSpan}` } : {}}
            >
              <${PlotPanel}
                store=${store}
                names=${names}
                units=${units}
                slots=${slots}
                panel=${panel}
                index=${index}
                onChange=${(delta) => change(panel.id, delta)}
                onDuplicate=${panels.length < MAX_PANELS ? () => duplicate(panel.id) : null}
                onRemove=${panels.length > 1 ? () => remove(panel.id) : null}
                showPrevious=${showPrevious}
                theme=${theme}
                view=${views[panel.id] ?? null}
                onView=${(next) => setView(panel.id, next)}
              />
            </div>
          `,
        )}
      </div>
    </main>
  `;
}
