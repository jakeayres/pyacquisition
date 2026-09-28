// One plot panel: what to plot (one or more columns, which are also its legend),
// what against, how to draw it, log axes, fixed limits, and the plot, with a
// way back to autoscaling once it is zoomed. The plot area (area.js) arranges
// the panels.
import { useRef, useState } from "preact/hooks";
import { html } from "../html.js";
import { usePopover } from "../hooks.js";
import { AxesIcon, CopyIcon, CloseIcon, DownloadIcon, MarksIcon } from "../icons.js";
import { plotScript } from "../api.js";
import { exportName, plotImage, saveFile, scriptSettings, viewCsv } from "./export.js";
import { ScriptDialog } from "./script-dialog.js";
import { colourVar, isTimeColumn } from "../colours.js";
import { Plot } from "./plot.js";

// The most columns on one plot: as many as there are colours.
export const MAX_SERIES = 8;

// The x column to start with: time, if there is one, or else the first.
export function defaultX(columns) {
  return columns.includes("time") ? "time" : columns[0];
}

// The y column to start with: the first that is not the x column, nor a time.
export function defaultY(columns, x) {
  return (
    columns.find((name) => name !== x && !isTimeColumn(name)) ??
    columns.find((name) => name !== x) ??
    columns[0]
  );
}

// What a panel plots, made sound for the columns there are: a saved choice
// holds only while its columns exist. (A column's colour is not saved: it is
// the quantity's, from colours.js.)
export function resolve(panel, names) {
  const x = names.includes(panel.x) ? panel.x : defaultX(names);
  let series = (panel.series ?? [])
    .filter((s) => names.includes(s.name))
    .map(({ name, hidden }) => ({ name, hidden }));
  if (series.length === 0) series = [{ name: defaultY(names, x) }];
  return { ...panel, x, series, logX: panel.logX ?? false, logY: panel.logY ?? false };
}

const withUnit = (name, units) => (units[name] ? `${name} (${units[name]})` : name);

function XPicker({ value, columns, units, onChange }) {
  return html`
    <label class="picker">
      <span class="picker-label">against</span>
      <select value=${value} onChange=${(event) => onChange(event.target.value)}>
        ${columns.map(
          (name) => html`<option key=${name} value=${name}>${withUnit(name, units)}</option>`,
        )}
      </select>
    </label>
  `;
}

// The plotted columns, as the legend: each shows its quantity's colour, and
// clicking it hides or shows it; its × takes it off the plot.
function SeriesKey({ series, columns, units, onToggle, onRemove, onAdd }) {
  const plotted = new Set(series.map((s) => s.name));
  const addable = columns.filter((name) => !plotted.has(name));
  const full = series.length >= MAX_SERIES;
  return html`
    <div class="series-key" role="group" aria-label="Plotted columns">
      <span class="picker-label">Plot</span>
      ${series.map(
        (s) => html`
          <span key=${s.name} class="series-chip ${s.hidden ? "hidden" : ""}">
            <button
              class="series-toggle"
              aria-pressed=${!s.hidden}
              title=${s.hidden ? `Show ${s.name}` : `Hide ${s.name}`}
              onClick=${() => onToggle(s.name)}
            >
              <span class="key-line" style=${{ background: colourVar(s.slot) }}></span>
              <span class="series-name">${withUnit(s.name, units)}</span>
            </button>
            ${series.length > 1 &&
            html`
              <button
                class="series-remove"
                aria-label=${`Remove ${s.name}`}
                title=${`Remove ${s.name}`}
                onClick=${() => onRemove(s.name)}
              >
                ×
              </button>
            `}
          </span>
        `,
      )}
      ${addable.length > 0 &&
      html`
        <select
          class="series-add"
          aria-label="Add a column to the plot"
          value=""
          disabled=${full}
          title=${full ? `At most ${MAX_SERIES} columns on one plot` : "Add a column to the plot"}
          onChange=${(event) => {
            onAdd(event.target.value);
            event.target.value = "";
          }}
        >
          <option value="" disabled>+ Add</option>
          ${addable.map(
            (name) => html`<option key=${name} value=${name}>${withUnit(name, units)}</option>`,
          )}
        </select>
      `}
    </div>
  `;
}

export const MARKS = [
  ["lines", "Lines"],
  ["points", "Points"],
  ["both", "Both"],
];

// A small picture of each way of drawing, beside its name in the menu.
const MarksGlyph = ({ marks }) => html`
  <svg class="marks-glyph" viewBox="0 0 28 12" aria-hidden="true">
    ${marks !== "points" &&
    html`<path d="M2 9l8-5 8 4 8-6" fill="none" stroke="currentColor" stroke-width="1.5" />`}
    ${marks !== "lines" &&
    html`
      <circle cx="10" cy="4" r="1.8" fill="currentColor" />
      <circle cx="18" cy="8" r="1.8" fill="currentColor" />
      <circle cx="26" cy="2.5" r="1.8" fill="currentColor" />
    `}
  </svg>
`;

// How the data is drawn: lines, points, or both. Opens from an icon in the
// toolbar; choosing one closes it.
function MarksMenu({ value, onChange }) {
  const [open, setOpen] = useState(false);
  const menu = useRef(null);
  usePopover(menu, open, () => setOpen(false));
  const changed = value !== "lines"; // from the default
  const label = MARKS.find(([marks]) => marks === value)?.[1] ?? value;
  return html`
    <div class="axes-control" ref=${menu}>
      <button
        class="icon-button axes-button"
        aria-label="Line and point style"
        aria-pressed=${changed}
        aria-expanded=${open}
        title=${`Line and point style: ${label.toLowerCase()}`}
        onClick=${() => setOpen(!open)}
      >
        <${MarksIcon} />
        ${changed && html`<span class="axes-badge" aria-hidden="true"></span>`}
      </button>
      ${open &&
      html`
        <div class="axes-menu export-menu" role="menu" aria-label="Line and point style">
          <span class="menu-heading">Draw as</span>
          ${MARKS.map(
            ([marks, name]) => html`
              <button
                key=${marks}
                class="export-item marks-item"
                role="menuitemradio"
                aria-checked=${value === marks}
                onClick=${() => {
                  onChange(marks);
                  setOpen(false);
                }}
              >
                <${MarksGlyph} marks=${marks} />
                ${name}
              </button>
            `,
          )}
        </div>
      `}
    </div>
  `;
}

const tidy = (v) => String(Number(v.toPrecision(6)));

// The axes that are not scaling to the data: those held by a zoom or pan (a
// linked panel's view holds only x, and y still fits what is in it), or fixed
// in the axes menu.
export function manualAxes(view, limits) {
  const axes = [];
  if (view?.x || limits?.x) axes.push("x");
  if (view?.y || limits?.y) axes.push("y");
  return axes;
}

// The fixed limits typed into the axis settings, checked against whether each
// axis is to be logarithmic: {x, y}, each {min, max} or null for automatic, or
// an error to show.
export function checkLimits(draft) {
  const out = {};
  for (const axis of ["x", "y"]) {
    const field = draft[axis];
    const log = !!field.log;
    if (field.auto) {
      out[axis] = null;
      continue;
    }
    const min = Number(field.min);
    const max = Number(field.max);
    const name = axis.toUpperCase();
    if (field.min.trim() === "" || field.max.trim() === "" || !isFinite(min) || !isFinite(max)) {
      return { error: `${name}: give a number for both the minimum and the maximum.` };
    }
    if (!(min < max)) return { error: `${name}: the minimum must be below the maximum.` };
    if (log && !(min > 0)) return { error: `${name}: a log axis needs a minimum above zero.` };
    out[axis] = { min, max };
  }
  return { limits: out };
}

// What an axis-settings button says about the settings, for its tooltip.
export function axisSummary(limits, logX, logY) {
  const parts = [];
  if (limits?.x) parts.push("x fixed");
  if (limits?.y) parts.push("y fixed");
  if (logX) parts.push("log x");
  if (logY) parts.push("log y");
  return parts.length ? `Axis settings: ${parts.join(", ")}` : "Axis settings";
}

// The axis settings: for each axis, its limits (fixed, or scaling to the data)
// and whether it is logarithmic. Opens from an icon in the toolbar, starting
// from the settings, and for an automatic axis from what it shows now. Nothing
// changes until Apply.
export function AxesMenu({ limits, logX, logY, scalesRef, onApply }) {
  const [draft, setDraft] = useState(null); // open while there is one
  const [error, setError] = useState("");
  const menu = useRef(null);
  const changed = !!(limits?.x || limits?.y || logX || logY); // from the defaults

  const open = () => {
    const now = scalesRef.current?.();
    const field = (limit, shown, log) =>
      limit
        ? { auto: false, min: String(limit.min), max: String(limit.max), log }
        : {
            auto: true,
            min: shown ? tidy(shown.min) : "",
            max: shown ? tidy(shown.max) : "",
            log,
          };
    setDraft({ x: field(limits?.x, now?.x, logX), y: field(limits?.y, now?.y, logY) });
    setError("");
  };
  const close = () => setDraft(null);
  usePopover(menu, !!draft, close);

  const edit = (axis, change) => setDraft((d) => ({ ...d, [axis]: { ...d[axis], ...change } }));
  const apply = () => {
    const checked = checkLimits(draft);
    if (checked.error) return setError(checked.error);
    onApply({ limits: checked.limits, logX: draft.x.log, logY: draft.y.log });
    close();
  };
  const autoscaleBoth = () => {
    onApply({ limits: { x: null, y: null }, logX: draft.x.log, logY: draft.y.log });
    close();
  };
  const useCurrent = () => {
    const now = scalesRef.current?.();
    if (!now) return;
    for (const axis of ["x", "y"]) {
      edit(axis, { auto: false, min: tidy(now[axis].min), max: tidy(now[axis].max) });
    }
  };

  const row = (axis) => html`
    <div class="axes-row">
      <span class="axes-name">${axis.toUpperCase()}</span>
      <label class="axes-auto">
        <input
          type="checkbox"
          checked=${draft[axis].auto}
          onChange=${(e) => edit(axis, { auto: e.target.checked })}
        />
        Auto
      </label>
      <input
        class="axes-input"
        aria-label=${`${axis.toUpperCase()} minimum`}
        inputmode="decimal"
        value=${draft[axis].min}
        disabled=${draft[axis].auto}
        onInput=${(e) => edit(axis, { min: e.target.value })}
        onKeyDown=${(e) => e.key === "Enter" && apply()}
      />
      <span class="axes-to">to</span>
      <input
        class="axes-input"
        aria-label=${`${axis.toUpperCase()} maximum`}
        inputmode="decimal"
        value=${draft[axis].max}
        disabled=${draft[axis].auto}
        onInput=${(e) => edit(axis, { max: e.target.value })}
        onKeyDown=${(e) => e.key === "Enter" && apply()}
      />
      <label class="axes-log">
        <input
          type="checkbox"
          aria-label=${`Log ${axis}`}
          checked=${draft[axis].log}
          onChange=${(e) => edit(axis, { log: e.target.checked })}
        />
        Log
      </label>
    </div>
  `;

  const summary = axisSummary(limits, logX, logY);
  return html`
    <div class="axes-control" ref=${menu}>
      <button
        class="icon-button axes-button"
        aria-label="Axis settings"
        aria-pressed=${changed}
        aria-expanded=${!!draft}
        title=${summary}
        onClick=${() => (draft ? close() : open())}
      >
        <${AxesIcon} />
        ${changed && html`<span class="axes-badge" aria-hidden="true"></span>`}
      </button>
      ${draft &&
      html`
        <div class="axes-menu" role="dialog" aria-label="Axis settings">
          ${row("x")} ${row("y")}
          ${error && html`<p class="axes-error" role="alert">${error}</p>`}
          <div class="axes-buttons">
            <button class="button" onClick=${useCurrent}>Use current view</button>
            <button class="button" onClick=${autoscaleBoth}>Autoscale both</button>
            <button class="button button-primary" onClick=${apply}>Apply</button>
          </div>
        </div>
      `}
    </div>
  `;
}

// Exporting the plot: as an image of it, the data in view as CSV (export.js), or
// a Python script that draws it with matplotlib (written by the server), as it
// looks or as a figure for a paper, shown first in a dialog (script-dialog.js)
// to copy or save. A message says where it went, for a few seconds.
function ExportMenu({ store, plotRef, scalesRef, what }) {
  const [open, setOpen] = useState(false);
  const [message, setMessage] = useState(null); // {text, failed}
  const [shown, setShown] = useState(null); // a script in its dialog: {title, name, script}
  const menu = useRef(null);
  const timer = useRef(null);
  usePopover(menu, open, () => setOpen(false));

  const tell = (text, failed = false) => {
    clearTimeout(timer.current);
    setMessage({ text, failed });
    timer.current = setTimeout(() => setMessage(null), 5000);
  };

  const save = async (name, content) => {
    const where = await saveFile(name, content);
    if (where) tell(`Saved ${where}`);
  };

  // The image and the data are saved straight away. A script is shown first,
  // to copy or save.
  const run = async (kind) => {
    setOpen(false);
    try {
      const u = plotRef.current;
      if (!u) throw new Error("there is no plot yet");
      if (kind === "png" || kind === "csv") {
        const content =
          kind === "png"
            ? await plotImage(u, what)
            : viewCsv(store, { ...what, range: scalesRef.current().x });
        await save(exportName(store, what, kind), content);
        return;
      }
      const held = manualAxes(what.view, what.limits).length > 0;
      const style = kind === "aps" ? "aps" : "screen";
      const script = await plotScript(scriptSettings(what, scalesRef.current(), held, style));
      // The figure's script is named apart from the plain one of the same plot.
      const name =
        kind === "aps"
          ? exportName(store, what, "py").replace(/\.py$/, " - figure.py")
          : exportName(store, what, "py");
      const title = kind === "aps" ? "Publication figure (APS style)" : "Python script (matplotlib)";
      setShown({ title, name, script });
    } catch (error) {
      tell(`Couldn't export: ${error.message ?? error}`, true);
    }
  };

  const saveShown = async () => {
    const { name, script } = shown;
    setShown(null);
    try {
      await save(name, script);
    } catch (error) {
      tell(`Couldn't export: ${error.message ?? error}`, true);
    }
  };

  return html`
    <div class="axes-control export-control" ref=${menu}>
      <button
        class="icon-button"
        aria-label="Export"
        aria-expanded=${open}
        title="Export this plot"
        onClick=${() => setOpen(!open)}
      >
        <${DownloadIcon} />
      </button>
      ${open &&
      html`
        <div class="axes-menu export-menu" role="menu" aria-label="Export">
          <button class="export-item" role="menuitem" onClick=${() => run("png")}>
            Image of the plot (PNG)
          </button>
          <button class="export-item" role="menuitem" onClick=${() => run("csv")}>
            Data in view (CSV)
          </button>
          <button class="export-item" role="menuitem" onClick=${() => run("py")}>
            Python script (matplotlib)
          </button>
          <button class="export-item" role="menuitem" onClick=${() => run("aps")}>
            Publication figure (APS style)
          </button>
        </div>
      `}
      ${message &&
      html`<span class="export-message ${message.failed ? "failed" : ""}" role="status">${message.text}</span>`}
      ${shown &&
      html`<${ScriptDialog} ...${shown} onSave=${saveShown} onClose=${() => setShown(null)} />`}
    </div>
  `;
}

// `panel` is what it plots (resolved). `onChange` gets changes to it, and
// `reframe` says whether they change what the axes mean (so any zoom is let go).
// `slots` gives each quantity's colour (colours.js).
export function PlotPanel({
  store,
  names,
  units,
  slots,
  panel,
  index,
  onChange,
  onDuplicate,
  onRemove,
  showPrevious,
  theme,
  view,
  onView,
  scalesRef: givenScales = null,
}) {
  const { x, logX, logY } = panel;
  const marks = panel.marks ?? "lines";
  const limits = panel.limits ?? null;
  const series = panel.series.map((s) => ({ ...s, slot: slots.get(s.name) ?? null }));
  const saved = (list) => list.map(({ name, hidden }) => ({ name, hidden }));
  const ownScales = useRef(null);
  const scalesRef = givenScales ?? ownScales; // what the plot's axes show now
  const plotRef = useRef(null); // the uPlot, to export
  const set = (change, reframe = false) => {
    onChange(change);
    if (reframe) onView(null);
  };
  const manual = manualAxes(view, limits);
  // Autoscaling both axes again: no zoom or pan, no fixed limits.
  const autoscale = () => {
    onView(null);
    if (limits?.x || limits?.y) onChange({ limits: { x: null, y: null } });
  };
  return html`
    <section class="plot-panel" aria-label=${`Plot ${index + 1}`}>
      <div class="plot-toolbar">
        <${SeriesKey}
          series=${series}
          columns=${names}
          units=${units}
          onToggle=${(name) =>
            set({
              series: saved(series.map((s) => (s.name === name ? { ...s, hidden: !s.hidden } : s))),
            })}
          onRemove=${(name) => set({ series: saved(series.filter((s) => s.name !== name)) })}
          onAdd=${(name) => {
            if (series.length < MAX_SERIES) set({ series: [...saved(series), { name }] });
          }}
        />
        <${XPicker}
          value=${x}
          columns=${names}
          units=${units}
          onChange=${(value) => set({ x: value }, true)}
        />
        <div class="toolbar-end">
          <${MarksMenu} value=${marks} onChange=${(value) => set({ marks: value })} />
          <${AxesMenu}
            limits=${limits}
            logX=${logX}
            logY=${logY}
            scalesRef=${scalesRef}
            onApply=${(next) => set(next, true)}
          />
          <${ExportMenu}
            store=${store}
            plotRef=${plotRef}
            scalesRef=${scalesRef}
            what=${{ x, series, units, showPrevious, view, limits, marks, logX, logY }}
          />
          ${onDuplicate &&
          html`
            <button
              class="icon-button"
              aria-label="Duplicate this plot"
              title="Duplicate this plot"
              onClick=${onDuplicate}
            >
              <${CopyIcon} />
            </button>
          `}
          ${onRemove &&
          html`
            <button
              class="icon-button"
              aria-label="Remove this plot"
              title="Remove this plot"
              onClick=${onRemove}
            >
              <${CloseIcon} />
            </button>
          `}
        </div>
      </div>
      <div class="plot-frame">
        <${Plot}
          store=${store}
          x=${x}
          series=${series}
          units=${units}
          showPrevious=${showPrevious}
          logX=${logX}
          logY=${logY}
          theme=${theme}
          view=${view}
          onView=${onView}
          index=${index}
          marks=${marks}
          limits=${limits}
          scalesRef=${scalesRef}
          plotRef=${plotRef}
          onAutoscale=${autoscale}
        />
        ${manual.length > 0 &&
        html`
          <div class="autoscale-off" role="status">
            <span class="autoscale-state">Autoscale off: ${manual.join(", ")}</span>
            <button
              class="autoscale-button"
              title="Scale both axes to the data again (or double-click the plot)"
              onClick=${autoscale}
            >
              Autoscale
            </button>
          </div>
        `}
      </div>
    </section>
  `;
}
