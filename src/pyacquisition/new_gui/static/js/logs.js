// The log messages, kept in the page for as long as it is open, whichever tab is
// showing: a /logs/history snapshot, then each entry from /stream/logs (feed.js).
import { Watched } from "./store.js";

// Every level the logger has, least severe first.
export const LEVELS = ["trace", "debug", "info", "warning", "error", "exception"];

export class LogStore extends Watched {
  constructor() {
    super();
    this.seq = 0;
    this.maxEntries = Infinity;
    this.entries = []; // oldest first
    this.status = "connecting";
  }

  load(snapshot) {
    this.seq = snapshot.seq;
    this.maxEntries = snapshot.max_entries ?? Infinity;
    this.entries = snapshot.entries.map(prepare);
    this.changed();
  }

  // Adds one entry from the stream. Returns false if one was missed, so the
  // caller can load a fresh snapshot.
  apply(entry) {
    if (entry.seq <= this.seq) return true; // already in the snapshot
    if (entry.seq !== this.seq + 1) return false;
    this.seq = entry.seq;
    this.entries.push(prepare(entry));
    // As the server does, keeping the last maxEntries, but trimmed a few at a
    // time rather than for every entry. Trimmed into a new list, so the one the
    // Logs tab last drew keeps its rows where they were until it draws again.
    const excess = this.entries.length - this.maxEntries;
    if (excess > 0) {
      this.entries = this.entries.slice(excess + Math.floor(this.maxEntries / 100));
    }
    this.changed();
    return true;
  }
}

// An entry, with its message split into the component that logged it (the
// "[Rack]" that starts most messages) and the rest, and lower-cased for search.
function prepare(entry) {
  const match = /^\[([^\]]{1,40})\]\s*/.exec(entry.message);
  return {
    ...entry,
    source: match ? match[1] : null,
    text: match ? entry.message.slice(match[0].length) : entry.message,
    lower: entry.message.toLowerCase(),
  };
}
