// The experiment's traces, for the trace and map panels: fetches them, reads
// the binary form, and follows /stream/traces (the protocol in
// core/trace_history.py).
//
// A trace, as parseTraces gives it: its header (seq, name, index, data_file,
// time_start, time, points, binned, length, axis, x_name, x_unit, unit,
// channels, row_start, row, columns), with `x` (a Float64Array) and `values`
// ({channel: {min, max, mean}} when binned, or {channel: {values}}, of
// Float32Arrays, or Float64Arrays at full resolution).
import { getBinary } from "./api.js";
import { startFeed } from "./feed.js";
import { Watched } from "./store.js";

const ARRAYS = { f4: Float32Array, f8: Float64Array };

// The binary form: a uint32 giving the header's length, the header, then each
// trace's arrays where its `blocks` say. Gives the header, with each trace's
// arrays in place of its blocks.
export function parseTraces(buffer) {
  const length = new DataView(buffer).getUint32(0, true);
  const header = JSON.parse(new TextDecoder().decode(new Uint8Array(buffer, 4, length)));
  const start = 4 + length;
  for (const trace of header.traces) {
    trace.x = null;
    trace.values = {};
    for (const block of trace.blocks) {
      const array = new ARRAYS[block.dtype](buffer, start + block.offset, block.length);
      if (block.part === "x") trace.x = array;
      else (trace.values[block.channel] ??= {})[block.part] = array;
    }
    delete trace.blocks;
  }
  return header;
}

const path = (name, what) => `/traces/${encodeURIComponent(name)}/${what}`;

// The trace's latest, thinned (or every point, with `full`), as {seq, traces:
// [it]}. Its request waits as long as a large trace may take.
export async function fetchLatest(name, { full = false } = {}) {
  const params = { format: "binary", ...(full ? { full: "true" } : {}) };
  return parseTraces(await getBinary(path(name, "latest"), { params, timeout: 60000 }));
}

// The trace's recent traces, oldest first, or only those after event `after`.
export async function fetchHistory(name, { after } = {}) {
  const params = { format: "binary", ...(after !== undefined ? { after } : {}) };
  return parseTraces(await getBinary(path(name, "history"), { params, timeout: 60000 }));
}

const bytes = (trace) =>
  trace.x.byteLength +
  Object.values(trace.values)
    .flatMap((parts) => Object.values(parts))
    .reduce((sum, array) => sum + array.byteLength, 0);

// One trace's recent traces, kept as the server keeps them (those of the
// current data file and the one before, and the latest, within the budget),
// and followed as they are taken. Components watch it with useStore.
export class TraceStore extends Watched {
  constructor(name) {
    super();
    this.name = name;
    this.seq = 0; // the last event applied
    this.traces = []; // oldest first
    this.files = [null, null]; // the previous data file, and the current one
    this.budget = Infinity; // bytes
    this.fetching = Promise.resolve();
  }

  get latest() {
    return this.traces.at(-1) ?? null;
  }

  // Replaces everything with a snapshot (fetchHistory's).
  load(snapshot) {
    this.seq = snapshot.seq;
    this.traces = snapshot.traces;
    this.files = [snapshot.previous_file, snapshot.file];
    this.budget = snapshot.budget_mb * 1e6;
    this.changed();
  }

  // Applies an event from the stream: false if one was missed.
  apply(event) {
    if (event.seq <= this.seq) return true; // already in the snapshot
    if (event.seq !== this.seq + 1) return false;
    this.seq = event.seq;
    if (event.type === "trace" && event.name === this.name) this.fetchNew();
    else if (event.type === "new_file") this.newFile(event.file);
    return true;
  }

  // Fetches the traces stored since the last held, one fetch after another,
  // so each comes once and in order. One that fails is fetched with the next.
  fetchNew() {
    this.fetching = this.fetching.then(async () => {
      try {
        const after = this.latest?.seq ?? 0;
        const { traces } = await fetchHistory(this.name, { after });
        const known = this.latest?.seq ?? 0;
        const fresh = traces.filter((trace) => trace.seq > known);
        if (!fresh.length) return;
        this.traces.push(...fresh);
        this.limit();
        this.changed();
      } catch {
        // Missed for now: the next trace's fetch takes it too.
      }
    });
    return this.fetching;
  }

  newFile(file) {
    if (file !== this.files[1]) this.files = [this.files[1], file];
    const latest = this.latest;
    const kept = this.traces.filter(
      (trace) => this.files.includes(trace.data_file) || trace === latest,
    );
    if (kept.length !== this.traces.length) {
      this.traces = kept;
      this.changed();
    }
  }

  // Past the budget, the oldest go first, but never the latest.
  limit() {
    let total = this.traces.reduce((sum, trace) => sum + bytes(trace), 0);
    while (total > this.budget && this.traces.length > 1) {
      total -= bytes(this.traces.shift());
    }
  }
}

// Follows a trace: /stream/traces after a /traces/<name>/history snapshot.
export const traceFeed = (store, options) =>
  startFeed(store, {
    ...options,
    stream: "/stream/traces",
    snapshot: () => fetchHistory(store.name),
  });
