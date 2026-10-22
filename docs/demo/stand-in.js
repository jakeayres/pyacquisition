// SPDX-License-Identifier: MPL-2.0
// Copyright (C) 2023-2026 Jake Ayres
//
// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.

// The stand-in for an experiment, so the real interface can run in the docs.
//
// The interface (docs/demo/app/, a copy of src/pyacquisition/gui/static/) asks
// the experiment for everything through `fetch`, at absolute paths, and follows
// its streams through `WebSocket`. This script runs first and takes the place
// of both. It answers from a recording (session.json, made by
// scripts/record_demo.py from examples/simulated_rig/front_page_rig.py):
//
// - the rows of one cycle of cooling and warming, played round and round, with
//   `time` and `seq` counting on, and any data files the recording started;
// - the task managers' state and the log, as they were at each row;
// - the recorded answer of every fixed endpoint;
// - the latest value, for a query that a measurement makes.
//
// Pausing and resuming the rack work. Anything else that would change the
// experiment (a command, a task, a new file) answers with the demo message,
// which the interface shows as it shows any error.
//
// window.pyacquisitionDemo is for the page around the frame (hero.js) and for
// the tests: `answers(path)`, `streams`, `unanswered`, `hold(reason)` and
// `release(reason)`, `held` and `seq`.
(() => {
  "use strict";

  const MESSAGE =
    "This is a demo in the documentation, with no instruments connected. " +
    "Install PyAcquisition to run your own.";

  const realFetch = window.fetch.bind(window);
  const SESSION = new URL("../session.json", document.baseURI);
  const still = matchMedia("(prefers-reduced-motion: reduce)").matches;

  // What changes the experiment, answered with the demo message.
  const ACTIONS = [
    /^\/tasks\//,
    /^\/task_manager\//,
    /^\/managers\/[^/]+\//,
    /^\/scribe\/next_file$/,
    /^\/rack\/period\/set\/$/,
    /^\/sequences\/(save|load|delete)$/,
    /^\/experiment\/(plot_script|shutdown)$/,
    /^\/traces\/[^/]+\/acquire$/,
  ];

  // The interface keeps its layout for the session in sessionStorage, which the
  // docs' pages share with it: a layout the front page's frame kept would come back
  // in the full-size demo. So each page of the demo keeps its own, in memory.
  const memory = new Map();
  const own = {
    getItem: (key) => (memory.has(key) ? memory.get(key) : null),
    setItem: (key, value) => void memory.set(key, String(value)),
    removeItem: (key) => void memory.delete(key),
    clear: () => memory.clear(),
    key: (i) => [...memory.keys()][i] ?? null,
    get length() {
      return memory.size;
    },
  };
  Object.defineProperty(window, "sessionStorage", { value: own, configurable: true });

  const unanswered = [];
  const holds = new Set(); // why the rows are held: "hidden", "away"...
  let rackPaused = false;

  // ------------------------------------------------------------ the recording
  let demo = null; // the recording, once loaded, with what is worked out from it

  // Loads it, trying again a few times, waiting longer each time: a request
  // that fails on its way would otherwise leave the demo waiting for ever.
  function load(attempt = 0) {
    return realFetch(SESSION)
      .then((response) => {
        if (!response.ok) throw new Error(`${SESSION} answered ${response.status}`);
        return response.json();
      })
      .catch((error) => {
        if (attempt >= 4) throw error;
        return new Promise((resolve) => setTimeout(resolve, 400 * 2 ** attempt)).then(() =>
          load(attempt + 1),
        );
      });
  }

  const ready = load().then((session) => {
    demo = prepare(session);
    start();
    return demo;
  });
  ready.catch((error) => console.error(`The demo's recording didn't load: ${error}`));

  // A recording is played as a cycle of events, round and round: a row for each
  // recorded row, and before a row that started a data file, that file. Event `g`
  // counts from the start of the recording, for ever, as the stream's `seq` does.
  function prepare(session) {
    const rows = session.rows;
    const length = rows.length;
    const at = session.columns.indexOf("time");
    const timed = at >= 0 && length > 1;
    const step = timed ? (rows[length - 1][at] - rows[0][at]) / (length - 1) : session.period;
    const cycle = timed ? rows[length - 1][at] - rows[0][at] + step : length * step;

    const starts = new Map((session.files ?? []).map(([index, file]) => [index, file]));
    const events = [];
    const eventOfRow = [];
    rows.forEach((_, i) => {
      if (starts.has(i)) events.push({ file: starts.get(i) });
      eventOfRow.push(events.length);
      events.push({ row: i });
    });

    // Open just before the sample first goes through its transition, so
    // something is happening from the start. The row where the signal `x`
    // first crosses half its swing, either way, is the middle of it.
    let first = 0;
    const x = session.columns.indexOf("x");
    if (x >= 0 && length) {
      const xs = rows.map((row) => row[x]);
      const half = (Math.min(...xs) + Math.max(...xs)) / 2;
      const crossing = xs.findIndex((value, i) => i > 0 && value > half !== xs[i - 1] > half);
      const lead = Math.round(6 / session.period); // seconds before it
      first = eventOfRow[crossing > lead ? crossing - lead : 0];
    }

    // The log entries of each event, and how many come before each event in a cycle.
    const logsAt = events.map(() => []);
    for (const [index, entry] of session.logs) logsAt[eventOfRow[index]]?.push(entry);
    const before = [0];
    for (let j = 0; j < events.length; j += 1) before.push(before[j] + logsAt[j].length);

    // The file each event is in: the last to start at or before it, round the cycle,
    // or the recording's own if it started none.
    const fileOf = [];
    let file = session.responses["/scribe/state"]?.data?.file ?? "demo.data";
    const last = [...events].reverse().find((e) => e.file);
    if (last) file = last.file;
    for (const e of events) {
      if (e.file) file = e.file;
      fileOf.push(file);
    }

    return {
      session,
      rows,
      length,
      cycle,
      events,
      count: events.length,
      first, // the oldest event in the first snapshot
      next: first + events.length, // the next event to send
      fileOf,
      file,
      logsAt,
      before,
      opened: Date.now() / 1000,
    };
  }

  const eventAt = (g) => demo.events[g % demo.count];

  // Row event `g`'s values, its time on by a cycle for each time round.
  function rowAt(g) {
    const { rows, count, cycle, session } = demo;
    const values = {};
    const recorded = rows[eventAt(g).row];
    session.columns.forEach((name, i) => {
      values[name] = recorded[i];
    });
    if ("time" in values) values.time += Math.floor(g / count) * cycle;
    return values;
  }

  // The latest row sent, as an event, or -1 if there is none.
  function latestRow() {
    for (let g = demo.next - 1; g >= demo.next - demo.count && g >= 0; g -= 1) {
      if ("row" in eventAt(g)) return g;
    }
    return -1;
  }

  // The sequence number of event `g`: the first snapshot's are 1 to `count`.
  const seqOf = (g) => g - demo.first + 1;

  // When event `g` happened, by the wall's clock, for the log.
  const wallOf = (g) => demo.opened + (g - (demo.first + demo.count)) * demo.session.period;

  // The log entries before event `g`, since the first snapshot's oldest event.
  function logCount(g) {
    const { count, before, first } = demo;
    if (!count) return 0;
    const upto = (n) => Math.floor(n / count) * before[count] + before[n % count];
    return upto(g) - upto(first);
  }

  function logEntries(g) {
    const base = demo.session.prelude.length + logCount(g);
    return demo.logsAt[g % demo.count].map((entry, j) => ({
      ...entry,
      type: "log",
      seq: base + j + 1,
      time: wallOf(g),
    }));
  }

  // ------------------------------------------------------------ the clock
  const sockets = { "/stream/data": new Set(), "/stream/logs": new Set() };

  function start() {
    if (still || !demo.count) return;
    setInterval(tick, demo.session.period * 1000);
  }

  // Sends the next row, and the file it starts, if it starts one.
  function tick() {
    if (rackPaused || holds.size) return;
    for (;;) {
      const g = demo.next;
      demo.next += 1;
      const event = eventAt(g);
      if (event.file) {
        send("/stream/data", { type: "new_file", seq: seqOf(g), file: event.file });
        continue;
      }
      send("/stream/data", { type: "row", seq: seqOf(g), values: rowAt(g) });
      for (const entry of logEntries(g)) send("/stream/logs", entry);
      return;
    }
  }

  function send(stream, event) {
    const text = JSON.stringify(event);
    for (const socket of sockets[stream]) socket._message(text);
  }

  document.addEventListener("visibilitychange", () => {
    if (document.hidden) holds.add("hidden");
    else holds.delete("hidden");
  });

  // ------------------------------------------------------------ the answers
  const ok = (data) => ({ status: 200, data });

  // The history: the last cycle of events, as the files they are in, the current
  // and the one before, as History keeps them (core/history.py).
  function snapshotBinary() {
    const { count, next, session, fileOf } = demo;
    const columns = session.columns;
    const segments = [];
    let segment = { file: count ? fileOf[(next - count) % count] : demo.file, values: [] };
    segments.push(segment);
    for (let g = next - count; g < next; g += 1) {
      const event = eventAt(g);
      if (event.file) {
        segment = { file: event.file, values: [] };
        segments.push(segment);
      } else {
        segment.values.push(rowAt(g));
      }
    }
    const kept = segments.filter((s, i) => s.values.length || i === segments.length - 1).slice(-2);
    const latestAt = latestRow();
    const header = {
      seq: count ? seqOf(next - 1) : 0,
      max_rows: demo.length,
      latest: latestAt >= 0 ? rowAt(latestAt) : {},
      segments: kept.map((s) => ({ file: s.file, rows: s.values.length, columns })),
    };
    let text = JSON.stringify(header);
    text += " ".repeat((8 - ((4 + text.length) % 8)) % 8); // columns start on 8 bytes
    const head = new TextEncoder().encode(text);
    const total = kept.reduce((n, s) => n + s.values.length, 0);
    const buffer = new ArrayBuffer(4 + head.length + 8 * total * columns.length);
    new DataView(buffer).setUint32(0, head.length, true);
    new Uint8Array(buffer, 4, head.length).set(head);
    let offset = 4 + head.length;
    for (const s of kept) {
      for (const name of columns) {
        const column = new Float64Array(buffer, offset, s.values.length);
        s.values.forEach((v, i) => {
          column[i] = v[name] ?? NaN;
        });
        offset += 8 * s.values.length;
      }
    }
    return buffer;
  }

  function logHistory() {
    const { session, first, next, count } = demo;
    const prelude = session.prelude.map((entry, i) => ({
      ...entry,
      type: "log",
      seq: i + 1,
      time: wallOf(first) - (session.prelude.length - i),
    }));
    const entries = [...prelude];
    if (count) for (let g = first; g < next; g += 1) entries.push(...logEntries(g));
    return { seq: prelude.length + logCount(next), max_entries: 5000, entries };
  }

  function managerState() {
    const latestAt = latestRow();
    const index = latestAt >= 0 ? eventAt(latestAt).row : 0;
    let state = demo.session.managers[0][1];
    for (const [at, recorded] of demo.session.managers) {
      if (at > index) break;
      state = recorded;
    }
    state = structuredClone(state);
    for (const manager of Object.values(state)) {
      const task = manager.current_task;
      if (task) task.started_at = Date.now() / 1000 - (task.elapsed ?? 0);
    }
    return ok(state);
  }

  // The latest value of the column a measurement's query feeds, if these are
  // the arguments it is called with.
  function measured(path, params) {
    const found = demo.session.measured[path];
    const latestAt = latestRow();
    if (!found || latestAt < 0) return undefined;
    const plain = (value) => String(value).toUpperCase().replace(/[^A-Z0-9]+/g, "_");
    for (const [name, value] of Object.entries(found.params)) {
      if (plain(params.get(name) ?? "") !== plain(value)) return undefined;
    }
    return ok(rowAt(latestAt)[found.column]);
  }

  const LIVE = {
    "/history": () => snapshotBinary(),
    "/logs/history": () => ok(logHistory()),
    "/managers/state": managerState,
    "/rack/state": () => ({ ...demo.session.responses["/rack/state"], paused: rackPaused }),
    "/rack/pause/": () => {
      rackPaused = true;
      return { status: "success", paused: true };
    },
    "/rack/resume/": () => {
      rackPaused = false;
      return { status: "success", paused: false };
    },
    "/experiment/layout": () => ok(demo.session.layout),
    "/news": () =>
      ok({ show: [], all: [], mode: "all", maker_news: false, pending: false, waiting: false }),
    "/news/choices": () => ({ status: 200 }),
  };

  // How a path is answered: "live", "recorded", "measured", "demo", or null
  // for a path the stand-in doesn't know.
  function answers(path) {
    if (path in LIVE) return "live";
    if (path in demo.session.responses) return "recorded";
    if (path in demo.session.measured) return "measured";
    if (ACTIONS.some((pattern) => pattern.test(path))) return "demo";
    const uid = path.split("/")[1];
    const instruments = demo.session.responses["/rack/list_instruments"]?.instruments ?? {};
    if (uid in instruments) return "demo"; // the instrument's other queries, and its commands
    return null;
  }

  function reply(body, status = 200) {
    if (body instanceof ArrayBuffer) {
      return new Response(body, {
        status,
        headers: { "Content-Type": "application/octet-stream" },
      });
    }
    return new Response(JSON.stringify(body), {
      status,
      headers: { "Content-Type": "application/json" },
    });
  }

  async function answer(url, init) {
    await ready;
    const { pathname: path, searchParams: params } = new URL(url, location.origin);
    const method = (init?.method ?? "GET").toUpperCase();
    switch (answers(path)) {
      case "live":
        if (path === "/experiment/layout" && method !== "GET") return reply({ status: 200 });
        return reply(LIVE[path]());
      case "recorded":
        return reply(demo.session.responses[path]);
      case "measured": {
        const value = measured(path, params);
        return value ? reply(value) : reply({ detail: MESSAGE }, 409);
      }
      case "demo":
        return reply({ detail: MESSAGE }, 409);
      default:
        unanswered.push(path);
        console.error(`The demo has no answer for ${method} ${path}`);
        return reply({ detail: `The demo has no answer for ${path}.` }, 404);
    }
  }

  window.fetch = (input, init) => {
    const url = input instanceof Request ? input.url : String(input);
    // The interface's requests are absolute paths. Anything else is a file.
    if (!url.startsWith("/")) return realFetch(input, init);
    return answer(url, init);
  };

  // ------------------------------------------------------------ the streams
  class DemoSocket extends EventTarget {
    static CONNECTING = 0;
    static OPEN = 1;
    static CLOSING = 2;
    static CLOSED = 3;

    constructor(url) {
      super();
      this.url = String(url);
      this.stream = new URL(this.url).pathname;
      this.readyState = DemoSocket.CONNECTING;
      this.onopen = this.onmessage = this.onclose = this.onerror = null;
      ready.then(() => {
        if (this.readyState !== DemoSocket.CONNECTING) return;
        if (!(this.stream in sockets)) {
          unanswered.push(this.stream);
          console.error(`The demo has no stream ${this.stream}`);
          this.close();
          return;
        }
        sockets[this.stream].add(this);
        this.readyState = DemoSocket.OPEN;
        this._fire("open", new Event("open"));
      });
    }

    _fire(type, event) {
      this.dispatchEvent(event);
      this[`on${type}`]?.(event);
    }

    _message(data) {
      if (this.readyState === DemoSocket.OPEN) {
        this._fire("message", new MessageEvent("message", { data }));
      }
    }

    send() {}

    close() {
      if (this.readyState === DemoSocket.CLOSED) return;
      this.readyState = DemoSocket.CLOSED;
      sockets[this.stream]?.delete(this);
      setTimeout(() => this._fire("close", new CloseEvent("close")), 0);
    }
  }
  window.WebSocket = DemoSocket;

  // ------------------------------------------------------------ for the page
  window.pyacquisitionDemo = {
    ready,
    unanswered,
    answers: (path) => (demo ? answers(path) : null),
    streams: Object.keys(sockets),
    hold: (reason) => holds.add(reason),
    release: (reason) => holds.delete(reason),
    get held() {
      return holds.size > 0 || rackPaused;
    },
    get seq() {
      return demo ? seqOf(demo.next - 1) : 0;
    },
    message: MESSAGE,
  };

  // Opened on its own, not in the front page's frame: say what it is, and the
  // way back.
  if (window.top === window) {
    addEventListener("DOMContentLoaded", async () => {
      const banner = document.createElement("a");
      banner.className = "demo-banner";
      banner.href = new URL("../", location.href).href;
      const label = (await ready.catch(() => null))?.session.label ?? "simulated instruments";
      banner.innerHTML = `<b>Demo</b> · ${label.replace(/[<&]/g, "")} · <span>Back to the docs</span>`;
      document.body.append(banner);
    });
  }
})();
