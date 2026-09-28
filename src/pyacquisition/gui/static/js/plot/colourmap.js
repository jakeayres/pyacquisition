// Drawing a colour map: rows of values, each over its own x values and its own
// band of y, coloured by a colour scale, with a colour bar to read it by.
//
// It is written for any map of this kind, not only the map panel's traces
// (map-panel.js): the 2D sweep map of roadmap 4 is meant to use it too. The
// functions are plain ones of the data, so they can be tested alone, and the
// drawing fills an image a pixel at a time, which is quick for the hundreds of
// rows and thousands of points a map may have.
//
// A scale is what an axis shows, `{min, max, log}` (as in draw.js). The colour
// scale is one too: a value's place on it picks its colour.
import { unitOf, valueAt } from "./draw.js";

// The colour maps, as evenly spaced stops from the lowest value to the highest:
// two perceptual ones, and a diverging one for values either side of a middle.
export const COLOUR_MAPS = {
  viridis: ["#440154", "#472d7b", "#3b528b", "#2c728e", "#21918c", "#28ae80", "#5ec962", "#addc30", "#fde725"],
  magma: ["#000004", "#1c1044", "#4f127b", "#812581", "#b5367a", "#e55064", "#fb8761", "#fec287", "#fcfdbf"],
  coolwarm: ["#3b4cc0", "#6282ea", "#8db0fe", "#b8d0f9", "#dddddd", "#f5c4ad", "#f49a7b", "#de604d", "#b40426"],
};

const STEPS = 256;
const tables = new Map();

const rgb = (hex) => [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16));

// A colour map's 256 colours, as the 32-bit pixels of an ImageData (red in the
// lowest byte, and opaque).
export function colourTable(name) {
  if (tables.has(name)) return tables.get(name);
  const stops = (COLOUR_MAPS[name] ?? COLOUR_MAPS.viridis).map(rgb);
  const table = new Uint32Array(STEPS);
  for (let i = 0; i < STEPS; i++) {
    const at = (i / (STEPS - 1)) * (stops.length - 1);
    const k = Math.min(stops.length - 2, Math.floor(at));
    const f = at - k;
    const [r, g, b] = stops[k].map((c, j) => Math.round(c + f * (stops[k + 1][j] - c)));
    table[i] = (255 << 24) | (b << 16) | (g << 8) | r;
  }
  tables.set(name, table);
  return table;
}

// A pixel of the table as CSS, for the tests and the exported image.
export const pixelColour = (pixel) =>
  `rgb(${pixel & 255}, ${(pixel >>> 8) & 255}, ${(pixel >>> 16) & 255})`;

// Where a value falls on a colour scale, from 0 to 1 (clamped at the ends), or
// NaN if it has none (NaN, or not above zero on a log scale).
export function colourUnit(scale, value) {
  const u = unitOf(scale, value);
  if (u !== u) return NaN;
  return u < 0 ? 0 : u > 1 ? 1 : u;
}

// The pixel for a value, or 0 (transparent) if it has no colour.
export function colourOf(table, scale, value) {
  const u = colourUnit(scale, value);
  return u === u ? table[Math.round(u * (STEPS - 1))] : 0;
}

// The lowest and highest value across some rows' values that a colour scale can
// show (NaN skipped, and not above zero on a log one), or null.
export function valueRange(rows, { log = false } = {}) {
  let low = Infinity;
  let high = -Infinity;
  for (const { values } of rows) {
    for (let i = 0; i < values.length; i++) {
      const v = values[i];
      if (log && !(v > 0)) continue;
      if (v < low) low = v;
      if (v > high) high = v;
    }
  }
  if (!(low <= high)) return null;
  if (low === high) return log ? [low / 2, high * 2] : [low - (Math.abs(low) || 1), high + (Math.abs(high) || 1)];
  return [low, high];
}

// The band of y each row covers, as [low, high], in the order given: halfway to
// the rows either side of it (in y), so uneven steps draw true, but reaching no
// further than the median step on either side, so a long pause shows as a gap
// rather than one tall band. An end row reaches as far out as it does in. Rows
// at the same y share a band (the one drawn last shows). On a log scale this is
// worked out in powers of ten.
export function strips(ys, { log = false } = {}) {
  const to = log ? Math.log10 : (v) => v;
  const from = log ? (v) => 10 ** v : (v) => v;
  const values = Array.from(ys, to);
  const distinct = [...new Set(values.filter((v) => Number.isFinite(v)))].sort((a, b) => a - b);
  const steps = distinct.slice(1).map((v, i) => v - distinct[i]);
  const median = steps.length ? [...steps].sort((a, b) => a - b)[Math.floor(steps.length / 2)] : 0;
  const lone = Math.abs(distinct[0] ?? 0) * 0.05 || 0.5; // one y only: a band this wide
  const bands = new Map();
  distinct.forEach((v, i) => {
    let below = i > 0 ? Math.min((v - distinct[i - 1]) / 2, median) : null;
    let above = i < distinct.length - 1 ? Math.min((distinct[i + 1] - v) / 2, median) : null;
    if (below === null && above === null) below = above = lone;
    below ??= above;
    above ??= below;
    bands.set(v, [from(v - below), from(v + above)]);
  });
  return values.map((v) => bands.get(v) ?? null);
}

// One pixel row of a map row: the colour of the value nearest each pixel
// column's centre (`centres`, the x values, rising), within the row's own x
// range (halfway beyond its first and last point), and transparent outside it.
function fillLine(line, centres, xs, values, table, colour) {
  const n = Math.min(xs.length, values.length);
  line.fill(0);
  if (n === 0) return;
  const falling = n > 1 && xs[0] > xs[n - 1];
  const at = falling ? (i) => n - 1 - i : (i) => i;
  const first = xs[at(0)];
  const last = xs[at(n - 1)];
  const low = n > 1 ? first - (xs[at(1)] - first) / 2 : first - (Math.abs(first) * 0.005 || 0.5);
  const high = n > 1 ? last + (last - xs[at(n - 2)]) / 2 : last + (Math.abs(last) * 0.005 || 0.5);
  let j = 0;
  for (let c = 0; c < centres.length; c++) {
    const v = centres[c];
    if (!(v >= low && v <= high)) continue;
    while (j < n - 1 && Math.abs(xs[at(j + 1)] - v) <= Math.abs(xs[at(j)] - v)) j++;
    line[c] = colourOf(table, colour, values[at(j)]);
  }
}

// Draws a map on a canvas's 2D context, within `area` (in canvas pixels):
// `rows` are {x, values, low, high} (each over its own x, from low to high in
// y), drawn in order, so a later one covers an earlier one where they meet;
// `x`, `y` and `colour` are the scales; `table` a colour table. Gives the
// number of rows drawn.
export function drawMap(ctx, area, rows, { x, y, colour, table }) {
  const width = Math.max(1, Math.round(area.width));
  const height = Math.max(1, Math.round(area.height));
  const image = new ImageData(width, height);
  const pixels = new Uint32Array(image.data.buffer);
  const line = new Uint32Array(width);
  const centres = new Float64Array(width);
  for (let c = 0; c < width; c++) centres[c] = valueAt(x, (c + 0.5) / width); // x.min < x.max
  let drawn = 0;
  for (const row of rows) {
    let top = Math.round((1 - unitOf(y, row.high)) * height);
    let bottom = Math.round((1 - unitOf(y, row.low)) * height);
    if (top !== top || bottom !== bottom) continue; // no place on a log scale
    if (bottom <= top) bottom = top + 1; // a row always shows, if only as a line
    top = Math.max(0, top);
    bottom = Math.min(height, bottom);
    if (top >= bottom) continue;
    fillLine(line, centres, row.x, row.values, table, colour);
    for (let r = top; r < bottom; r++) pixels.set(line, r * width);
    drawn++;
  }
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  canvas.getContext("2d").putImageData(image, 0, 0);
  ctx.drawImage(canvas, area.left, area.top);
  return drawn;
}

// A colour bar: the table from bottom (lowest) to top, filling a canvas.
export function drawColourBar(canvas, table) {
  const { width, height } = canvas;
  if (!width || !height) return;
  const image = new ImageData(width, height);
  const pixels = new Uint32Array(image.data.buffer);
  for (let r = 0; r < height; r++) {
    const pixel = table[Math.round((1 - r / Math.max(1, height - 1)) * (STEPS - 1))];
    pixels.fill(pixel, r * width, (r + 1) * width);
  }
  canvas.getContext("2d").putImageData(image, 0, 0);
}
