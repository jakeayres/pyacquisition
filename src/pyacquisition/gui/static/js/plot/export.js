// Exporting a plot: as an image of what it shows (the plot and its axes, as
// drawn, with a legend above), or as the data in view (the rows whose x is on
// the x axis now, of the columns it plots) in a CSV file. The third export, a
// Python script, is written by the server (/experiment/plot_script) from
// `scriptSettings`.
//
// In the app's window the file is saved where a Save dialog says (the window
// doesn't download); in a browser it downloads.

const LEGEND_ROW = 26; // css pixels for a line of the legend
const KEY_LENGTH = 18; // the stroke of colour before each name
const GAP = 16; // between one entry and the next

const cssValue = (name) =>
  getComputedStyle(document.documentElement).getPropertyValue(name).trim();

export const colourOf = (slot) => cssValue(slot ? `--series-${slot}` : "--series-other");
const withUnit = (name, units) => (units[name] ? `${name} (${units[name]})` : name);

// Where a legend's entries go: rows of [{text, x}], as wide as `width`.
function legendRows(ctx, entries, width) {
  const rows = [[]];
  let x = 0;
  for (const entry of entries) {
    const w = KEY_LENGTH + 6 + ctx.measureText(entry.text).width;
    if (x > 0 && x + w > width) {
      rows.push([]);
      x = 0;
    }
    rows.at(-1).push({ ...entry, x });
    x += w + GAP;
  }
  return rows;
}

// The plot as an image: its canvas (the plot and axes, as drawn, at the screen's
// resolution) on the page's background, under a legend of what is shown.
// Resolves to a PNG blob.
export function plotImage(u, { series, units }) {
  const source = u.ctx.canvas;
  const ratio = source.width / u.width; // device pixels to a css pixel
  const shown = series.filter((s) => !s.hidden);
  const font = `12px ${cssValue("--font-sans")}`;

  const measure = document.createElement("canvas").getContext("2d");
  measure.font = font;
  const entries = shown.map((s) => ({ text: withUnit(s.name, units), colour: colourOf(s.slot) }));
  const pad = 12;
  const rows = legendRows(measure, entries, u.width - 2 * pad);
  const legend = rows.length * LEGEND_ROW + pad;

  const canvas = document.createElement("canvas");
  canvas.width = source.width;
  canvas.height = source.height + Math.round(legend * ratio);
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = cssValue("--bg");
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  ctx.save();
  ctx.scale(ratio, ratio);
  ctx.font = font;
  ctx.textBaseline = "middle";
  rows.forEach((row, r) => {
    const y = pad + r * LEGEND_ROW + LEGEND_ROW / 2;
    for (const entry of row) {
      ctx.strokeStyle = entry.colour;
      ctx.lineWidth = 2;
      ctx.lineCap = "round";
      ctx.beginPath();
      ctx.moveTo(pad + entry.x, y);
      ctx.lineTo(pad + entry.x + KEY_LENGTH, y);
      ctx.stroke();
      ctx.fillStyle = cssValue("--text");
      ctx.fillText(entry.text, pad + entry.x + KEY_LENGTH + 6, y);
    }
  });
  ctx.restore();

  ctx.drawImage(source, 0, Math.round(legend * ratio));
  return new Promise((resolve, reject) =>
    canvas.toBlob((blob) => (blob ? resolve(blob) : reject(new Error("no image"))), "image/png"),
  );
}

// A field as CSV has it: quoted if it holds a comma, a quote or a line break.
const field = (text) => (/[",\r\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text);

// The rows in view as CSV text: those whose x is within `range` ({min, max}),
// with x first and then each series shown. With the previous file shown too,
// its rows come first, and a first column names each row's file.
export function viewCsv(store, { x, series, units, showPrevious, range }) {
  const columns = [x, ...series.filter((s) => !s.hidden).map((s) => s.name).filter((n) => n !== x)];
  const segments = showPrevious && store.previous ? [store.previous, store.current] : [store.current];
  const withFile = segments.length > 1;
  const lines = [
    [...(withFile ? ["file"] : []), ...columns.map((c) => withUnit(c, units))].map(field).join(","),
  ];
  for (const segment of segments) {
    const xs = segment.column(x);
    if (!xs) continue;
    const values = columns.map((c) => segment.column(c));
    for (let i = 0; i < segment.rows; i++) {
      const v = xs[i];
      if (!(v >= range.min && v <= range.max)) continue; // off the axis, or no value
      const row = values.map((col) => (col && Number.isFinite(col[i]) ? String(col[i]) : ""));
      lines.push([...(withFile ? [field(segment.file ?? "")] : []), ...row].join(","));
    }
  }
  return `${lines.join("\r\n")}\r\n`;
}

// A colour as #rrggbb, however the theme writes it: a canvas gives an opaque
// colour back in that form.
function hexColour(colour) {
  const ctx = document.createElement("canvas").getContext("2d");
  ctx.fillStyle = "#000000";
  ctx.fillStyle = colour;
  return ctx.fillStyle;
}

// The plot's settings, as /experiment/plot_script takes them: the series shown,
// each in its colour on screen, and both axes' ranges as they show now
// (`scales`) if either axis is `held` (by a zoom, a pan or fixed limits), or
// neither, to fit the data.
export function scriptSettings({ x, series, marks, logX, logY, showPrevious }, scales, held) {
  const range = (axis) => (held ? [scales[axis].min, scales[axis].max] : null);
  return {
    x,
    series: series
      .filter((s) => !s.hidden)
      .map((s) => ({ name: s.name, colour: hexColour(colourOf(s.slot)) })),
    marks: marks ?? "lines",
    log_x: !!logX,
    log_y: !!logY,
    x_limits: range("x"),
    y_limits: range("y"),
    previous: !!showPrevious,
  };
}

// A file name from what the plot shows, without characters a file can't have.
export function exportName(store, { x, series }, extension) {
  const file = (store.current.file ?? "plot").replace(/\.[^.]+$/, "");
  const shown = series.filter((s) => !s.hidden).map((s) => s.name);
  const name = `${file} - ${shown.join(", ")} vs ${x}`.replace(/[<>:"/\\|?*]/g, "_");
  return `${name}.${extension}`;
}

function base64Of(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result).split(",", 2)[1]);
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(blob);
  });
}

// The media type of a downloaded text file, by its extension.
const MEDIA_TYPES = { csv: "text/csv", py: "text/x-python" };

// Saves text or a blob as a file called `name`. In the app's window, a Save
// dialog asks where; it resolves to where it went, or null if cancelled. In a
// browser, it downloads, and resolves to the name.
export async function saveFile(name, content) {
  const api = window.pywebview?.api;
  if (api?.save_file) {
    return typeof content === "string"
      ? api.save_file(name, content, null)
      : api.save_file(name, null, await base64Of(content));
  }
  const type = MEDIA_TYPES[name.split(".").pop().toLowerCase()] ?? "text/plain";
  const blob =
    typeof content === "string" ? new Blob([content], { type: `${type};charset=utf-8` }) : content;
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = name;
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(link.href), 10000);
  return name;
}
