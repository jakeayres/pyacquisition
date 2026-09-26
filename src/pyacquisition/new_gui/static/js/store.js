// The data, as the experiment's history keeps it: the current data file and the
// one before it, each column a Float64Array (NaN where there is no value).
//
// It is filled from a /history snapshot, then kept up to date with the events of
// /stream/data, following the protocol in core/history.py. Listeners are told of
// changes at most once per animation frame.

const MIN_CAPACITY = 1024;

class Segment {
  constructor(file = null) {
    this.file = file;
    this.rows = 0;
    this.capacity = 0;
    this.buffers = new Map(); // name -> Float64Array, longer than `rows`
  }

  static fromSnapshot({ file, rows, data }) {
    const segment = new Segment(file);
    segment.reserve(rows);
    for (const [name, values] of Object.entries(data)) {
      const buffer = segment.newBuffer();
      buffer.set(values);
      segment.buffers.set(name, buffer);
    }
    segment.rows = rows;
    return segment;
  }

  get names() {
    return [...this.buffers.keys()];
  }

  // A column's values, without the spare room after them.
  column(name) {
    const buffer = this.buffers.get(name);
    return buffer ? buffer.subarray(0, this.rows) : null;
  }

  newBuffer() {
    return new Float64Array(this.capacity).fill(NaN);
  }

  reserve(rows) {
    if (rows <= this.capacity) return;
    this.capacity = Math.max(MIN_CAPACITY, rows, this.capacity * 2);
    for (const [name, old] of this.buffers) {
      const grown = this.newBuffer();
      grown.set(old.subarray(0, this.rows));
      this.buffers.set(name, grown);
    }
  }

  // `numbers` holds only the row's numeric values; a column it leaves out gets
  // NaN, and a new column is NaN for the rows before it.
  append(numbers) {
    this.reserve(this.rows + 1);
    for (const name of Object.keys(numbers)) {
      if (!this.buffers.has(name)) this.buffers.set(name, this.newBuffer());
    }
    for (const [name, buffer] of this.buffers) {
      buffer[this.rows] = name in numbers ? numbers[name] : NaN;
    }
    this.rows += 1;
  }

  dropOldest(count) {
    for (const buffer of this.buffers.values()) {
      buffer.copyWithin(0, count, this.rows);
      buffer.fill(NaN, this.rows - count, this.rows);
    }
    this.rows -= count;
  }
}

// The binary form of /history (see core/history.py): a little-endian uint32
// header length, the JSON header, then each segment's columns as float64s.
export function parseSnapshot(buffer) {
  const length = new DataView(buffer).getUint32(0, true);
  const header = JSON.parse(new TextDecoder().decode(new Uint8Array(buffer, 4, length)));
  let offset = 4 + length;
  for (const segment of header.segments) {
    segment.data = {};
    for (const name of segment.columns) {
      segment.data[name] = new Float64Array(buffer, offset, segment.rows);
      offset += 8 * segment.rows;
    }
  }
  return header;
}

// A value from the stream as a number for a column, or undefined if it is not
// one. A bool counts, as the server stores it. null is a missing number.
function asNumber(value) {
  if (typeof value === "number") return value;
  if (typeof value === "boolean") return value ? 1 : 0;
  return undefined;
}

export class DataStore {
  constructor() {
    this.seq = 0;
    this.maxRows = Infinity;
    this.latest = {}; // the last value of every column, numeric or not
    this.previous = null;
    this.current = new Segment();
    this.version = 0; // goes up with every change
    this.listeners = new Set();
    this.frame = null;
  }

  get segments() {
    return this.previous ? [this.previous, this.current] : [this.current];
  }

  // Every numeric column, in the order they first appeared.
  get columns() {
    const names = new Set();
    for (const segment of this.segments) segment.names.forEach((n) => names.add(n));
    return [...names];
  }

  // Replaces everything with a snapshot (parsed by parseSnapshot).
  load(snapshot) {
    this.seq = snapshot.seq;
    this.maxRows = snapshot.max_rows ?? Infinity;
    this.latest = { ...snapshot.latest };
    const segments = snapshot.segments.map((s) => Segment.fromSnapshot(s));
    this.current = segments.pop() ?? new Segment();
    this.previous = segments.pop() ?? null;
    this.changed();
  }

  // Applies one event from the stream. Returns false if an event was missed,
  // so the caller can load a fresh snapshot.
  apply(event) {
    if (event.seq <= this.seq) return true; // already in the snapshot
    if (event.seq !== this.seq + 1) return false;
    this.seq = event.seq;

    if (event.type === "new_file") {
      if (this.current.rows > 0) {
        this.previous = this.current;
        this.current = new Segment(event.file);
      } else {
        this.current.file = event.file;
      }
    } else if (event.type === "row") {
      const numbers = {};
      for (const [name, value] of Object.entries(event.values)) {
        const number = asNumber(value);
        if (number !== undefined) numbers[name] = number;
        // null only fills a column that already exists, as on the server.
        else if (value === null && this.hasColumn(name)) numbers[name] = NaN;
      }
      this.current.append(numbers);
      Object.assign(this.latest, event.values);
      this.limit();
    }
    this.changed();
    return true;
  }

  hasColumn(name) {
    return this.current.buffers.has(name);
  }

  // As the server does: past maxRows, drop the oldest down to 99% of it, from
  // the previous file first.
  limit() {
    let excess = this.previousRows() + this.current.rows - this.maxRows;
    if (excess <= 0) return;
    excess += Math.max(1, Math.floor(this.maxRows / 100));
    for (const segment of this.segments) {
      const dropped = Math.min(excess, segment.rows);
      segment.dropOldest(dropped);
      excess -= dropped;
    }
    if (this.previous && this.previous.rows === 0) this.previous = null;
  }

  previousRows() {
    return this.previous ? this.previous.rows : 0;
  }

  subscribe(listener) {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  changed() {
    this.version += 1;
    if (this.frame !== null) return;
    this.frame = requestAnimationFrame(() => {
      this.frame = null;
      for (const listener of this.listeners) listener(this);
    });
  }
}
