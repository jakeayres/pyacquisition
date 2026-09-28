// A plot of one or more columns against another, drawn with uPlot, with zooming,
// panning and a readout of the values under the pointer.
//
// Each y column is drawn twice: the previous data file in its colour but faded
// and thinner, behind the current one. uPlot runs in its "mode 2", where each
// series has its own x values, since the two files' rows are kept apart, and x
// need not be sorted (a sweep may go up and back down). The lines, ranges and
// readout are worked out here (see draw.js), and the data is handed over as the
// store's own arrays, without copying.
//
// The axes scale to the data (their ranges fit everything, newest included)
// until it is zoomed or panned, or given fixed limits. A zoom or pan holds that
// `view` until autoscaling is turned back on (a double-click, or the panel's
// "Autoscale"). The data keeps arriving and being drawn all the while.
import uPlot from "uplot";
import { useEffect, useLayoutEffect, useRef } from "preact/hooks";
import { html } from "../html.js";
import { formatValue } from "../format.js";
import {
  ascending,
  extent,
  extentWithin,
  linePath,
  logTicks,
  pointPath,
  nearestInSorted,
  nearestPoint,
  padded,
  tickLabels,
  unitOf,
  valueAt,
  withinLimits,
} from "./draw.js";
import { attachGestures } from "./gestures.js";

const EMPTY = new Float64Array(0);
const LINE_WIDTH = 2;
const PREVIOUS_WIDTH = 1;
const DOT = 2.5; // a point's radius, in CSS pixels
const PREVIOUS_DOT = 2;
const X_PADDING = 0.01; // so the newest point sits just inside the right edge
const Y_PADDING = 0.05;
const LABEL_MARGIN = 10; // between the y axis title and its tick labels

function cssValue(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

// The colours and type of the current theme, read from tokens.css.
export function themeStyle() {
  return {
    // A quantity's colour (colours.js): its slot's, or the neutral one.
    series: (slot) => cssValue(slot ? `--series-${slot}` : "--series-other"),
    previousOpacity: parseFloat(cssValue("--previous-opacity")) || 0.35,
    text: cssValue("--text-muted"),
    grid: cssValue("--plot-grid"),
    axis: cssValue("--plot-axis"),
    font: cssValue("--font-sans"),
  };
}

// "#2a78d6" with an opacity, as canvas wants it.
export function withOpacity(hex, opacity) {
  const n = parseInt(hex.slice(1), 16);
  return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${opacity})`;
}

export function axisLabel(names, units) {
  const parts = [].concat(names).map((n) => (units[n] ? `${n} (${units[n]})` : n));
  return parts.join(", ");
}

const NO_PATH = new Path2D();

// uPlot calls this to draw a series: our own line, or dots, or both (the panel's
// `marks`), in canvas pixels. Dots are filled in the series' colour; the
// previous file's (odd series) a little smaller. As lines, a point with no
// neighbour to join (a sparse column's) is drawn as a dot of its own.
function drawSeries(u, seriesIndex) {
  const [xs, ys] = u.data[seriesIndex];
  const x = { min: u.scales.x.min, max: u.scales.x.max, log: u._log.x };
  const y = { min: u.scales.y.min, max: u.scales.y.max, log: u._log.y };
  const marks = u._marks;
  const radius = (seriesIndex % 2 ? PREVIOUS_DOT : DOT) * devicePixelRatio;
  return {
    stroke:
      marks === "points"
        ? NO_PATH
        : linePath(
            xs,
            ys,
            u.bbox,
            x,
            y,
            u._sorted.get(seriesIndex) ?? ascending(xs),
            marks === "lines" ? (u.series[seriesIndex].width * devicePixelRatio) / 2 : 0,
          ),
    fill: marks === "lines" ? null : pointPath(xs, ys, u.bbox, x, y, radius),
    clip: null,
    band: null,
    gaps: null,
    flags: 0,
  };
}

// Room for the longest tick label on the y axis, measured, so none is cut off.
export function axisSize(u, values, axisIndex, cycle) {
  const axis = u.axes[axisIndex];
  if (cycle > 1) return axis._size;
  let size = axis.ticks.size + axis.gap + LABEL_MARGIN;
  const longest = (values ?? []).reduce((a, v) => (v.length > a.length ? v : a), "");
  if (longest) {
    u.ctx.font = axis.font[0];
    size += u.ctx.measureText(longest).width / devicePixelRatio;
  }
  return Math.ceil(size);
}

// An axis, in the theme's style, with its title.
export function axisOptions(style, label, log) {
  return {
    label,
    stroke: style.text,
    font: `12px ${style.font}`,
    labelFont: `500 12px ${style.font}`,
    grid: { stroke: style.grid, width: 1 },
    ticks: { stroke: style.axis, width: 1, size: 4 },
    // A log axis gets its own ticks (logTicks): uPlot's give a narrow one
    // only a label or two. Evenly spaced ones are labelled as on a linear axis.
    ...(log && { splits: (u, i, min, max) => logTicks(min, max).ticks }),
    values: (u, splits, i, space, incr) => {
      const even = log && logTicks(u.scales[u.axes[i].scale].min, u.scales[u.axes[i].scale].max).even;
      return tickLabels(splits, { log: log && !even });
    },
  };
}

// A scale that is set here, not by uPlot, linear or log.
export const scaleOptions = (log) => ({ time: false, auto: false, distr: log ? 3 : 1, log: 10 });

function options(style, { labels, series, logX, logY }, width, height) {
  const axis = (label, log) => axisOptions(style, label, log);
  const line = (stroke, width) => ({
    stroke,
    fill: stroke, // the dots, when drawn (see drawSeries)
    width,
    facets: [
      { scale: "x", auto: false },
      { scale: "y", auto: false },
    ],
    paths: drawSeries,
    points: { show: false },
  });
  const scale = scaleOptions;
  return {
    width,
    height,
    mode: 2,
    padding: [16, 20, 4, 4],
    scales: { x: scale(logX), y: scale(logY) },
    axes: [
      { ...axis(labels.x, logX), size: 32, labelSize: 20 },
      { ...axis(labels.y, logY), size: axisSize },
    ],
    // For each column: the previous file, then the current one.
    series: [
      {},
      ...series.flatMap((s) => [
        line(withOpacity(style.series(s.slot), style.previousOpacity), PREVIOUS_WIDTH),
        line(style.series(s.slot), LINE_WIDTH),
      ]),
    ],
    legend: { show: false },
    cursor: { show: false },
    select: { show: false },
  };
}

// What is drawn: for each column and file, its x and y values, and whether the
// x values are sorted. A hidden column, or the previous file when it is hidden,
// is drawn with no points.
function gather(store, settings) {
  const { x, series, showPrevious } = settings;
  const files = [
    { segment: showPrevious ? store.previous : null, previous: true },
    { segment: store.current, previous: false },
  ].map((file) => {
    const xs = file.segment?.column(x) ?? EMPTY;
    return { ...file, xs, sorted: ascending(xs) };
  });
  const pairs = [];
  const sorted = new Map();
  series.forEach((s, i) => {
    files.forEach((file, j) => {
      const ys = (!s.hidden && file.segment?.column(s.name)) || EMPTY;
      const index = 1 + 2 * i + j;
      pairs.push([ys === EMPTY ? EMPTY : file.xs, ys]);
      sorted.set(index, file.sorted);
    });
  });
  return { files, pairs, sorted };
}

// The ranges that fit everything drawn.
function fitted(pairs, logX, logY) {
  const xs = pairs.map(([x]) => x);
  const ys = pairs.map(([, y]) => y);
  return {
    x: { log: logX, ...toScale(padded(extent(xs, { log: logX }), X_PADDING, { log: logX })) },
    y: { log: logY, ...toScale(padded(extent(ys, { log: logY }), Y_PADDING, { log: logY })) },
  };
}

export const toScale = ([min, max]) => ({ min, max });

// What the axes show, in this order of precedence:
//   1. a view held by zooming or panning (or only an x range, from a linked
//      panel, with y fitted to what is in it);
//   2. the fixed limits set for either axis (with y fitted to what is within a
//      fixed x, when y is not fixed too);
//   3. ranges that fit all the data, following it as it arrives.
// Whatever set them, log scales stay within what uPlot can label.
export function chooseScales(pairs, { view, limits }, logX, logY) {
  let chosen;
  if (view) {
    chosen = { x: view.x, y: view.y ?? yWithin(pairs, view.x, logY) };
  } else {
    const fits = fitted(pairs, logX, logY);
    const x = limits?.x ? { log: logX, ...limits.x } : fits.x;
    const y = limits?.y
      ? { log: logY, ...limits.y }
      : limits?.x
        ? yWithin(pairs, x, logY)
        : fits.y;
    chosen = { x, y };
  }
  return { x: withinLimits(chosen.x), y: withinLimits(chosen.y) };
}

// A y scale fitted to the points within an x range, with room around them.
export function yWithin(pairs, x, logY) {
  let range = null;
  for (const [xs, ys] of pairs) {
    const r = extentWithin(xs, [ys], x, { log: logY });
    if (r) range = range ? [Math.min(range[0], r[0]), Math.max(range[1], r[1])] : r;
  }
  return { log: logY, ...toScale(padded(range, Y_PADDING, { log: logY })) };
}

// ------------------------------------------------------------------ readout

// The crosshair, the dots on each line, and the box of values beside the
// pointer. Made once per plot, and moved about directly (not re-rendered).
export function makeReadout(u, container) {
  const crosshair = document.createElement("div");
  crosshair.className = "plot-crosshair";
  const dots = document.createElement("div");
  const tip = document.createElement("div");
  tip.className = "plot-tip";
  tip.setAttribute("role", "status");
  u.over.append(crosshair, dots);
  container.append(tip);
  const hide = () => {
    crosshair.style.display = "none";
    dots.replaceChildren();
    tip.style.display = "none";
  };
  hide();
  return { crosshair, dots, tip, hide };
}

export function tipRow(value, unit, key, name) {
  const row = document.createElement("div");
  row.className = "plot-tip-row";
  if (key) {
    const line = document.createElement("span");
    line.className = "plot-tip-key";
    line.style.background = key;
    row.append(line);
  }
  const strong = document.createElement("strong");
  strong.textContent = formatValue(value); // labels are data: text, never HTML
  row.append(strong);
  if (unit) {
    const u = document.createElement("span");
    u.className = "plot-tip-unit";
    u.textContent = unit;
    row.append(u);
  }
  const label = document.createElement("span");
  label.className = "plot-tip-name";
  label.textContent = name;
  row.append(label);
  return row;
}

// Shows the values of the row nearest the pointer at (px, py), in the overlay's
// CSS pixels. When x is sorted (time), the nearest in x; otherwise the nearest
// point on any line.
function showReadout(u, readout, drawn, settings, px, py, container) {
  const width = u.over.clientWidth;
  const height = u.over.clientHeight;
  const xScale = { min: u.scales.x.min, max: u.scales.x.max, log: u._log.x };
  const yScale = { min: u.scales.y.min, max: u.scales.y.max, log: u._log.y };
  const toX = (v) => unitOf(xScale, v) * width;
  const toY = (v) => (1 - unitOf(yScale, v)) * height;
  const visible = settings.series.filter((s) => !s.hidden);

  let best = null;
  for (const file of drawn.files) {
    if (!file.segment || file.xs.length === 0) continue;
    const columns = visible.map((s) => file.segment.column(s.name) ?? EMPTY);
    let index;
    let distance;
    if (file.sorted) {
      index = nearestInSorted(file.xs, valueAt(xScale, px / width));
      distance = index < 0 ? Infinity : Math.abs(toX(file.xs[index]) - px);
    } else {
      ({ index, distance } = nearestPoint(file.xs, columns, px, py, toX, toY));
    }
    if (index >= 0 && (!best || distance < best.distance)) {
      best = { file, index, distance, columns };
    }
  }
  if (!best || visible.length === 0) {
    readout.hide();
    return;
  }

  const { file, index, columns } = best;
  const xValue = file.xs[index];
  const cx = toX(xValue);
  readout.crosshair.style.display = "block";
  readout.crosshair.style.transform = `translateX(${cx}px)`;

  const style = u._style;
  const dots = [];
  readout.tip.replaceChildren(
    tipRow(xValue, settings.units[settings.x], null, settings.x),
  );
  if (file.previous) {
    const note = document.createElement("div");
    note.className = "plot-tip-note";
    note.textContent = "previous file";
    readout.tip.append(note);
  }
  visible.forEach((s, i) => {
    const yValue = columns[i][index];
    const colour = style.series(s.slot);
    readout.tip.append(tipRow(yValue, settings.units[s.name], colour, s.name));
    const cy = toY(yValue);
    if (cy === cy && cx === cx) {
      const dot = document.createElement("span");
      dot.className = "plot-dot";
      dot.style.background = colour;
      dot.style.transform = `translate(${cx}px, ${cy}px)`;
      dots.push(dot);
    }
  });
  readout.dots.replaceChildren(...dots);

  // Beside the pointer, on whichever side has room.
  const over = u.over.getBoundingClientRect();
  const box = container.getBoundingClientRect();
  const tip = readout.tip;
  tip.style.display = "block";
  const left = over.left - box.left + px;
  const top = over.top - box.top + py;
  const gap = 14;
  const x = left + gap + tip.offsetWidth > box.width ? left - gap - tip.offsetWidth : left + gap;
  const y = Math.min(Math.max(top - tip.offsetHeight / 2, 4), box.height - tip.offsetHeight - 4);
  tip.style.transform = `translate(${Math.max(4, x)}px, ${y}px)`;
}

// ------------------------------------------------------------------ the component

// Which columns, in which colours: a plot is made again when this changes.
const seriesKey = (series) => series.map((s) => `${s.name}:${s.slot}`).join(",");

// How long the last updates took, in milliseconds, drawing included: kept on
// `window.pyacquisition.plotTimes` for the tests and for checking performance.
const TIMES_KEPT = 50;
const times = [];
const readoutTimes = []; // likewise for the readout, on `readoutTimes`

export function Plot({
  store,
  x,
  series,
  units,
  showPrevious,
  logX,
  logY,
  theme,
  view,
  onView,
  index = 0, // which panel it is in, for `window.pyacquisition.plots`
  marks = "lines", // "lines", "points" or "both"
  limits = null, // fixed axis limits: {x, y}, each {min, max} or null for auto
  scalesRef = null, // given a function that returns what the axes show now
  plotRef = null, // given the uPlot, to export it
  onAutoscale = null, // turns autoscaling back on (a double-click)
}) {
  const box = useRef(null);
  const plot = useRef(null);
  const settings = useRef({});
  settings.current = {
    x,
    series,
    units,
    showPrevious,
    logX,
    logY,
    view,
    onView,
    index,
    marks,
    limits,
    onAutoscale,
  };
  const drawnKey = seriesKey(series);
  const hiddenKey = series.map((s) => (s.hidden ? "0" : "1")).join("");
  const limitsKey = JSON.stringify(limits ?? null);

  // Made again when what it shows, or the theme, changes; data updates go
  // straight to it, without re-rendering anything.
  useEffect(() => {
    const container = box.current;
    const labels = {
      x: axisLabel(x, units),
      y: axisLabel(series.map((s) => s.name), units),
    };
    const style = themeStyle();
    const u = new uPlot(
      options(style, { labels, series, logX, logY }, container.clientWidth, container.clientHeight),
      [null, ...series.flatMap(() => [[EMPTY, EMPTY], [EMPTY, EMPTY]])],
      container,
    );
    u._log = { x: logX, y: logY };
    u._style = style;
    u._sorted = new Map();
    plot.current = u;

    const readout = makeReadout(u, container);
    let drawn = { files: [], pairs: [], sorted: new Map() };
    let pointer = null; // where the pointer is over the plot, while it is
    let frame = null;

    const scalesNow = () => ({
      x: { min: u.scales.x.min, max: u.scales.x.max, log: logX },
      y: { min: u.scales.y.min, max: u.scales.y.max, log: logY },
    });

    const refreshReadout = () => {
      if (pointer && !gestures?.active()) {
        const start = performance.now();
        showReadout(u, readout, drawn, settings.current, pointer.x, pointer.y, container);
        readoutTimes.push(performance.now() - start);
        if (readoutTimes.length > TIMES_KEPT) readoutTimes.shift();
      } else readout.hide();
    };

    const redraw = () => {
      // Between a change of what is plotted and this plot being replaced, an
      // update may come; this plot cannot draw what it was not made for.
      const now = settings.current;
      if (now.x !== x || seriesKey(now.series) !== drawnKey || now.logX !== logX || now.logY !== logY) {
        return;
      }
      const start = performance.now();
      drawn = gather(store, now);
      u._sorted = drawn.sorted;
      u._marks = now.marks;
      u._drawnView = now.view;
      const scales = chooseScales(drawn.pairs, now, logX, logY);
      u.batch(() => {
        u.setData([null, ...drawn.pairs], false);
        u.setScale("x", toScale([scales.x.min, scales.x.max]));
        u.setScale("y", toScale([scales.y.min, scales.y.max]));
      });
      refreshReadout();
      times.push(performance.now() - start);
      if (times.length > TIMES_KEPT) times.shift();
      if (window.pyacquisition) {
        const plots = (window.pyacquisition.plots ??= []);
        plots[settings.current.index] = u;
        window.pyacquisition.plot = plots[0]; // the first panel's
        window.pyacquisition.plotTimes = times;
        window.pyacquisition.readoutTimes = readoutTimes;
      }
    };
    u._redraw = redraw;

    // Sets the view straight away, for a smooth drag, and tells the panel.
    const setView = (next) => {
      settings.current.view = next;
      redraw();
      settings.current.onView(next);
    };

    // ---- zooming and panning with the pointer (gestures.js)
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
      const plots = window.pyacquisition?.plots ?? [];
      if (plots.includes(u)) plots[plots.indexOf(u)] = null;
    };
  }, [store, x, drawnKey, logX, logY, theme, axisLabel(x, units), axisLabel(series.map((s) => s.name), units)]);

  // A change of which series are shown, or of the previous file: drawn again,
  // without making a new plot.
  useEffect(() => {
    plot.current?._redraw();
  }, [hiddenKey, showPrevious, marks, limitsKey]);

  // A change of view from the panel (back to live), drawn at once. A view the
  // plot set itself, while zooming or panning, is drawn already.
  useLayoutEffect(() => {
    if (plot.current && plot.current._drawnView !== view) plot.current._redraw();
  }, [view]);

  return html`<div class="plot-canvas" ref=${box}></div>`;
}
