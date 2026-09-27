// Alerts: a toast, and a count on the bell in the top bar, when something needs
// looking at: an error is logged, a task fails, measurements stop arriving, or
// the connection to the experiment drops. Each happening raises one alert: errors
// and a task failure close together are one alert (a failing task logs errors
// too), taking the most telling title. Recent alerts are listed under the bell.
import { useEffect, useRef, useState } from "preact/hooks";
import { html } from "./html.js";
import { Watched } from "./store.js";
import { useStore, usePopover } from "./hooks.js";
import { BellIcon, CloseIcon } from "./icons.js";

// The browser tests shorten the times below, so as not to wait them out, with a
// scale set before the page loads. It is 1 otherwise.
const SCALE = globalThis.pyacquisitionAlertTimeScale ?? 1;

const KEEP = 30; // alerts listed under the bell
const TOAST_FOR = 10000 * SCALE; // milliseconds a toast stays
const TOGETHER = 5000 * SCALE; // milliseconds within which alerts of a group are one
const STALL_PERIODS = 5; // measurement periods without a row before it's a stall
const STALL_AT_LEAST = 5000 * SCALE; // but never sooner than this, in milliseconds
const STALL_CHECK = 1000 * SCALE; // milliseconds between checks for a stall

// Text as a sentence: with a full stop, unless it ends in one already.
const sentence = (text) => (/[.!?]$/.test(text.trim()) ? text.trim() : `${text.trim()}.`);

// How telling each kind is, for the title of a merged alert.
const RANK = { error: 1, failed: 2 };

export class AlertStore extends Watched {
  constructor() {
    super();
    this.alerts = []; // newest first
    this.toasts = []; // the ids of those showing as toasts
    this.unread = 0;
    this.nextId = 1;
    this.timers = new Map();
  }

  // Raises an alert: {kind, title, message, group}. Within TOGETHER of the last
  // alert of the same group, it is merged into that one instead.
  add({ kind, title, message = "", group = null }) {
    const now = Date.now();
    const last = group && this.alerts.find((a) => a.group === group);
    if (last && now - last.at < TOGETHER) {
      last.count += 1;
      last.at = now;
      if ((RANK[kind] ?? 0) > (RANK[last.kind] ?? 0)) {
        Object.assign(last, { kind, title, message });
      }
      if (!this.toasts.includes(last.id)) this.toasts.unshift(last.id);
      this.showFor(last.id);
      this.changed();
      return last;
    }
    const alert = { id: this.nextId++, kind, title, message, group, at: now, count: 1, time: new Date() };
    this.alerts = [alert, ...this.alerts].slice(0, KEEP);
    this.toasts.unshift(alert.id);
    this.unread += 1;
    this.showFor(alert.id);
    this.changed();
    return alert;
  }

  showFor(id) {
    clearTimeout(this.timers.get(id));
    this.timers.set(id, setTimeout(() => this.dismiss(id), TOAST_FOR));
  }

  dismiss(id) {
    clearTimeout(this.timers.get(id));
    this.timers.delete(id);
    this.toasts = this.toasts.filter((t) => t !== id);
    this.changed();
  }

  // Seen: the count on the bell goes, and so do the toasts, which the list
  // shows too.
  read() {
    for (const id of this.toasts) clearTimeout(this.timers.get(id));
    this.toasts = [];
    this.unread = 0;
    this.changed();
  }

  clear() {
    for (const id of this.toasts) clearTimeout(this.timers.get(id));
    this.alerts = [];
    this.toasts = [];
    this.unread = 0;
    this.changed();
  }
}

// Watches for what raises alerts. `store` is the data, `logs` the log,
// `managers` the task managers' states (polled), `rack` the measurements' state
// (polled), and `connection` whether the experiment answers.
export function useAlertWatch({ alerts, connection, store, logs, managers, rack }) {
  // Errors logged from now on. The log from before the page loaded (or before
  // the experiment restarted) is history, not news.
  useEffect(() => {
    let seen = null;
    return logs.subscribe(() => {
      if (logs.status !== "live") return;
      if (seen === null || logs.seq < seen) {
        seen = logs.seq;
        return;
      }
      for (const entry of logs.entries) {
        if (entry.seq <= seen) continue;
        if (entry.level === "error" || entry.level === "exception") {
          alerts.add({ kind: "error", title: "An error was logged", message: entry.message, group: "trouble" });
        }
      }
      seen = logs.seq;
    });
  }, [logs, alerts]);

  // A task that fails: its manager's last result changes, and says failed. The
  // results already there when the page first looks are history.
  const known = useRef(null);
  useEffect(() => {
    const states = managers.states;
    if (!states) return;
    const first = known.current === null;
    known.current ??= {};
    for (const [name, state] of Object.entries(states)) {
      const result = state.last_result;
      const at = result?.finished_at ?? null;
      const before = known.current[name];
      known.current[name] = at;
      if (first || before === undefined || at === before || !result) continue;
      if (result.outcome === "failed") {
        const where = name === "main" ? "" : ` on ${name}`;
        alerts.add({
          kind: "failed",
          title: `${result.name} failed${where}`,
          message: `${sentence(result.error ?? "It failed")} The queue is paused until you resume it.`,
          group: "trouble",
        });
      }
    }
  }, [managers.states, alerts]);

  // No rows for a while, although measuring: once for each stall.
  const lastRow = useRef({ seq: store.seq, at: Date.now(), stalled: false });
  useEffect(
    () =>
      store.subscribe(() => {
        if (store.seq !== lastRow.current.seq) {
          lastRow.current = { seq: store.seq, at: Date.now(), stalled: false };
        }
      }),
    [store],
  );
  const measuring = connection === "connected" && rack.state && !rack.state.paused;
  const period = rack.state?.period ?? 1;
  useEffect(() => {
    if (!measuring) {
      // Paused or away: the wait starts again when measuring does.
      lastRow.current = { ...lastRow.current, at: Date.now(), stalled: false };
      return;
    }
    const limit = Math.max(STALL_PERIODS * period * 1000, STALL_AT_LEAST);
    const timer = setInterval(() => {
      const row = lastRow.current;
      if (row.stalled || store.status !== "live" || Date.now() - row.at < limit) return;
      row.stalled = true;
      const seconds = Math.round((Date.now() - row.at) / 1000);
      alerts.add({
        kind: "stalled",
        title: "No data is arriving",
        message: `Measuring every ${Number(period.toPrecision(3))} s, but no row has arrived for ${seconds} s.`,
        group: "stall",
      });
    }, STALL_CHECK);
    return () => clearInterval(timer);
  }, [measuring, period, store, alerts]);

  // The connection dropping, unless the experiment was stopped from here.
  const before = useRef(connection);
  useEffect(() => {
    if (before.current === "connected" && connection === "disconnected" && !window.pyacquisition?.stopping) {
      alerts.add({
        kind: "connection",
        title: "The experiment stopped answering",
        message: "The connection dropped. The page reconnects by itself when it answers again.",
        group: "connection",
      });
    }
    before.current = connection;
  }, [connection, alerts]);
}

const time = (date) => date.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit", second: "2-digit" });

function AlertBody({ alert }) {
  return html`
    <div class="alert-body">
      <div class="alert-title">
        ${alert.title}
        ${alert.count > 1 && html`<span class="alert-count" title="Merged alerts">×${alert.count}</span>`}
      </div>
      ${alert.message && html`<div class="alert-message">${alert.message}</div>`}
      <time class="alert-time">${time(alert.time)}</time>
    </div>
  `;
}

// The toasts, top right, newest first.
export function AlertToasts({ alerts }) {
  useStore(alerts);
  const shown = alerts.toasts
    .map((id) => alerts.alerts.find((a) => a.id === id))
    .filter(Boolean)
    .slice(0, 3);
  return html`
    <div class="toasts" aria-label="Alerts" role="region">
      ${shown.map(
        (alert) => html`
          <div class="toast" key=${alert.id} data-kind=${alert.kind} role="alert">
            <${AlertBody} alert=${alert} />
            <button class="icon-button" aria-label="Dismiss" title="Dismiss" onClick=${() => alerts.dismiss(alert.id)}>
              <${CloseIcon} />
            </button>
          </div>
        `,
      )}
    </div>
  `;
}

// The bell in the top bar: how many alerts are new, and the recent ones.
export function AlertBell({ alerts }) {
  useStore(alerts);
  const [open, setOpen] = useState(false);
  const menu = useRef(null);
  usePopover(menu, open, () => setOpen(false));
  const toggle = () => {
    if (!open) alerts.read();
    setOpen(!open);
  };
  const unread = alerts.unread;
  return html`
    <div class="topbar-menu alert-bell" ref=${menu}>
      <button
        class="icon-button"
        aria-label=${unread ? `Alerts, ${unread} new` : "Alerts"}
        aria-expanded=${open}
        title="Alerts"
        onClick=${toggle}
      >
        <${BellIcon} />
        ${unread > 0 && html`<span class="alert-badge">${unread > 9 ? "9+" : unread}</span>`}
      </button>
      ${open &&
      html`
        <div class="popover alert-list" role="dialog" aria-label="Recent alerts">
          <div class="alert-list-head">
            <span class="popover-label">Recent alerts</span>
            ${alerts.alerts.length > 0 &&
            html`<button class="link-button link-button-plain" onClick=${() => alerts.clear()}>Clear</button>`}
          </div>
          ${alerts.alerts.length === 0
            ? html`<p class="placeholder">No alerts.</p>`
            : html`
                <ol class="alert-items">
                  ${alerts.alerts.map(
                    (alert) => html`<li class="alert-item" key=${alert.id} data-kind=${alert.kind}><${AlertBody} alert=${alert} /></li>`,
                  )}
                </ol>
              `}
        </div>
      `}
    </div>
  `;
}
