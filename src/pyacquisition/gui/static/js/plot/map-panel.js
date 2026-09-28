// A map panel: one channel of a trace as a colour map. x is the trace's axis;
// y is the traces, by any column of the rows they were taken beside (the
// temperature of a sweep, or `time`), at the midpoint of its values when the
// trace started and ended, or by when they were taken. Each trace is a strip
// reaching halfway to its neighbours in y, and no further than the median step
// (colourmap.js's `strips`), so uneven steps draw true and a long pause shows as
// a gap; and each covers its own x range, so a span changed mid-run draws true
// too. A binned trace is drawn from its means.
//
// It shows the current data file's traces (those the page keeps: traces.js).
// The colour scale follows the data, or holds fixed limits, linear or log, in
// one of colourmap.js's maps, read by the colour bar beside it. Zooming,
// panning and the axis settings work as on the other panels.
import uPlot from "uplot";
import { useEffect, useLayoutEffect, useRef, useState } from "preact/hooks";
import { html } from "../html.js";
import { usePopover, useStore } from "../hooks.js";
import { CloseIcon, CopyIcon, DownloadIcon } from "../icons.js";
import {
  COLOUR_MAPS,
  colourTable,
  drawColourBar,
  drawMap,
  strips,
  valueRange,
} from "./colourmap.js";
import { ascending, logTicks, nearestInSorted, niceTicks, tickLabels, unitOf, valueAt, withinLimits } from "./draw.js";
import { attachGestures } from "./gestures.js";
import { saveFile } from "./export.js";
import { AxesMenu, checkLimits, manualAxes } from "./panel.js";
import { axisOptions, axisSize, makeReadout, exactScale, themeStyle, tipRow, toScale } from "./plot.js";
import { NOTHING, useTraceStore } from "./trace-panel.js";

export const TAKEN = "(when taken)"; // y by the trace's own clock, not a column
const EMPTY = new Float64Array(0);

// A map panel's settings, made sound.
export function resolveMap(panel) {
  const colours = panel.colours ?? {};
  return {
    ...panel,
    kind: "map",
    channel: panel.channel ?? null,
    y: panel.y ?? null,
    colours: {
      map: COLOUR_MAPS[colours.map] ? colours.map : "viridis",
      log: !!colours.log,
      limits: colours.limits ?? null,
    },
    logX: panel.logX ?? false,
    logY: panel.logY ?? false,
  };
}

// What y can be: the columns of the rows the traces were taken beside, `time`
// first, then when they were taken.
export function yChoices(traces) {
  const names = new Set();
  for (const trace of traces) {
    for (const name of Object.keys(trace.row ?? {})) names.add(name);
    for (const name of Object.keys(trace.row_start ?? {})) names.add(name);
  }
  const sorted = [...names].sort((a, b) => (a === "time" ? -1 : b === "time" ? 1 : 0));
  return [...sorted, TAKEN];
}

// A trace's y: the midpoint of a column's values at its start and its end
// (or whichever there is), or, for TAKEN, of its times, in seconds after `t0`.
export function yOf(trace, y, t0 = 0) {
  if (y === TAKEN) return (trace.time_start + trace.time) / 2 - t0;
  const start = trace.row_start?.[y];
  const end = trace.row?.[y];
  if (Number.isFinite(start) && Number.isFinite(end)) return (start + end) / 2;
  if (Number.isFinite(end)) return end;
  return Number.isFinite(start) ? start : NaN;
}

// The map's rows: each trace with the channel, as {x, values, low, high, y,
// trace}, in the order they were taken. One with no y is left out.
export function mapRows(traces, { channel, y, logY = false }) {
  const kept = traces.filter((trace) => trace.values[channel]);
  const t0 = kept[0]?.time_start ?? 0;
  const ys = kept.map((trace) => yOf(trace, y, t0));
  const bands = strips(ys, { log: logY });
  const rows = [];
  kept.forEach((trace, i) => {
    if (!bands[i]) return;
    const parts = trace.values[channel];
    rows.push({
      x: trace.x,
      values: trace.binned ? parts.mean : parts.values,
      low: bands[i][0],
      high: bands[i][1],
      y: ys[i],
      trace,
    });
  });
  return rows;
}

// The ranges that hold every row: x over each's own axis, y over its strips.
export function mapExtent(rows) {
  let x = [Infinity, -Infinity];
  let y = [Infinity, -Infinity];
  for (const row of rows) {
    const n = row.x.length;
    if (n) {
      x = [Math.min(x[0], row.x[0], row.x[n - 1]), Math.max(x[1], row.x[0], row.x[n - 1])];
    }
    y = [Math.min(y[0], row.low), Math.max(y[1], row.high)];
  }
  const sound = ([low, high]) => (low < high ? { min: low, max: high } : low === high ? { min: low - 1, max: high + 1 } : { min: 0, max: 1 });
  return { x: sound(x), y: sound(y) };
}

// What the axes show: a view held by zooming or panning, fixed limits, or all
// the rows.
function chooseMapScales(rows, { view, limits }, logX, logY) {
  const fits = mapExtent(rows);
  const x = view?.x ?? (limits?.x ? { ...limits.x } : fits.x);
  const y = view?.y ?? (limits?.y ? { ...limits.y } : fits.y);
  return { x: withinLimits({ ...x, log: logX }), y: withinLimits({ ...y, log: logY }) };
}

// The colour scale: fixed limits, or the rows' values.
export function colourScale(rows, colours) {
  const range = colours.limits
    ? [colours.limits.min, colours.limits.max]
    : (valueRange(rows, { log: colours.log }) ?? (colours.log ? [1, 10] : [0, 1]));
  return { min: range[0], max: range[1], log: colours.log };
}

const withUnit = (name, unit) => (unit ? `${name} (${unit})` : name);

// The value under the pointer: of the row whose strip it is in, nearest in x.
function showReadout(u, readout, drawing, px, py, container) {
  const width = u.over.clientWidth;
  const height = u.over.clientHeight;
  const xScale = { min: u.scales.x.min, max: u.scales.x.max, log: u._log.x };
  const yScale = { min: u.scales.y.min, max: u.scales.y.max, log: u._log.y };
  const yValue = valueAt(yScale, 1 - py / height);
  const xValue = valueAt(xScale, px / width);
  const row = drawing?.rows.findLast((r) => yValue >= r.low && yValue <= r.high);
  if (!row || row.x.length === 0) return readout.hide();
  const index = ascending(row.x)
    ? nearestInSorted(row.x, xValue)
    : row.x.reduce((best, v, i) => (Math.abs(v - xValue) < Math.abs(row.x[best] - xValue) ? i : best), 0);
  const { labels } = drawing;
  readout.crosshair.style.display = "block";
  readout.crosshair.style.transform = `translateX(${unitOf(xScale, row.x[index]) * width}px)`;
  readout.dots.replaceChildren();
  readout.tip.replaceChildren(
    tipRow(row.values[index], labels.unit, null, labels.channel),
    tipRow(row.x[index], labels.xUnit, null, labels.xName),
    tipRow(row.y, labels.yUnit, null, labels.y),
  );
  const over = u.over.getBoundingClientRect();
  const box = container.getBoundingClientRect();
  const tip = readout.tip;
  tip.style.display = "block";
  const left = over.left - box.left + px;
  const top = over.top - box.top + py;
  const gap = 14;
  const tx = left + gap + tip.offsetWidth > box.width ? left - gap - tip.offsetWidth : left + gap;
  const ty = Math.min(Math.max(top - tip.offsetHeight / 2, 4), box.height - tip.offsetHeight - 4);
  tip.style.transform = `translate(${Math.max(4, tx)}px, ${ty}px)`;
}

// How long the last draws took, in milliseconds, on
// `window.pyacquisition.mapTimes`.
const TIMES_KEPT = 50;
const times = [];

// The traces of the current data file (the store keeps the one before too).
const currentTraces = (store) => {
  const file = store.files[1];
  return file ? store.traces.filter((t) => t.data_file === file) : store.traces;
};

// The map, drawn: made again when its axes' kind or titles or the theme
// change; each new trace goes straight to it. `onFrame` is told where the
// plot's area is (css pixels), for the colour bar to line up with it, and
// `onColour` the colour scale, whenever they change.
function MapPlot({
  store,
  settings: given,
  labels,
  theme,
  view,
  onView,
  index,
  scalesRef,
  plotRef,
  onAutoscale,
  onFrame,
  onColour,
}) {
  const box = useRef(null);
  const plot = useRef(null);
  const settings = useRef({});
  settings.current = { ...given, labels, view, onView, onAutoscale, index, onFrame, onColour };
  const { logX, logY } = given;
  const xTitle = withUnit(labels.xName, labels.xUnit);
  const yTitle = withUnit(labels.y, labels.yUnit);

  useEffect(() => {
    const container = box.current;
    const style = themeStyle();
    const u = new uPlot(
      {
        width: container.clientWidth,
        height: container.clientHeight,
        mode: 2,
        padding: [16, 12, 4, 4],
        scales: { x: exactScale(logX), y: exactScale(logY) },
        axes: [
          { ...axisOptions(style, xTitle, logX), size: 32, labelSize: 20, grid: { show: false } },
          { ...axisOptions(style, yTitle, logY), size: axisSize, grid: { show: false } },
        ],
        // One series that draws nothing: the map is drawn by the draw hook.
        series: [
          {},
          {
            facets: [
              { scale: "x", auto: false },
              { scale: "y", auto: false },
            ],
            paths: () => null,
            points: { show: false },
          },
        ],
        legend: { show: false },
        cursor: { show: false },
        select: { show: false },
        hooks: {
          draw: [
            (u) => {
              const d = u._drawing;
              if (!d) return;
              const x = { min: u.scales.x.min, max: u.scales.x.max, log: logX };
              const y = { min: u.scales.y.min, max: u.scales.y.max, log: logY };
              d.drawn = drawMap(u.ctx, u.bbox, d.rows, { x, y, colour: d.colour, table: d.table });
            },
          ],
        },
      },
      [null, [EMPTY, EMPTY]],
      container,
    );
    u._log = { x: logX, y: logY };
    plot.current = u;

    const readout = makeReadout(u, container);
    let pointer = null;
    let frame = null;
    let lastFrame = "";
    let lastColour = "";

    const scalesNow = () => ({
      x: { min: u.scales.x.min, max: u.scales.x.max, log: logX },
      y: { min: u.scales.y.min, max: u.scales.y.max, log: logY },
    });
    const refreshReadout = () => {
      if (pointer && !gestures?.active()) showReadout(u, readout, u._drawing, pointer.x, pointer.y, container);
      else readout.hide();
    };
    const tellFrame = () => {
      const ratio = devicePixelRatio;
      const at = { top: u.bbox.top / ratio, height: u.bbox.height / ratio };
      const key = `${at.top}:${at.height}`;
      if (key !== lastFrame) {
        lastFrame = key;
        settings.current.onFrame?.(at);
      }
    };

    const redraw = () => {
      const now = settings.current;
      // One about to be replaced draws nothing meanwhile.
      if (now.logX !== logX || now.logY !== logY) return;
      if (withUnit(now.labels.xName, now.labels.xUnit) !== xTitle || withUnit(now.labels.y, now.labels.yUnit) !== yTitle) return;
      const start = performance.now();
      const rows = mapRows(currentTraces(store), { channel: now.channel, y: now.y, logY });
      const colour = colourScale(rows, now.colours);
      u._drawing = { rows, colour, table: colourTable(now.colours.map), labels: now.labels };
      const colourKey = JSON.stringify(colour);
      if (colourKey !== lastColour) {
        lastColour = colourKey;
        now.onColour?.(colour);
      }
      u._drawnView = now.view;
      const scales = chooseMapScales(rows, now, logX, logY);
      u.batch(() => {
        u.setData([null, [EMPTY, EMPTY]], false); // so it draws again
        u.setScale("x", toScale([scales.x.min, scales.x.max]));
        u.setScale("y", toScale([scales.y.min, scales.y.max]));
      });
      refreshReadout();
      tellFrame();
      times.push(performance.now() - start);
      if (times.length > TIMES_KEPT) times.shift();
      if (window.pyacquisition) {
        (window.pyacquisition.mapPlots ??= [])[now.index] = u;
        window.pyacquisition.mapTimes = times;
      }
    };
    u._redraw = redraw;

    const setView = (next) => {
      settings.current.view = next;
      redraw();
      settings.current.onView(next);
    };
    const gestures = attachGestures(u, {
      scalesNow,
      setView,
      fitY: () => mapExtent(u._drawing?.rows ?? []).y,
      onAutoscale: () => settings.current.onAutoscale?.(),
      onGesture: () => readout.hide(),
      onPointer: (point, now) => {
        pointer = point;
        if (!point) readout.hide();
        else if (now) refreshReadout();
        else if (frame === null) {
          frame = requestAnimationFrame(() => {
            frame = null;
            refreshReadout();
          });
        }
      },
    });
    if (scalesRef) scalesRef.current = scalesNow;
    if (plotRef) plotRef.current = u;

    redraw();
    const unsubscribe = store.subscribe(redraw);
    const resize = new ResizeObserver(([entry]) => {
      const { width, height } = entry.contentRect;
      u.setSize({ width: Math.floor(width), height: Math.floor(height) });
      refreshReadout();
      tellFrame();
    });
    resize.observe(container);
    return () => {
      unsubscribe();
      resize.disconnect();
      if (frame !== null) cancelAnimationFrame(frame);
      readout.tip.remove();
      u.destroy();
      plot.current = null;
      if (plotRef?.current === u) plotRef.current = null;
      const plots = window.pyacquisition?.mapPlots ?? [];
      if (plots.includes(u)) plots[plots.indexOf(u)] = null;
    };
  }, [store, logX, logY, theme, xTitle, yTitle]);

  // A change of what is shown, drawn again without a new plot.
  useEffect(() => {
    plot.current?._redraw();
  }, [given.channel, given.y, JSON.stringify(given.colours), JSON.stringify(given.limits ?? null)]);

  useLayoutEffect(() => {
    if (plot.current && plot.current._drawnView !== view) plot.current._redraw();
  }, [view]);

  return html`<div class="plot-canvas" ref=${box}></div>`;
}

// ------------------------------------------------------------------ the colour bar

// The ticks of a colour scale, with their labels, and where each falls (0 at
// the bottom, 1 at the top).
export function colourTicks(scale) {
  const { ticks, even } = scale.log ? logTicks(scale.min, scale.max) : { ticks: niceTicks(scale.min, scale.max, 5), even: true };
  const labels = tickLabels(ticks, { log: scale.log && !even });
  return ticks.map((value, i) => ({ value, label: labels[i], at: unitOf(scale, value) }));
}

function ColourBar({ table, scale, frame }) {
  const canvas = useRef(null);
  useLayoutEffect(() => {
    const c = canvas.current;
    if (!c || !frame) return;
    c.width = 1;
    c.height = Math.max(1, Math.round(frame.height));
    drawColourBar(c, table);
  }, [table, frame?.height]);
  if (!frame || !scale) return null;
  return html`
    <div class="colour-bar" style=${{ paddingTop: `${frame.top}px` }} aria-label="Colour scale">
      <div class="colour-bar-scale" style=${{ height: `${frame.height}px` }}>
        <canvas ref=${canvas} class="colour-bar-canvas"></canvas>
        ${colourTicks(scale).map(
          (tick) => html`
            <span key=${tick.value} class="colour-bar-tick" style=${{ bottom: `${tick.at * 100}%` }}>
              ${tick.label}
            </span>
          `,
        )}
      </div>
    </div>
  `;
}

// The colour settings: the map, log or linear, and automatic or fixed limits.
// Nothing changes until Apply.
function ColourMenu({ colours, scale, onApply }) {
  const [draft, setDraft] = useState(null);
  const [error, setError] = useState("");
  const menu = useRef(null);
  usePopover(menu, !!draft, () => setDraft(null));
  const open = () => {
    const shown = colours.limits ?? scale;
    setDraft({
      map: colours.map,
      c: {
        auto: !colours.limits,
        min: shown ? String(Number(shown.min.toPrecision(6))) : "",
        max: shown ? String(Number(shown.max.toPrecision(6))) : "",
        log: colours.log,
      },
    });
    setError("");
  };
  const apply = () => {
    // Checked as an axis's limits are (panel.js), with y's rules standing in.
    const checked = checkLimits({ x: { auto: true, min: "", max: "", log: false }, y: draft.c });
    if (checked.error) return setError(checked.error.replace(/^Y: /, ""));
    onApply({ map: draft.map, log: draft.c.log, limits: checked.limits.y });
    setDraft(null);
  };
  const edit = (change) => setDraft((d) => ({ ...d, c: { ...d.c, ...change } }));
  return html`
    <div class="axes-control" ref=${menu}>
      <button
        class="icon-button colour-button"
        aria-label="Colour scale"
        aria-expanded=${!!draft}
        title=${`Colour scale: ${colours.map}${colours.log ? ", log" : ""}${colours.limits ? ", fixed" : ""}`}
        onClick=${() => (draft ? setDraft(null) : open())}
      >
        <span class="colour-swatch" style=${{ background: `linear-gradient(90deg, ${COLOUR_MAPS[colours.map].join(", ")})` }}></span>
      </button>
      ${draft &&
      html`
        <div class="axes-menu" role="dialog" aria-label="Colour scale">
          <div class="axes-row">
            <span class="axes-name">Map</span>
            <select aria-label="Colour map" value=${draft.map} onChange=${(e) => setDraft((d) => ({ ...d, map: e.target.value }))}>
              ${Object.keys(COLOUR_MAPS).map((name) => html`<option key=${name} value=${name}>${name}</option>`)}
            </select>
          </div>
          <div class="axes-row">
            <span class="axes-name">Scale</span>
            <label class="axes-auto">
              <input type="checkbox" checked=${draft.c.auto} onChange=${(e) => edit({ auto: e.target.checked })} />
              Auto
            </label>
            <input
              class="axes-input"
              aria-label="Colour minimum"
              inputmode="decimal"
              value=${draft.c.min}
              disabled=${draft.c.auto}
              onInput=${(e) => edit({ min: e.target.value })}
              onKeyDown=${(e) => e.key === "Enter" && apply()}
            />
            <span class="axes-to">to</span>
            <input
              class="axes-input"
              aria-label="Colour maximum"
              inputmode="decimal"
              value=${draft.c.max}
              disabled=${draft.c.auto}
              onInput=${(e) => edit({ max: e.target.value })}
              onKeyDown=${(e) => e.key === "Enter" && apply()}
            />
            <label class="axes-log">
              <input type="checkbox" aria-label="Log colour" checked=${draft.c.log} onChange=${(e) => edit({ log: e.target.checked })} />
              Log
            </label>
          </div>
          ${error && html`<p class="axes-error" role="alert">${error}</p>`}
          <div class="axes-buttons">
            <button class="button button-primary" onClick=${apply}>Apply</button>
          </div>
        </div>
      `}
    </div>
  `;
}

// ------------------------------------------------------------------ export

// The map as an image: the plot as drawn, with its colour bar and its ticks
// beside it, on the page's background. Resolves to a PNG blob.
function mapImage(u, drawing, frame) {
  const cssValue = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  const source = u.ctx.canvas;
  const ratio = source.width / u.width;
  const bar = 80; // css pixels for the bar and its labels
  const canvas = document.createElement("canvas");
  canvas.width = source.width + Math.round(bar * ratio);
  canvas.height = source.height;
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = cssValue("--bg");
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.drawImage(source, 0, 0);
  const strip = document.createElement("canvas");
  strip.width = Math.round(14 * ratio);
  strip.height = Math.round(frame.height * ratio);
  drawColourBar(strip, drawing.table);
  const left = source.width + Math.round(8 * ratio);
  const top = Math.round(frame.top * ratio);
  ctx.drawImage(strip, left, top);
  ctx.save();
  ctx.scale(ratio, ratio);
  ctx.fillStyle = cssValue("--text-muted");
  ctx.font = `11px ${cssValue("--font-sans")}`;
  ctx.textBaseline = "middle";
  for (const tick of colourTicks(drawing.colour)) {
    ctx.fillText(tick.label, left / ratio + 18, frame.top + (1 - tick.at) * frame.height);
  }
  ctx.restore();
  return new Promise((resolve, reject) =>
    canvas.toBlob((blob) => (blob ? resolve(blob) : reject(new Error("no image"))), "image/png"),
  );
}

function MapExport({ plotRef, frame, name }) {
  const [message, setMessage] = useState(null);
  const timer = useRef(null);
  const run = async () => {
    clearTimeout(timer.current);
    try {
      const u = plotRef.current;
      if (!u?._drawing || !frame) throw new Error("there is no map yet");
      const where = await saveFile(`${name}.png`.replace(/[<>:"/\\|?*]/g, "_"), await mapImage(u, u._drawing, frame));
      if (where) setMessage({ text: `Saved ${where}` });
    } catch (error) {
      setMessage({ text: `Couldn't export: ${error.message ?? error}`, failed: true });
    }
    timer.current = setTimeout(() => setMessage(null), 5000);
  };
  return html`
    <div class="axes-control export-control">
      <button class="icon-button" aria-label="Export" title="Save an image of this map (PNG)" onClick=${run}>
        <${DownloadIcon} />
      </button>
      ${message &&
      html`<span class="export-message ${message.failed ? "failed" : ""}" role="status">${message.text}</span>`}
    </div>
  `;
}

// ------------------------------------------------------------------ the panel

// `panel` is what it shows (resolved); `traces` the experiment's (from
// /traces), or null until they are known; `units` the columns' units.
export function MapPanel({
  panel,
  traces,
  units = {},
  index,
  onChange,
  onDuplicate,
  onRemove,
  theme,
  view,
  onView,
  scalesRef: givenScales = null,
}) {
  const store = useTraceStore(panel.trace);
  useStore(store ?? NOTHING);
  const ownScales = useRef(null);
  const scalesRef = givenScales ?? ownScales;
  const plotRef = useRef(null);
  const [frame, setFrame] = useState(null);
  const [colour, setColour] = useState(null); // the colour scale drawn
  const info = traces?.find((t) => t.name === panel.trace) ?? null;
  const shown = store ? currentTraces(store) : [];
  const latest = shown.at(-1) ?? null;
  const channels = latest?.channels ?? info?.channels ?? [];
  const channel = channels.includes(panel.channel) ? panel.channel : (channels[0] ?? null);
  const choices = yChoices(shown);
  const y = choices.includes(panel.y) ? panel.y : choices[0];
  const limits = panel.limits ?? null;
  const manual = manualAxes(view, limits);
  const set = (change, reframe = false) => {
    onChange(change);
    if (reframe) onView(null);
  };
  const autoscale = () => {
    onView(null);
    if (limits?.x || limits?.y) onChange({ limits: { x: null, y: null } });
  };
  const labels = {
    xName: latest?.x_name ?? "x",
    xUnit: latest?.x_unit ?? null,
    channel: channel ?? "",
    unit: latest?.unit ?? null,
    y: y === TAKEN ? "time taken" : y,
    yUnit: y === TAKEN ? "s" : (units[y] ?? null),
  };
  const missing = traces && !info;

  return html`
    <section class="plot-panel map-panel" aria-label=${`Plot ${index + 1}`} data-trace=${panel.trace}>
      <div class="plot-toolbar">
        <div class="series-key" role="group" aria-label="Map of">
          <span class="picker-label">Map</span>
          ${traces && traces.length > 1
            ? html`
                <label class="picker">
                  <select
                    aria-label="Trace"
                    value=${panel.trace}
                    onChange=${(e) => set({ trace: e.target.value, channel: null, y: null }, true)}
                  >
                    ${traces.map((t) => html`<option key=${t.name} value=${t.name}>${t.name}</option>`)}
                  </select>
                </label>
              `
            : html`<span class="trace-name">${panel.trace}</span>`}
          ${channels.length > 1 &&
          html`
            <label class="picker">
              <select aria-label="Channel" value=${channel} onChange=${(e) => set({ channel: e.target.value })}>
                ${channels.map((c) => html`<option key=${c} value=${c}>${c}</option>`)}
              </select>
            </label>
          `}
        </div>
        <label class="picker">
          <span class="picker-label">against</span>
          <select aria-label="Against" value=${y} onChange=${(e) => set({ y: e.target.value }, true)}>
            ${choices.map(
              (name) => html`<option key=${name} value=${name}>${name === TAKEN ? "when taken" : withUnit(name, units[name])}</option>`,
            )}
          </select>
        </label>
        <div class="toolbar-end">
          <${ColourMenu}
            colours=${panel.colours}
            scale=${colour}
            onApply=${(colours) => set({ colours })}
          />
          <${AxesMenu}
            limits=${limits}
            logX=${panel.logX}
            logY=${panel.logY}
            scalesRef=${scalesRef}
            onApply=${(next) => set(next, true)}
          />
          <${MapExport} plotRef=${plotRef} frame=${frame} name=${`${latest?.data_file?.replace(/\.[^.]+$/, "") ?? "map"} - ${panel.trace} map`} />
          ${onDuplicate &&
          html`
            <button class="icon-button" aria-label="Duplicate this plot" title="Duplicate this plot" onClick=${onDuplicate}>
              <${CopyIcon} />
            </button>
          `}
          ${onRemove &&
          html`
            <button class="icon-button" aria-label="Remove this plot" title="Remove this plot" onClick=${onRemove}>
              <${CloseIcon} />
            </button>
          `}
        </div>
      </div>
      <div class="plot-frame">
        ${missing
          ? html`<div class="empty-state"><p>There is no trace called ${panel.trace} in this experiment.</p></div>`
          : store &&
            html`
              <${MapPlot}
                store=${store}
                settings=${{ channel, y, colours: panel.colours, logX: panel.logX, logY: panel.logY, limits }}
                labels=${labels}
                theme=${theme}
                view=${view}
                onView=${onView}
                index=${index}
                scalesRef=${scalesRef}
                plotRef=${plotRef}
                onAutoscale=${autoscale}
                onFrame=${setFrame}
                onColour=${setColour}
              />
              <${ColourBar} table=${colourTable(panel.colours.map)} scale=${colour} frame=${frame} />
              ${!latest &&
              html`<div class="trace-waiting" role="status">Waiting for the first ${panel.trace} trace</div>`}
            `}
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
