// The Values tab: a tile for each column, with its latest value and unit, where
// it comes from, and a small graph of it over the current data file.
import { useRef } from "preact/hooks";
import { html } from "../html.js";
import { useStore } from "../hooks.js";
import { exactValue, formatValue } from "../format.js";
import { colourSlots, colourVar } from "../colours.js";

const SPARK_BUCKETS = 120; // the graph's resolution, across its width
const SPARK_REFRESH = 1000; // milliseconds between redraws of a long graph
const SPARK_RAW = 2 * SPARK_BUCKETS; // below this many points, draw each one

// The graph's path, in a 100 x 24 box. A long column is drawn as the lowest and
// highest value in each of SPARK_BUCKETS slices, so that no spike is lost.
export function sparkPath(values) {
  const points = [];
  const n = values.length;
  if (n < 2) return "";
  if (n <= SPARK_RAW) {
    for (let i = 0; i < n; i++) points.push([i / (n - 1), values[i]]);
  } else {
    for (let b = 0; b < SPARK_BUCKETS; b++) {
      const start = Math.floor((b * n) / SPARK_BUCKETS);
      const end = Math.floor(((b + 1) * n) / SPARK_BUCKETS);
      let low = Infinity;
      let high = -Infinity;
      for (let i = start; i < end; i++) {
        const v = values[i];
        if (v < low) low = v;
        if (v > high) high = v;
      }
      if (low === Infinity) continue; // all NaN
      const x = (b + 0.5) / SPARK_BUCKETS;
      points.push([x, low], [x, high]);
    }
  }
  let low = Infinity;
  let high = -Infinity;
  for (const [, y] of points) {
    if (y < low) low = y;
    if (y > high) high = y;
  }
  if (low === Infinity) return "";
  const span = high - low || 1;
  let path = "";
  let drawing = false;
  for (const [x, y] of points) {
    if (Number.isNaN(y)) {
      drawing = false; // a gap where there is no value
      continue;
    }
    const px = (x * 100).toFixed(2);
    const py = (22 - ((y - low) / span) * 20).toFixed(2);
    path += `${drawing ? "L" : "M"}${px} ${py}`;
    drawing = true;
  }
  return path;
}

function Sparkline({ values }) {
  // A long graph is redrawn once a second, not on every new value.
  const cache = useRef({ path: "", time: 0, rows: 0 });
  const now = performance.now();
  const rows = values ? values.length : 0;
  const stale =
    rows < cache.current.rows || // a new file started
    rows <= SPARK_RAW ||
    now - cache.current.time > SPARK_REFRESH;
  if (stale) cache.current = { path: values ? sparkPath(values) : "", time: now, rows };
  return html`
    <svg class="spark" viewBox="0 0 100 24" preserveAspectRatio="none" aria-hidden="true">
      <path d=${cache.current.path} vector-effect="non-scaling-stroke" />
    </svg>
  `;
}

// A tile's colour is its quantity's (colours.js): on the key beside its name and
// its graph, never on the text, which stays readable in every colour.
function ValueTile({ name, info, value, values, colour }) {
  const numeric = typeof value === "number" || value === null;
  return html`
    <div class="value-tile" data-column=${name} style=${{ "--quantity": colour }}>
      <div class="value-head">
        <span class="value-key" aria-hidden="true"></span>
        <span class="value-name">${name}</span>
        ${info?.source && html`<span class="value-source">${info.source}</span>`}
      </div>
      <div class="value-reading" title=${exactValue(value)}>
        <span class="value-number ${numeric ? "" : "value-text"}">${formatValue(value)}</span>
        ${info?.unit && html`<span class="value-unit">${info.unit}</span>`}
      </div>
      ${values && html`<${Sparkline} values=${values} />`}
    </div>
  `;
}

// The columns to show: those described by the experiment, in its order, then
// any others that have arrived.
function columnOrder(info, latest) {
  const names = info.map((column) => column.name);
  for (const name of Object.keys(latest)) {
    if (!names.includes(name)) names.push(name);
  }
  return names;
}

export function ValuesTab({ store, columns }) {
  useStore(store);
  const info = columns ?? [];
  const names = columnOrder(info, store.latest);
  if (names.length === 0) {
    return html`<p class="placeholder">Waiting for data…</p>`;
  }
  const byName = Object.fromEntries(info.map((column) => [column.name, column]));
  const slots = colourSlots(store.columns);
  return html`
    <div class="value-grid">
      ${names.map(
        (name) => html`
          <${ValueTile}
            key=${name}
            name=${name}
            info=${byName[name]}
            value=${store.latest[name]}
            values=${store.current.column(name)}
            colour=${colourVar(slots.get(name) ?? null)}
          />
        `,
      )}
    </div>
  `;
}
