// The plot area: one or more panels in an automatic grid, a way to add more,
// an option to link their x axes, and a key to the current and previous data
// files (for every panel).
//
// A panel has a `kind`: "plot" (columns against another, panel.js; the kind of
// a saved panel that doesn't say) or "trace" (a trace against its axis,
// trace-panel.js). When the experiment has traces, **+ Add plot** offers either.
import { useEffect, useLayoutEffect, useRef, useState } from "preact/hooks";
import { html } from "../html.js";
import { usePopover, useStore } from "../hooks.js";
import { load, save } from "../session.js";
import { ChartIcon, EyeIcon, EyeOffIcon } from "../icons.js";
import { colourSlots, isTimeColumn } from "../colours.js";
import { MAX_SERIES, PlotPanel, defaultX, defaultY, resolve } from "./panel.js";
import { DEFAULT_OVERLAY, TracePanel, resolveTrace } from "./trace-panel.js";

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

const isTrace = (panel) => panel.kind === "trace";

// A panel made sound for the columns there are, whatever its kind.
export const resolvePanel = (panel, names) =>
  isTrace(panel) ? resolveTrace(panel) : resolve(panel, names);

// A new panel: against the same x as the first plot, plotting the first column
// no plot plots yet.
export function newPanel(panels, names, id) {
  const x = panels.find((p) => !isTrace(p))?.x ?? defaultX(names);
  const plotted = new Set(panels.flatMap((p) => (p.series ?? []).map((s) => s.name)));
  const name =
    names.find((n) => n !== x && !plotted.has(n) && !isTimeColumn(n)) ?? defaultY(names, x);
  return { id, x, series: [{ name }], logX: false, logY: false };
}

// A new trace panel, of the trace called `trace`.
export const newTracePanel = (trace, id) => ({
  id,
  kind: "trace",
  trace,
  overlay: DEFAULT_OVERLAY,
  logX: false,
  logY: false,
});

// **+ Add plot**: a plot of columns, or, when the experiment has traces, a
// menu of a plot or a trace panel of each trace.
function AddButton({ traces, full, onPlot, onTrace }) {
  const [open, setOpen] = useState(false);
  const menu = useRef(null);
  usePopover(menu, open, () => setOpen(false));
  const title = full ? "At most 6 plots" : "Add a plot";
  if (!traces?.length) {
    return html`
      <button class="bar-button" disabled=${full} title=${title} onClick=${onPlot}>+ Add plot</button>
    `;
  }
  const choose = (then) => () => {
    setOpen(false);
    then();
  };
  return html`
    <div class="axes-control add-control" ref=${menu}>
      <button
        class="bar-button"
        disabled=${full}
        title=${title}
        aria-expanded=${open}
        aria-haspopup="menu"
        onClick=${() => setOpen(!open)}
      >
        + Add plot
      </button>
      ${open &&
      html`
        <div class="axes-menu export-menu add-menu" role="menu" aria-label="Add a plot">
          <button class="export-item" role="menuitem" onClick=${choose(onPlot)}>
            Plot of columns
          </button>
          ${traces.map(
            (trace) => html`
              <button
                key=${trace.name}
                class="export-item"
                role="menuitem"
                onClick=${choose(() => onTrace(trace.name))}
              >
                Trace: ${trace.name}
              </button>
            `,
          )}
        </div>
      `}
    </div>
  `;
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

// `traces` are the experiment's (from /traces), or null until they are known.
export function PlotArea({ store, columns, theme, traces = null }) {
  useStore(store);
  const names = store.columns;
  const units = Object.fromEntries(
    (columns ?? []).filter((c) => c.unit).map((c) => [c.name, c.unit]),
  );
  const [state, setState] = useState(savedPlots);
  const [views, setViews] = useState({}); // zooms, by panel id; none: autoscaling
  useLayoutEffect(() => save("plots", state), [state]);
  const scales = useRef(new Map()); // each panel's scalesRef, by panel id
  const scalesOf = (id) => {
    if (!scales.current.has(id)) scales.current.set(id, { current: null });
    return scales.current.get(id);
  };
  const viewsNow = useRef(views);
  viewsNow.current = views;
  const stateNow = useRef(state);
  stateNow.current = state;

  // The palette's "Add a plot" and "Add a column to a plot": each answers
  // through `detail.done(problem)`, null when it was done.
  useEffect(() => {
    const addPlot = (event) => {
      const names = store.columns;
      const panels = stateNow.current.panels.map((p) => resolvePanel(p, names));
      if (panels.length >= MAX_PANELS) {
        return event.detail?.done?.(`There are ${MAX_PANELS} plots already, the most there can be.`);
      }
      const id = Math.max(0, ...panels.map((p) => p.id)) + 1;
      setState((s) => ({ ...s, panels: [...panels, newPanel(panels, names, id)] }));
      event.detail?.done?.(null);
    };
    const addSeries = (event) => {
      const { column, plot = 1, done } = event.detail ?? {};
      const names = store.columns;
      const panels = stateNow.current.panels.map((p) => resolvePanel(p, names));
      const panel = panels[plot - 1];
      if (!panel) {
        return done?.(`There is no plot ${plot}: there ${panels.length === 1 ? "is 1" : `are ${panels.length}`}.`);
      }
      if (isTrace(panel)) return done?.(`Plot ${plot} shows a trace, not columns.`);
      if (!names.includes(column)) return done?.(`There is no column called ${column}.`);
      if (panel.series.some((s) => s.name === column)) return done?.(`Plot ${plot} has ${column} already.`);
      if (panel.series.length >= MAX_SERIES) {
        return done?.(`Plot ${plot} has ${MAX_SERIES} columns already, the most it can have.`);
      }
      const series = [...panel.series.map(({ name, hidden }) => ({ name, hidden })), { name: column }];
      setState((s) => ({ ...s, panels: panels.map((p, i) => (i === plot - 1 ? { ...p, series } : p)) }));
      done?.(null);
    };
    window.addEventListener("pyacquisition:add-plot", addPlot);
    window.addEventListener("pyacquisition:add-series", addSeries);
    return () => {
      window.removeEventListener("pyacquisition:add-plot", addPlot);
      window.removeEventListener("pyacquisition:add-series", addSeries);
    };
  }, [store]);

  // The Space shortcut: every plot holds where it is, or, if any is held (by a
  // zoom, a pan or Space), they all follow the data again. Fixed limits stay.
  useEffect(() => {
    const toggle = () => {
      if (Object.values(viewsNow.current).some(Boolean)) {
        setViews({});
        return;
      }
      const held = {};
      for (const [id, ref] of scales.current) {
        const now = ref.current?.();
        if (now) held[id] = { x: now.x, y: now.y };
      }
      setViews(held);
    };
    window.addEventListener("pyacquisition:toggle-hold", toggle);
    return () => window.removeEventListener("pyacquisition:toggle-hold", toggle);
  }, []);

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

  const panels = state.panels.map((p) => resolvePanel(p, names));
  const slots = colourSlots(names); // each quantity's colour, as in the Values tab
  const update = (change) => setState((s) => ({ ...s, ...change }));
  const nextId = () => Math.max(0, ...panels.map((p) => p.id)) + 1;

  const add = () => update({ panels: [...panels, newPanel(panels, names, nextId())] });
  const addTrace = (trace) => update({ panels: [...panels, newTracePanel(trace, nextId())] });
  const duplicate = (id) => {
    const at = panels.findIndex((p) => p.id === id);
    const copy = { ...panels[at], id: nextId() };
    update({ panels: [...panels.slice(0, at + 1), copy, ...panels.slice(at + 1)] });
    setViews((v) => ({ ...v, [copy.id]: v[id] ?? null }));
  };
  const remove = (id) => {
    scales.current.delete(id);
    update({ panels: panels.filter((p) => p.id !== id) });
  };
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
      if (!source || isTrace(source)) return out;
      for (const p of panels) {
        if (p.id === id || isTrace(p) || p.x !== source.x || p.logX !== source.logX) continue;
        out[p.id] = next ? { x: next.x, y: null } : null;
      }
      return out;
    });

  const { columns: gridColumns, rows, lastSpan } = gridShape(panels.length);
  const showPrevious = state.showPrevious ?? true;

  return html`
    <main class="plot-area plot-area-panels">
      <div class="plot-area-bar">
        <${AddButton}
          traces=${traces}
          full=${panels.length >= MAX_PANELS}
          onPlot=${add}
          onTrace=${addTrace}
        />
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
              ${isTrace(panel)
                ? html`
                    <${TracePanel}
                      panel=${panel}
                      traces=${traces}
                      index=${index}
                      onChange=${(delta) => change(panel.id, delta)}
                      onDuplicate=${panels.length < MAX_PANELS ? () => duplicate(panel.id) : null}
                      onRemove=${panels.length > 1 ? () => remove(panel.id) : null}
                      theme=${theme}
                      view=${views[panel.id] ?? null}
                      onView=${(next) => setView(panel.id, next)}
                      scalesRef=${scalesOf(panel.id)}
                    />
                  `
                : html`
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
                      scalesRef=${scalesOf(panel.id)}
                    />
                  `}
            </div>
          `,
        )}
      </div>
    </main>
  `;
}
