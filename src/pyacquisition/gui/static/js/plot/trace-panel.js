// A trace panel: one trace's channels against its axis (a spectrum against
// frequency), following it as each is taken (traces.js).
//
// The latest trace is drawn fully, and the few before it (`overlay`, 0 to 10)
// fainter behind it. A binned trace (one longer than the server sends whole) is
// drawn as the band between each bin's lowest and highest value, with its mean
// as the line, so a narrow spike still shows. Zooming, panning, log axes, fixed
// limits and the readout work as on a plot panel (gestures.js, panel.js's axis
// settings). **Acquire now** takes one at once, waiting as long as the trace
// may take. It exports an image of what it shows, and the latest trace at full
// resolution as CSV.
//
// It is drawn on uPlot's canvas by a draw hook, as uPlot's own series can't draw
// a band of this kind; uPlot gives the axes, the grid and the scales.
import uPlot from "uplot";
import { useEffect, useLayoutEffect, useRef, useState } from "preact/hooks";
import { html } from "../html.js";
import { usePopover, useStore } from "../hooks.js";
import { acquireTrace } from "../api.js";
import { formatValue } from "../format.js";
import { CloseIcon, CopyIcon, DownloadIcon } from "../icons.js";
import { TraceStore, fetchLatest, traceFeed } from "../traces.js";
import { ascending, bandPath, linePath, nearestInSorted, nearestPoint, unitOf, valueAt } from "./draw.js";
import { attachGestures } from "./gestures.js";
import { plotImage, saveFile } from "./export.js";
import { AxesMenu, manualAxes } from "./panel.js";
import {
  axisOptions,
  axisSize,
  chooseScales,
  makeReadout,
  scaleOptions,
  themeStyle,
  tipRow,
  toScale,
  withOpacity,
  yWithin,
} from "./plot.js";

export const MAX_OVERLAY = 10;
export const DEFAULT_OVERLAY = 3;
const LINE_WIDTH = 1.5;
const BAND_OPACITY = 0.25; // a binned trace's band, against its line
const EMPTY = new Float64Array(0);

// A trace panel's settings, made sound: `trace` is the trace it shows.
export function resolveTrace(panel) {
  const overlay = Number.isInteger(panel.overlay) ? panel.overlay : DEFAULT_OVERLAY;
  return {
    ...panel,
    kind: "trace",
    overlay: Math.min(MAX_OVERLAY, Math.max(0, overlay)),
    logX: panel.logX ?? false,
    logY: panel.logY ?? false,
    hidden: panel.hidden ?? [],
  };
}

// A channel's colour slot: in the order the trace gives them, 1 to 8.
const slotOf = (channels, channel) => (channels.indexOf(channel) % 8) + 1;

// How strongly a trace is drawn: the latest fully, the older ones fainter.
const opacityOf = (age, overlay) => (age === 0 ? 1 : 0.5 * (1 - (age - 1) / (overlay + 1)));

// What is drawn: the traces (oldest first), and for fitting the axes, each
// visible channel's [x, values] (a binned one's lows and highs both).
function gather(store, { overlay, hidden }) {
  const traces = store.traces.slice(-(overlay + 1));
  const pairs = [];
  for (const trace of traces) {
    for (const channel of trace.channels) {
      if (hidden.includes(channel)) continue;
      const parts = trace.values[channel];
      if (trace.binned) pairs.push([trace.x, parts.min], [trace.x, parts.max]);
      else pairs.push([trace.x, parts.values]);
    }
  }
  return { traces, pairs };
}

// Draws the traces on the plot's canvas, within its box.
function paint(u) {
  const drawing = u._drawing;
  if (!drawing) return;
  const { traces, hidden, overlay } = drawing;
  const style = u._style;
  const ctx = u.ctx;
  const x = { min: u.scales.x.min, max: u.scales.x.max, log: u._log.x };
  const y = { min: u.scales.y.min, max: u.scales.y.max, log: u._log.y };
  const { left, top, width, height } = u.bbox;
  ctx.save();
  ctx.beginPath();
  ctx.rect(left, top, width, height);
  ctx.clip();
  ctx.lineWidth = LINE_WIDTH * devicePixelRatio;
  ctx.lineJoin = "round";
  traces.forEach((trace, k) => {
    const age = traces.length - 1 - k;
    const opacity = opacityOf(age, overlay);
    const sorted = ascending(trace.x);
    for (const channel of trace.channels) {
      if (hidden.includes(channel)) continue;
      const colour = style.series(slotOf(trace.channels, channel));
      const parts = trace.values[channel];
      if (trace.binned) {
        ctx.fillStyle = withOpacity(colour, opacity * BAND_OPACITY);
        ctx.fill(bandPath(trace.x, parts.min, parts.max, u.bbox, x, y));
      }
      ctx.strokeStyle = withOpacity(colour, opacity);
      const line = trace.binned ? parts.mean : parts.values;
      ctx.stroke(linePath(trace.x, line, u.bbox, x, y, sorted, ctx.lineWidth / 2));
    }
  });
  ctx.restore();
}

// The value of each visible channel of the latest trace nearest the pointer.
function showReadout(u, readout, latest, settings, px, py, container) {
  if (!latest) return readout.hide();
  const width = u.over.clientWidth;
  const height = u.over.clientHeight;
  const xScale = { min: u.scales.x.min, max: u.scales.x.max, log: u._log.x };
  const yScale = { min: u.scales.y.min, max: u.scales.y.max, log: u._log.y };
  const toX = (v) => unitOf(xScale, v) * width;
  const toY = (v) => (1 - unitOf(yScale, v)) * height;
  const visible = latest.channels.filter((c) => !settings.hidden.includes(c));
  const lines = visible.map((c) => {
    const parts = latest.values[c];
    return latest.binned ? parts.mean : parts.values;
  });
  const index = ascending(latest.x)
    ? nearestInSorted(latest.x, valueAt(xScale, px / width))
    : nearestPoint(latest.x, lines, px, py, toX, toY).index;
  if (index < 0 || visible.length === 0) return readout.hide();

  const xValue = latest.x[index];
  const cx = toX(xValue);
  readout.crosshair.style.display = "block";
  readout.crosshair.style.transform = `translateX(${cx}px)`;
  readout.tip.replaceChildren(tipRow(xValue, latest.x_unit, null, latest.x_name));
  if (latest.binned) {
    const note = document.createElement("div");
    note.className = "plot-tip-note";
    note.textContent = "mean of a bin";
    readout.tip.append(note);
  }
  const dots = [];
  visible.forEach((channel, i) => {
    const colour = u._style.series(slotOf(latest.channels, channel));
    const value = lines[i][index];
    readout.tip.append(tipRow(value, latest.unit, colour, channel));
    const cy = toY(value);
    if (cy === cy && cx === cx) {
      const dot = document.createElement("span");
      dot.className = "plot-dot";
      dot.style.background = colour;
      dot.style.transform = `translate(${cx}px, ${cy}px)`;
      dots.push(dot);
    }
  });
  readout.dots.replaceChildren(...dots);

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
// `window.pyacquisition.traceTimes` (as the plots' are on `plotTimes`).
const TIMES_KEPT = 50;
const times = [];

const withUnit = (name, unit) => (unit ? `${name} (${unit})` : name);

// The axis titles for a trace: its axis, and its channels, with their units.
const labelsOf = (latest) => ({
  x: latest ? withUnit(latest.x_name, latest.x_unit) : "",
  y: latest ? withUnit(latest.channels.join(", "), latest.unit) : "",
});

// The trace, drawn: made again when the axes' kind or titles or the theme
// change; each new trace goes straight to it.
function TracePlot({ store, settings: given, theme, view, onView, index, scalesRef, plotRef, onAutoscale }) {
  const box = useRef(null);
  const plot = useRef(null);
  const settings = useRef({});
  settings.current = { ...given, view, onView, onAutoscale, index };
  const { logX, logY } = given;
  const labels = labelsOf(store.latest);

  useEffect(() => {
    const container = box.current;
    const style = themeStyle();
    const u = new uPlot(
      {
        width: container.clientWidth,
        height: container.clientHeight,
        mode: 2,
        padding: [16, 20, 4, 4],
        scales: { x: scaleOptions(logX), y: scaleOptions(logY) },
        axes: [
          { ...axisOptions(style, labels.x, logX), size: 32, labelSize: 20 },
          { ...axisOptions(style, labels.y, logY), size: axisSize },
        ],
        // One series that draws nothing: the traces are drawn by `paint`.
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
        hooks: { draw: [paint] },
      },
      [null, [EMPTY, EMPTY]],
      container,
    );
    u._log = { x: logX, y: logY };
    u._style = style;
    plot.current = u;

    const readout = makeReadout(u, container);
    let drawn = { traces: [], pairs: [] };
    let pointer = null;
    let frame = null;

    const scalesNow = () => ({
      x: { min: u.scales.x.min, max: u.scales.x.max, log: logX },
      y: { min: u.scales.y.min, max: u.scales.y.max, log: logY },
    });
    const refreshReadout = () => {
      if (pointer && !gestures?.active()) {
        showReadout(u, readout, drawn.traces.at(-1), settings.current, pointer.x, pointer.y, container);
      } else readout.hide();
    };

    const redraw = () => {
      // A plot about to be replaced (its axes' kind or titles have changed:
      // the first trace brings the titles) draws nothing meanwhile.
      const now = settings.current;
      const titles = labelsOf(store.latest);
      if (now.logX !== logX || now.logY !== logY || titles.x !== labels.x || titles.y !== labels.y) {
        return;
      }
      const start = performance.now();
      drawn = gather(store, now);
      u._drawing = { traces: drawn.traces, hidden: now.hidden, overlay: now.overlay };
      u._drawnView = now.view;
      const scales = chooseScales(drawn.pairs, now, logX, logY);
      u.batch(() => {
        u.setData([null, [EMPTY, EMPTY]], false); // so it draws again
        u.setScale("x", toScale([scales.x.min, scales.x.max]));
        u.setScale("y", toScale([scales.y.min, scales.y.max]));
      });
      refreshReadout();
      times.push(performance.now() - start);
      if (times.length > TIMES_KEPT) times.shift();
      if (window.pyacquisition) {
        (window.pyacquisition.tracePlots ??= [])[now.index] = u;
        window.pyacquisition.traceTimes = times;
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
      fitY: (nextX) => yWithin(drawn.pairs, nextX, logY),
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
      const plots = window.pyacquisition?.tracePlots ?? [];
      if (plots.includes(u)) plots[plots.indexOf(u)] = null;
    };
  }, [store, logX, logY, theme, labels.x, labels.y]);

  // A change of what is shown, drawn again without a new plot.
  useEffect(() => {
    plot.current?._redraw();
  }, [given.overlay, given.hidden.join("\n"), JSON.stringify(given.limits ?? null)]);

  useLayoutEffect(() => {
    if (plot.current && plot.current._drawnView !== view) plot.current._redraw();
  }, [view]);

  return html`<div class="plot-canvas" ref=${box}></div>`;
}

// ------------------------------------------------------------------ the toolbar

const field = (text) => (/[",\r\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text);

// A trace as CSV: its axis, then each channel, with their units.
export function traceCsv(trace) {
  const header = [withUnit(trace.x_name, trace.x_unit), ...trace.channels.map((c) => withUnit(c, trace.unit))];
  const lines = [header.map(field).join(",")];
  const columns = [trace.x, ...trace.channels.map((c) => trace.values[c].values)];
  for (let i = 0; i < trace.length; i++) {
    lines.push(columns.map((col) => (Number.isFinite(col[i]) ? String(col[i]) : "")).join(","));
  }
  return `${lines.join("\r\n")}\r\n`;
}

const fileName = (trace, extension) => {
  const file = (trace.data_file || "trace").replace(/\.[^.]+$/, "");
  return `${file} - ${trace.name} ${trace.index}.${extension}`.replace(/[<>:"/\\|?*]/g, "_");
};

function TraceExportMenu({ store, plotRef, hidden }) {
  const [open, setOpen] = useState(false);
  const [message, setMessage] = useState(null); // {text, failed}
  const menu = useRef(null);
  const timer = useRef(null);
  usePopover(menu, open, () => setOpen(false));
  const tell = (text, failed = false) => {
    clearTimeout(timer.current);
    setMessage({ text, failed });
    timer.current = setTimeout(() => setMessage(null), 5000);
  };
  const run = async (kind) => {
    setOpen(false);
    try {
      const latest = store.latest;
      if (!latest || !plotRef.current) throw new Error("there is no trace yet");
      let name;
      let content;
      if (kind === "png") {
        const series = latest.channels
          .filter((c) => !hidden.includes(c))
          .map((c) => ({ name: c, slot: slotOf(latest.channels, c) }));
        const units = Object.fromEntries(latest.channels.map((c) => [c, latest.unit]));
        content = await plotImage(plotRef.current, { series, units });
        name = fileName(latest, "png");
      } else {
        const { traces } = await fetchLatest(store.name, { full: true });
        content = traceCsv(traces[0]);
        name = fileName(traces[0], "csv");
      }
      const where = await saveFile(name, content);
      if (where) tell(`Saved ${where}`);
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
        title="Export this trace"
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
            The latest trace, every point (CSV)
          </button>
        </div>
      `}
      ${message &&
      html`<span class="export-message ${message.failed ? "failed" : ""}" role="status">${message.text}</span>`}
    </div>
  `;
}

// Takes a trace now. The request waits as long as the trace may take.
function AcquireButton({ name, timeout }) {
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState(null);
  const acquire = async () => {
    setBusy(true);
    setProblem(null);
    try {
      await acquireTrace(name, timeout ?? undefined);
    } catch (error) {
      setProblem(error.message ?? String(error));
    } finally {
      setBusy(false);
    }
  };
  return html`
    <button
      class="bar-button acquire-button"
      disabled=${busy}
      aria-busy=${busy}
      title=${`Take a ${name} trace now`}
      onClick=${acquire}
    >
      ${busy ? "Acquiring…" : "Acquire now"}
    </button>
    ${problem && html`<span class="export-message failed" role="alert">${problem}</span>`}
  `;
}

const clock = (seconds) => new Date(seconds * 1000).toLocaleTimeString();

// When the latest was taken, and the row it was taken beside.
function TraceNote({ latest }) {
  if (!latest) return null;
  const row = Object.entries(latest.row ?? {});
  const title = row.map(([name, value]) => `${name}: ${formatValue(value)}`).join("\n");
  return html`
    <span class="trace-note" title=${title || null}>
      #${latest.index} at ${clock(latest.time)}${latest.binned
        ? html` · ${latest.points.toLocaleString()} points, binned`
        : ""}
    </span>
  `;
}

const NOTHING = { version: 0, subscribe: () => () => {} }; // no store yet

// One trace's store, following it while the panel shows it.
function useTraceStore(name) {
  const [store, setStore] = useState(null);
  useEffect(() => {
    const made = new TraceStore(name);
    const stop = traceFeed(made, {});
    setStore(made);
    return stop;
  }, [name]);
  return store;
}

// `panel` is what it shows (resolved); `traces` the experiment's (from
// /traces), or null until they are known.
export function TracePanel({
  panel,
  traces,
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
  const info = traces?.find((t) => t.name === panel.trace) ?? null;
  const latest = store?.latest ?? null;
  const channels = latest?.channels ?? info?.channels ?? [];
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
  const toggle = (channel) =>
    set({
      hidden: panel.hidden.includes(channel)
        ? panel.hidden.filter((c) => c !== channel)
        : [...panel.hidden, channel],
    });
  const missing = traces && !info;

  return html`
    <section class="plot-panel trace-panel" aria-label=${`Plot ${index + 1}`} data-trace=${panel.trace}>
      <div class="plot-toolbar">
        <div class="series-key" role="group" aria-label="Trace channels">
          ${traces && traces.length > 1
            ? html`
                <label class="picker">
                  <select
                    aria-label="Trace"
                    value=${panel.trace}
                    onChange=${(e) => set({ trace: e.target.value, hidden: [] }, true)}
                  >
                    ${traces.map((t) => html`<option key=${t.name} value=${t.name}>${t.name}</option>`)}
                  </select>
                </label>
              `
            : html`<span class="picker-label trace-name">${panel.trace}</span>`}
          ${channels.map(
            (channel) => html`
              <span key=${channel} class="series-chip ${panel.hidden.includes(channel) ? "hidden" : ""}">
                <button
                  class="series-toggle"
                  aria-pressed=${!panel.hidden.includes(channel)}
                  title=${panel.hidden.includes(channel) ? `Show ${channel}` : `Hide ${channel}`}
                  onClick=${() => toggle(channel)}
                >
                  <span
                    class="key-line"
                    style=${{ background: `var(--series-${slotOf(channels, channel)})` }}
                  ></span>
                  <span class="series-name">${withUnit(channel, latest?.unit ?? null)}</span>
                </button>
              </span>
            `,
          )}
        </div>
        <label class="picker">
          <span class="picker-label">behind</span>
          <select
            aria-label="Earlier traces shown behind"
            value=${panel.overlay}
            onChange=${(e) => set({ overlay: Number(e.target.value) })}
          >
            ${Array.from({ length: MAX_OVERLAY + 1 }, (_, n) => html`<option key=${n} value=${n}>${n}</option>`)}
          </select>
        </label>
        <${TraceNote} latest=${latest} />
        <div class="toolbar-end">
          ${!missing && html`<${AcquireButton} name=${panel.trace} timeout=${info?.timeout} />`}
          <${AxesMenu}
            limits=${limits}
            logX=${panel.logX}
            logY=${panel.logY}
            scalesRef=${scalesRef}
            onApply=${(next) => set(next, true)}
          />
          ${store && html`<${TraceExportMenu} store=${store} plotRef=${plotRef} hidden=${panel.hidden} />`}
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
              <${TracePlot}
                store=${store}
                settings=${{ overlay: panel.overlay, hidden: panel.hidden, logX: panel.logX, logY: panel.logY, limits }}
                theme=${theme}
                view=${view}
                onView=${onView}
                index=${index}
                scalesRef=${scalesRef}
                plotRef=${plotRef}
                onAutoscale=${autoscale}
              />
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
