// The Logs tab: every message kept, newest at the bottom, with its time, level
// and the component that logged it. Levels can be hidden, and the messages
// searched. The list follows new messages while it is at the bottom, and holds
// still once scrolled up, until it is scrolled back down or "Latest" is pressed.
//
// Only the rows in view are in the page (each is one line, of a fixed height),
// so a long, busy log costs no more to show than a short one. A row that is cut
// short is shown whole when clicked.
import { useEffect, useLayoutEffect, useRef, useState } from "preact/hooks";
import { html } from "../html.js";
import { useStore } from "../hooks.js";
import { load, save } from "../session.js";
import { LEVELS } from "../logs.js";
import { ArrowDownIcon, CloseIcon, CopyIcon, SearchIcon } from "../icons.js";

const OVERSCAN = 10; // rows drawn beyond each edge of the view
// Filter buttons shown even with no messages at that level yet. Trace and
// exception appear once there are some.
const ALWAYS_SHOWN = ["debug", "info", "warning", "error"];
const LABELS = {
  trace: "Trace",
  debug: "Debug",
  info: "Info",
  warning: "Warning",
  error: "Error",
  exception: "Exception",
};
// Keys that scroll the list up, and so stop it following.
const UP_KEYS = new Set(["ArrowUp", "PageUp", "Home"]);

const pad = (n, width = 2) => String(n).padStart(width, "0");

// A message to show, asked for from elsewhere (the palette's "Go to the last
// error"): the Logs tab shows it whole, in view, once it is open, which may be
// after it is asked for.
let wanted = null;

export function showLog(seq) {
  wanted = seq;
  window.dispatchEvent(new CustomEvent("pyacquisition:show-log", { detail: { seq } }));
}

// A message's time of day, to the millisecond, in the local time zone.
export function logTime(seconds) {
  const d = new Date(seconds * 1000);
  return (
    `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}` +
    `.${pad(d.getMilliseconds(), 3)}`
  );
}

function rowHeight() {
  const value = getComputedStyle(document.documentElement).getPropertyValue(
    "--log-row-height",
  );
  return parseFloat(value) || 22;
}

// The entries to show: those at a level not hidden, whose message has the query
// (already lower-cased) in it.
function filterEntries(entries, hidden, query) {
  if (hidden.length === 0 && !query) return entries;
  return entries.filter(
    (entry) => !hidden.includes(entry.level) && (!query || entry.lower.includes(query)),
  );
}

function countLevels(entries) {
  const counts = Object.fromEntries(LEVELS.map((level) => [level, 0]));
  for (const entry of entries) counts[entry.level] += 1;
  return counts;
}

// The index of the first entry numbered `seq` or later (entries are in order).
function firstFrom(entries, seq) {
  let low = 0;
  let high = entries.length;
  while (low < high) {
    const middle = (low + high) >> 1;
    if (entries[middle].seq < seq) low = middle + 1;
    else high = middle;
  }
  return low;
}

// The text, with each match of the query marked.
function highlight(text, query) {
  if (!query) return text;
  const lower = text.toLowerCase();
  const parts = [];
  let from = 0;
  for (let at = lower.indexOf(query); at !== -1; at = lower.indexOf(query, from)) {
    if (at > from) parts.push(text.slice(from, at));
    parts.push(html`<mark>${text.slice(at, at + query.length)}</mark>`);
    from = at + query.length;
  }
  parts.push(text.slice(from));
  return parts;
}

function LevelBadge({ level }) {
  return html`<span class="log-level" data-level=${level}>${LABELS[level]}</span>`;
}

function LogRow({ entry, top, query, selected, onSelect }) {
  const date = new Date(entry.time * 1000);
  return html`
    <div
      class="log-row ${selected ? "selected" : ""}"
      data-level=${entry.level}
      data-seq=${entry.seq}
      role="listitem"
      style=${{ transform: `translateY(${top}px)` }}
      title=${entry.message}
      onClick=${() => onSelect(selected ? null : entry.seq)}
    >
      <time class="log-time" datetime=${date.toISOString()}>${logTime(entry.time)}</time>
      <${LevelBadge} level=${entry.level} />
      ${entry.source &&
      html`<span class="log-source">${highlight(entry.source, query)}</span>`}
      <span class="log-message">${highlight(entry.text, query)}</span>
    </div>
  `;
}

// The selected message in full, under the list.
function LogDetail({ entry, onClose }) {
  const [copied, setCopied] = useState(false);
  useEffect(() => setCopied(false), [entry.seq]);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(entry.message);
      setCopied(true);
    } catch {
      // Not allowed here; the text can still be selected and copied by hand.
    }
  };
  return html`
    <div class="log-detail" role="region" aria-label="Log message">
      <div class="log-detail-head">
        <time class="log-time">${new Date(entry.time * 1000).toLocaleString()}</time>
        <${LevelBadge} level=${entry.level} />
        <div class="log-detail-actions">
          <button class="icon-button" aria-label="Copy the message" title="Copy" onClick=${copy}>
            <${CopyIcon} />
          </button>
          ${copied && html`<span class="log-copied" role="status">Copied</span>`}
          <button class="icon-button" aria-label="Close the message" title="Close" onClick=${onClose}>
            <${CloseIcon} />
          </button>
        </div>
      </div>
      <p class="log-detail-message">${entry.message}</p>
    </div>
  `;
}

export function LogsTab({ store }) {
  useStore(store);
  const [saved] = useState(() => load("logs", {}));
  const [hidden, setHidden] = useState(saved.hidden ?? []);
  const [query, setQuery] = useState(saved.query ?? "");
  const [selected, setSelected] = useState(null); // the seq of the entry shown whole
  const [view, setView] = useState({ top: 0, height: 0 });
  const [following, setFollowing] = useState(true);
  const [row] = useState(rowHeight);
  const list = useRef(null);
  // While held (not following): the first row in view, as {seq, index}, so that
  // it stays put when rows above it are trimmed or filtered out.
  const anchor = useRef(null);
  // A pointer is down on the list (dragging its scroll bar, say): it is not
  // scrolled for the user meanwhile.
  const pressed = useRef(false);

  useLayoutEffect(() => save("logs", { hidden, query }), [hidden, query]);

  // A message asked for (showLog): the filters that would hide it are cleared,
  // and it is shown whole and scrolled into the middle of the list, held there.
  const scrollTo = useRef(null); // the index of a row to bring into view
  const showRef = useRef(null);
  showRef.current = (seq) => {
    const index = firstFrom(store.entries, seq);
    if (store.entries[index]?.seq !== seq) return; // trimmed
    wanted = null;
    setHidden([]);
    setQuery("");
    setSelected(seq);
    anchor.current = { seq, index };
    scrollTo.current = index;
    setFollowing(false);
  };
  useEffect(() => {
    if (wanted !== null) showRef.current(wanted);
    const onShow = (event) => showRef.current(event.detail.seq);
    window.addEventListener("pyacquisition:show-log", onShow);
    return () => window.removeEventListener("pyacquisition:show-log", onShow);
  }, []);
  // Scrolled there once the list has drawn with every message in it.
  useLayoutEffect(() => {
    const element = list.current;
    if (scrollTo.current === null || !element || element.clientHeight === 0) return;
    element.scrollTop = Math.max(0, scrollTo.current * row - element.clientHeight / 2);
    scrollTo.current = null;
    setView({ top: element.scrollTop, height: element.clientHeight });
  });

  useEffect(() => {
    const element = list.current;
    const observer = new ResizeObserver(() =>
      setView((current) => ({ ...current, height: element.clientHeight })),
    );
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  const needle = query.trim().toLowerCase();
  const entries = store.entries;
  const shown = filterEntries(entries, hidden, needle);
  const counts = countLevels(entries);
  const total = shown.length * row;
  const bottom = Math.max(0, total - view.height);

  // Where the list is scrolled to: the bottom while following. While held, where
  // it was, moved by however many rows above the anchor have gone or come.
  let top = bottom;
  let shift = 0;
  if (!following) {
    if (anchor.current) {
      shift = (firstFrom(shown, anchor.current.seq) - anchor.current.index) * row;
    }
    top = Math.min(Math.max(0, view.top + shift), bottom);
  }

  // Only ever scrolled for the user when following, or when rows above the view
  // shift. Otherwise it is left alone, so as not to fight a smooth scroll.
  useLayoutEffect(() => {
    const element = list.current;
    if (following) {
      if (!pressed.current && Math.abs(element.scrollTop - top) >= 1) {
        element.scrollTop = top;
      }
    } else if (shift !== 0) {
      // Set outright, not moved by the shift: a shorter list has already had
      // its scroll position pulled in by the browser.
      element.scrollTop = top;
      anchor.current.index += shift / row;
      setView((current) => ({ ...current, top: element.scrollTop }));
    }
  });

  const hold = (at) => {
    const first = Math.floor(at / row);
    anchor.current = shown[first] ? { seq: shown[first].seq, index: first } : null;
  };

  // The user is scrolling up: held at once, before the scroll itself arrives,
  // so a new message can't pull the list back down first. Unless there is
  // nowhere up to go.
  const stopFollowing = () => {
    if (!following || !list.current || list.current.scrollTop < 1) return;
    hold(top);
    setView((current) => ({ ...current, top }));
    setFollowing(false);
  };

  const onScroll = () => {
    const element = list.current;
    // A scroll can arrive after the tab has closed, and the list with it.
    if (!element) return;
    const scrolled = element.scrollTop;
    const atBottom = element.scrollHeight - scrolled - element.clientHeight < row / 2;
    setFollowing(atBottom);
    if (atBottom) anchor.current = null;
    else hold(scrolled);
    setView({ top: scrolled, height: element.clientHeight });
  };

  const latest = () => {
    anchor.current = null;
    setFollowing(true);
  };

  const toggleLevel = (level) =>
    setHidden((current) =>
      current.includes(level) ? current.filter((l) => l !== level) : [...current, level],
    );

  const clearFilters = () => {
    setHidden([]);
    setQuery("");
  };

  const start = Math.max(0, Math.floor(top / row) - OVERSCAN);
  const end = Math.min(shown.length, Math.ceil((top + view.height) / row) + OVERSCAN);
  const newer = following ? 0 : Math.max(0, shown.length - Math.ceil((top + view.height) / row));
  const levels = LEVELS.filter(
    (level) => ALWAYS_SHOWN.includes(level) || counts[level] > 0 || hidden.includes(level),
  );
  const found = selected === null ? null : entries[firstFrom(entries, selected)];
  const selectedEntry = found?.seq === selected ? found : null; // it may be trimmed
  const filtering = hidden.length > 0 || needle !== "";

  return html`
    <div class="logs">
      <div class="logs-toolbar">
        <div class="level-filter" role="group" aria-label="Levels shown">
          ${levels.map(
            (level) => html`
              <button
                key=${level}
                class="level-toggle"
                data-level=${level}
                aria-pressed=${!hidden.includes(level)}
                title="${hidden.includes(level) ? "Show" : "Hide"} ${LABELS[level].toLowerCase()} messages"
                onClick=${() => toggleLevel(level)}
              >
                <span class="level-dot" aria-hidden="true"></span>
                ${LABELS[level]}
                <span class="level-count">${counts[level]}</span>
              </button>
            `,
          )}
        </div>
        <label class="logs-search">
          <${SearchIcon} />
          <input
            type="search"
            placeholder="Search"
            aria-label="Search the log"
            value=${query}
            onInput=${(event) => setQuery(event.currentTarget.value)}
            onKeyDown=${(event) => event.key === "Escape" && setQuery("")}
          />
        </label>
        <span class="logs-count">
          ${filtering
            ? `${shown.length.toLocaleString()} of ${entries.length.toLocaleString()}`
            : `${entries.length.toLocaleString()} messages`}
        </span>
      </div>
      <div class="logs-body">
        <div
          class="logs-list"
          ref=${list}
          role="list"
          aria-label="Log messages"
          tabindex="0"
          onScroll=${onScroll}
          onWheel=${(event) => event.deltaY < 0 && stopFollowing()}
          onKeyDown=${(event) => UP_KEYS.has(event.key) && stopFollowing()}
          onPointerDown=${() => (pressed.current = true)}
          onPointerUp=${() => (pressed.current = false)}
          onPointerCancel=${() => (pressed.current = false)}
        >
          <div class="logs-spacer" style=${{ height: `${total}px` }}>
            ${shown.slice(start, end).map(
              (entry, i) => html`
                <${LogRow}
                  key=${entry.seq}
                  entry=${entry}
                  top=${(start + i) * row}
                  query=${needle}
                  selected=${entry.seq === selected}
                  onSelect=${setSelected}
                />
              `,
            )}
          </div>
          ${entries.length === 0 &&
          html`<p class="placeholder logs-empty">No log messages yet.</p>`}
          ${entries.length > 0 &&
          shown.length === 0 &&
          html`
            <div class="logs-empty">
              <p class="placeholder">No messages match.</p>
              <button class="bar-button" onClick=${clearFilters}>Clear the filters</button>
            </div>
          `}
        </div>
        ${!following &&
        html`
          <button
            class="logs-latest"
            aria-label="Jump to the latest message"
            onClick=${latest}
          >
            <${ArrowDownIcon} />
            Latest
            ${newer > 0 && html`<span class="logs-newer">${newer.toLocaleString()} newer</span>`}
          </button>
        `}
      </div>
      ${selectedEntry &&
      html`<${LogDetail} entry=${selectedEntry} onClose=${() => setSelected(null)} />`}
    </div>
  `;
}
