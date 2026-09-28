// Drawing a plot of columns against another: the axis ranges, the lines, the
// tick labels, finding the point under the pointer, and zooming and panning.
// Plain functions of the data, so they can be tested alone.
//
// A scale is what an axis shows: `{min, max, log}`. On a log scale, a value of
// zero or below has no place, and is treated as missing (like NaN).

// Where a value falls on a scale, from 0 (min) to 1 (max). NaN if it has no
// place on it.
export function unitOf(scale, value) {
  if (scale.log) {
    if (!(value > 0)) return NaN;
    const low = Math.log10(scale.min);
    return (Math.log10(value) - low) / (Math.log10(scale.max) - low);
  }
  return (value - scale.min) / (scale.max - scale.min);
}

// The value at a place on a scale, from 0 (min) to 1 (max).
export function valueAt(scale, unit) {
  if (scale.log) {
    const low = Math.log10(scale.min);
    return 10 ** (low + unit * (Math.log10(scale.max) - low));
  }
  return scale.min + unit * (scale.max - scale.min);
}

// The lowest and highest values across some columns that a scale can show (NaN
// is skipped, and on a log scale so is anything not above zero), or null if
// there are none.
export function extent(columns, { log = false } = {}) {
  let low = Infinity;
  let high = -Infinity;
  for (const values of columns) {
    for (let i = 0; i < values.length; i++) {
      const v = values[i];
      if (log && !(v > 0)) continue;
      if (v < low) low = v; // false for NaN, so it is skipped
      if (v > high) high = v;
    }
  }
  return low <= high ? [low, high] : null;
}

// The most a log scale can show. uPlot's tick labelling for a log axis runs away
// (until the page runs out of memory) once the scale starts below somewhere
// between 1e-22 and 1e-25, whatever its top, so no log scale is given to it
// beyond these (with room to spare).
export const LOG_LIMITS = [1e-20, 1e25];

// A log scale kept within LOG_LIMITS (and a linear one as it is).
export function withinLimits(scale) {
  if (!scale.log) return scale;
  const [lowest, highest] = LOG_LIMITS;
  const min = Math.min(Math.max(scale.min, lowest), highest / 10);
  let max = Math.min(scale.max, highest);
  if (!(max > min)) max = min * 10; // only if clamping left it no span at all
  return { ...scale, min, max };
}

// A range with room around the data, so the line does not touch the edges. A
// flat line gets a band around its value. On a log scale the room is shared out
// in powers of ten, and the range kept within LOG_LIMITS.
export function padded(range, fraction = 0.05, { log = false } = {}) {
  if (log) {
    if (!range) return [1, 10];
    let [low, high] = range.map(Math.log10);
    const room = high === low ? 0.5 : (high - low) * fraction;
    const scale = withinLimits({ min: 10 ** (low - room), max: 10 ** (high + room), log });
    return [scale.min, scale.max];
  }
  if (!range) return [0, 1];
  const [low, high] = range;
  if (low === high) {
    const room = Math.abs(low) * 0.1 || 1;
    return [low - room, high + room];
  }
  const room = (high - low) * fraction;
  return [low - room, high + room];
}

// Whether a column never goes down (NaN aside), as a time column does.
export function ascending(values) {
  let previous = -Infinity;
  for (let i = 0; i < values.length; i++) {
    const v = values[i];
    if (v !== v) continue; // NaN
    if (v < previous) return false;
    previous = v;
  }
  return true;
}

// The line through the points (xs[i], ys[i]) in the order they were measured, as
// a Path2D in canvas pixels. `area` is the plot's box, and `x` and `y` the scales
// it shows. A point with no place on a scale (NaN, or not above zero on a log
// scale) breaks the line.
//
// Hundreds of thousands of points cannot all be drawn every update, and need not
// be: when x never goes down (a time axis), only the first, lowest, highest and
// last point of each pixel column can be seen, so those are drawn (two to four
// points a pixel, however long the data). Otherwise the line may double back (a
// sweep up and down), so every point is kept in order, leaving out only those
// that land on the same pixel as the one before.
//
// With a `dot` radius, a point that joins nothing (between gaps, as a sparse
// column's are) is drawn as a small circle, which the stroke fills in, so it
// shows. `path.dots` says how many were.
export function linePath(xs, ys, area, x, y, sorted = ascending(xs), dot = 0) {
  const path = new Path2D();
  path.dots = 0;
  const n = Math.min(xs.length, ys.length);
  if (n === 0 || x.max === x.min || y.max === y.min) return path;
  const bottom = area.top + area.height;
  const toX = (v) => area.left + unitOf(x, v) * area.width;
  const toY = (v) => bottom - unitOf(y, v) * area.height;

  let pen = false; // whether the next point joins the one before
  // The start of the piece of line being drawn, until it joins another point.
  let lone = null;
  const endPiece = () => {
    if (lone && dot > 0) {
      path.moveTo(lone[0] + dot, lone[1]);
      path.arc(lone[0], lone[1], dot, 0, 2 * Math.PI);
      path.dots++;
    }
    lone = null;
  };

  if (sorted) {
    let column = null;
    let first = 0;
    let low = 0;
    let high = 0;
    let last = 0;
    const flush = () => {
      if (column === null) return;
      if (pen) {
        path.lineTo(column, first);
        lone = null;
      } else {
        path.moveTo(column, first);
        lone = low === high ? [column, first] : null;
      }
      if (low !== high) {
        path.lineTo(column, low);
        path.lineTo(column, high);
      }
      path.lineTo(column, last);
      pen = true;
    };
    for (let i = 0; i < n; i++) {
      const px = Math.round(toX(xs[i]));
      const py = toY(ys[i]);
      if (px !== px || py !== py) {
        flush();
        endPiece();
        column = null;
        pen = false;
        continue;
      }
      if (px === column) {
        if (py < low) low = py;
        if (py > high) high = py;
        last = py;
        continue;
      }
      flush();
      column = px;
      first = low = high = last = py;
    }
    flush();
    endPiece();
    return path;
  }

  let lastX = NaN;
  let lastY = NaN;
  for (let i = 0; i < n; i++) {
    const px = Math.round(toX(xs[i]));
    const py = Math.round(toY(ys[i]));
    if (px !== px || py !== py) {
      endPiece();
      pen = false;
      continue;
    }
    if (pen && px === lastX && py === lastY) continue;
    if (pen) {
      path.lineTo(px, py);
      lone = null;
    } else {
      path.moveTo(px, py);
      lone = [px, py];
    }
    pen = true;
    lastX = px;
    lastY = py;
  }
  endPiece();
  return path;
}

// The band between two lines over the same x (a binned trace's lowest and
// highest values), as a Path2D to fill: along the highs and back along the
// lows, in pieces between points with no place on a scale.
export function bandPath(xs, lows, highs, area, x, y) {
  const path = new Path2D();
  const n = Math.min(xs.length, lows.length, highs.length);
  if (n === 0 || x.max === x.min || y.max === y.min) return path;
  const bottom = area.top + area.height;
  const toX = (v) => area.left + unitOf(x, v) * area.width;
  const toY = (v) => bottom - unitOf(y, v) * area.height;
  let piece = [];
  const close = () => {
    if (piece.length > 0) {
      path.moveTo(piece[0][0], piece[0][2]);
      for (const [px, , high] of piece) path.lineTo(px, high);
      for (let i = piece.length - 1; i >= 0; i--) path.lineTo(piece[i][0], piece[i][1]);
      path.closePath();
    }
    piece = [];
  };
  for (let i = 0; i < n; i++) {
    const px = toX(xs[i]);
    const low = toY(lows[i]);
    const high = toY(highs[i]);
    if (px !== px || low !== low || high !== high) close();
    else piece.push([px, low, high]);
  }
  close();
  return path;
}

// A dot of `radius` canvas pixels at each point (xs[i], ys[i]), as a Path2D to
// fill. Like the lines, not every one of hundreds of thousands of points need
// be drawn: the plot is divided into cells the size of a dot's radius, and only
// the first point in each cell gets a dot, which looks the same. A point with no
// place on a scale, or outside the plot, is left out.
export function pointPath(xs, ys, area, x, y, radius) {
  const path = new Path2D();
  const n = Math.min(xs.length, ys.length);
  if (n === 0 || x.max === x.min || y.max === y.min) return path;
  const cell = Math.max(1, radius);
  const columns = Math.ceil(area.width / cell) + 1;
  const rows = Math.ceil(area.height / cell) + 1;
  const taken = new Uint8Array(columns * rows);
  const bottom = area.top + area.height;
  let dots = 0;
  for (let i = 0; i < n; i++) {
    const px = area.left + unitOf(x, xs[i]) * area.width;
    const py = bottom - unitOf(y, ys[i]) * area.height;
    if (!(px >= area.left && px <= area.left + area.width)) continue; // NaN too
    if (!(py >= area.top && py <= bottom)) continue;
    const index =
      Math.floor((py - area.top) / cell) * columns + Math.floor((px - area.left) / cell);
    if (taken[index]) continue;
    taken[index] = 1;
    path.moveTo(px + radius, py);
    path.arc(px, py, radius, 0, 2 * Math.PI);
    dots++;
  }
  path.dots = dots; // how many were drawn, for the tests
  return path;
}

// The index of the value nearest `target` in a column that never goes down, or
// -1 if it has none. NaN values are stepped over.
export function nearestInSorted(xs, target) {
  let low = 0;
  let high = xs.length;
  while (low < high) {
    const mid = (low + high) >> 1;
    let probe = mid; // the first value that is not NaN, from the middle on
    while (probe < high && xs[probe] !== xs[probe]) probe++;
    if (probe === high) high = mid; // only NaN from here: look lower
    else if (xs[probe] < target) low = probe + 1;
    else high = probe;
  }
  let before = low - 1;
  while (before >= 0 && xs[before] !== xs[before]) before--;
  let after = low;
  while (after < xs.length && xs[after] !== xs[after]) after++;
  const candidates = [before, after].filter((i) => i >= 0 && i < xs.length);
  if (candidates.length === 0) return -1;
  return candidates.reduce((best, i) =>
    Math.abs(xs[i] - target) < Math.abs(xs[best] - target) ? i : best,
  );
}

// The index of the point nearest the pixel (px, py), across several y columns
// that share one x column, with `toX` and `toY` giving a value's pixel. Returns
// {index, distance}, index -1 if there is no point.
export function nearestPoint(xs, ysList, px, py, toX, toY) {
  let best = -1;
  let bestSquared = Infinity;
  for (let i = 0; i < xs.length; i++) {
    const dx = toX(xs[i]) - px;
    if (dx !== dx) continue;
    for (const ys of ysList) {
      const dy = toY(ys[i]) - py;
      const squared = dx * dx + dy * dy;
      if (squared < bestSquared) {
        bestSquared = squared;
        best = i;
      }
    }
  }
  return { index: best, distance: Math.sqrt(bestSquared) };
}

// The y extent of the points whose x is within a scale's range, for fitting the
// y axis to what an x zoom leaves in view.
export function extentWithin(xs, ysList, x, { log = false } = {}) {
  const inside = (v) => v >= x.min && v <= x.max;
  let low = Infinity;
  let high = -Infinity;
  for (let i = 0; i < xs.length; i++) {
    if (!inside(xs[i])) continue;
    for (const ys of ysList) {
      const v = ys[i];
      if (log && !(v > 0)) continue;
      if (v < low) low = v;
      if (v > high) high = v;
    }
  }
  return low <= high ? [low, high] : null;
}

// A scale moved along by a fraction of its span (positive: towards higher values).
export function panned(scale, fraction) {
  return { ...scale, min: valueAt(scale, fraction), max: valueAt(scale, 1 + fraction) };
}

// A scale zoomed by a factor (below 1: in) about a place on it, from 0 to 1,
// which stays where it is.
export function zoomedAbout(scale, factor, anchor) {
  return {
    ...scale,
    min: valueAt(scale, anchor - anchor * factor),
    max: valueAt(scale, anchor + (1 - anchor) * factor),
  };
}

// About `count` ticks at round numbers (1, 2, 2.5 or 5 times a power of ten
// apart) between min and max.
export function niceTicks(min, max, count = 5) {
  if (!(max > min)) return [min];
  const rough = (max - min) / count;
  const power = 10 ** Math.floor(Math.log10(rough));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * power).find((s) => s >= rough);
  const ticks = [];
  for (let v = Math.ceil(min / step) * step; v <= max + step * 1e-9; v += step) {
    ticks.push(Number(v.toPrecision(12))); // no 0.30000000000000004
  }
  return ticks;
}

// The ticks of a log axis, and whether they are evenly spaced:
// - less than a decade across: round numbers evenly spaced, as on a linear
//   axis (a log scale is nearly linear over so little);
// - up to three decades: 1, 2 and 5 times each power of ten;
// - more: the powers of ten, every so many if there are too many to label.
export function logTicks(min, max) {
  const decades = Math.log10(max / min);
  if (!(decades >= 1)) return { ticks: niceTicks(min, max), even: true };
  const first = Math.floor(Math.log10(min));
  const last = Math.ceil(Math.log10(max));
  const multiples = decades <= 3 ? [1, 2, 5] : [1];
  const every = Math.max(1, Math.ceil(decades / 8));
  const ticks = [];
  for (let e = first; e <= last; e++) {
    if ((e - first) % every) continue;
    for (const m of multiples) {
      const v = Number((m * 10 ** e).toPrecision(12));
      if (v >= min && v <= max) ticks.push(v);
    }
  }
  return { ticks, even: false };
}

// The labels of an axis's ticks, all in one style: plain for everyday numbers, or
// in exponent form when the axis is very large or small, each with as many digits
// as the spacing between the ticks needs, and no more. A log axis's ticks are
// powers of ten (and steps between them), labelled each on its own.
export function tickLabels(ticks, { log = false } = {}) {
  if (ticks.length === 0) return [];
  // uPlot passes null for a tick it wants left without a label (on a log axis,
  // most of those between the powers of ten).
  if (ticks.some((v) => v === null)) {
    const labels = tickLabels(ticks.filter((v) => v !== null), { log });
    return ticks.map((v) => (v === null ? "" : labels.shift()));
  }
  if (log) {
    return ticks.map((v) =>
      v >= 1e-3 && v < 1e6 ? String(Number(v.toPrecision(6))) : v.toExponential(0),
    );
  }
  const step = ticks.length > 1 ? Math.abs(ticks[1] - ticks[0]) : Math.abs(ticks[0]) || 1;
  const largest = Math.max(...ticks.map(Math.abs), step);
  const magnitude = (v) => Math.floor(Math.log10(v) + 1e-9);
  if (largest >= 1e6 || largest < 1e-3) {
    // Digits after the point of the mantissa: as many as the step needs there.
    const digits = Math.min(6, decimalsFor(step / 10 ** magnitude(largest)));
    return ticks.map((v) => (v === 0 ? "0" : v.toExponential(digits)));
  }
  const decimals = decimalsFor(step);
  return ticks.map((v) => (Math.abs(v) < step / 1e6 ? 0 : v).toFixed(decimals));
}

// The fewest decimals that write a step exactly: 0 for 5, 1 for 2.5 or 0.5, 3
// for 0.002. (Not just from its size: 2.5 needs one, where 2 needs none.)
export function decimalsFor(step) {
  for (let d = 0; d <= 10; d++) {
    const scaled = step * 10 ** d;
    if (Math.abs(scaled - Math.round(scaled)) < 1e-6 * Math.max(1, scaled)) return d;
  }
  return 10;
}
