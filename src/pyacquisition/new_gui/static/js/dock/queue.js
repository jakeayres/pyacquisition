// The Queue tab: each task manager, with its state, the task it is running and
// the tasks waiting, and the controls the classic Task Queue page has: pause and
// resume, abort (after asking), and remove or move a queued task. Clearing the
// queue is here too, after asking.
//
// The state is polled (useManagers), and fetched again straight after anything
// done here, so it shows at once.
import { useState } from "preact/hooks";
import { html } from "../html.js";
import { usePolled } from "../hooks.js";
import { managerAction, managerStates } from "../api.js";
import { ConfirmDialog } from "../confirm.js";
import {
  ChevronDownIcon,
  ChevronUpIcon,
  CloseIcon,
  PauseIcon,
  PlayIcon,
  StopIcon,
} from "../icons.js";

const CHECK = 1000; // milliseconds between checks of the task managers

// Every task manager's state, by name, kept current while connected.
export function useManagers(connection) {
  const { value, refresh } = usePolled(connection, managerStates, CHECK);
  return { states: value, refresh };
}

// What a task manager is doing, for its badge: running, idle, paused or aborting.
export function stateOf(manager) {
  if (manager.aborting) return "aborting";
  if (manager.status === "Paused") return "paused";
  return manager.current_task ? "running" : "idle";
}

const STATE_LABELS = {
  running: "Running",
  idle: "Idle",
  paused: "Paused",
  aborting: "Aborting…",
};

// A parameter as it is shown: numbers without trailing noise.
export function formatParameter(value) {
  if (typeof value === "number") return String(Number(value.toPrecision(6)));
  if (value === null || value === undefined) return "—";
  return String(value);
}

const title = (name) => name.charAt(0).toUpperCase() + name.slice(1);

function Parameters({ parameters }) {
  const entries = Object.entries(parameters ?? {});
  if (entries.length === 0) return null;
  return html`
    <dl class="task-parameters">
      ${entries.map(
        ([name, value]) => html`
          <div class="task-parameter" key=${name}>
            <dt>${name}</dt>
            <dd>${formatParameter(value)}</dd>
          </div>
        `,
      )}
    </dl>
  `;
}

// What the last task to finish did, when it is worth saying: a failure or an
// abort that left the queue paused is a notice to act on; otherwise a quiet line.
function LastResult({ manager }) {
  const last = manager.last_result;
  if (!last) return null;
  const held = manager.status === "Paused" && !manager.current_task;
  if (held && last.outcome === "failed") {
    return html`
      <div class="queue-notice" data-kind="failed" role="alert">
        <strong>${last.name} failed</strong>, so this queue is paused. Resume to carry on
        with the next task.
        ${last.error && html`<div class="queue-error">${last.error}</div>`}
      </div>
    `;
  }
  if (held && last.outcome === "aborted") {
    return html`
      <div class="queue-notice" data-kind="aborted">
        <strong>${last.name} was aborted</strong>, so this queue is paused. Resume to
        carry on with the next task.
      </div>
    `;
  }
  return html`
    <p class="queue-last" data-outcome=${last.outcome}>
      Last: <span class="queue-last-name">${last.name}</span> ${last.outcome}${last.error
        ? html`: <span class="queue-error-inline">${last.error}</span>`
        : ""}
    </p>
  `;
}

function RunningTask({ manager, state, onAbort }) {
  const task = manager.current_task;
  if (!task) {
    return html`
      <div class="running-task empty" data-state=${state}>
        ${state === "paused" ? "Paused: nothing is running" : "Nothing is running"}
      </div>
    `;
  }
  return html`
    <div class="running-task" data-state=${state} aria-label="Running task">
      <div class="running-head">
        <span class="state-badge" data-state=${state}>${STATE_LABELS[state]}</span>
        <span class="task-name">${task.name}</span>
        <button
          class="button button-small button-danger-quiet"
          disabled=${manager.aborting}
          onClick=${onAbort}
        >
          <${StopIcon} /> Abort
        </button>
      </div>
      ${task.description && html`<p class="task-description">${task.description}</p>`}
      <${Parameters} parameters=${task.parameters} />
    </div>
  `;
}

function QueuedTask({ task, index, count, onMove, onRemove }) {
  return html`
    <li class="queued-task" data-task-id=${task.id}>
      <span class="queued-index">${index + 1}</span>
      <div class="queued-body">
        <span class="task-name" title=${task.description ?? ""}>${task.name}</span>
        <${Parameters} parameters=${task.parameters} />
      </div>
      <div class="queued-actions">
        <button
          class="icon-button"
          aria-label=${`Move ${task.name} up`}
          title="Move up (runs sooner)"
          disabled=${index === 0}
          onClick=${() => onMove(task, "up")}
        >
          <${ChevronUpIcon} />
        </button>
        <button
          class="icon-button"
          aria-label=${`Move ${task.name} down`}
          title="Move down"
          disabled=${index === count - 1}
          onClick=${() => onMove(task, "down")}
        >
          <${ChevronDownIcon} />
        </button>
        <button
          class="icon-button remove-button"
          aria-label=${`Remove ${task.name}`}
          title="Remove from the queue"
          onClick=${() => onRemove(task)}
        >
          <${CloseIcon} />
        </button>
      </div>
    </li>
  `;
}

function ManagerPanel({ name, manager, single, act, ask }) {
  const state = stateOf(manager);
  const paused = manager.status === "Paused";
  const queue = manager.queue ?? [];
  const label = single ? "Task queue" : title(name);

  const abort = () =>
    ask({
      title: `Abort ${manager.current_task.name}?`,
      // Sentences built as strings: htm drops a line break next to a ${...}.
      message: html`<p>
          ${`The task stops at its next step and runs its teardown. The ` +
          `${single ? "" : `${label} `}queue is then paused, so nothing else ` +
          `starts until you press Resume.`}
        </p>`,
      confirmLabel: "Abort",
      danger: true,
      run: () => act(name, "abort"),
    });

  const clear = () =>
    ask({
      title: `Clear the ${single ? "" : `${label} `}queue?`,
      message: html`<p>
          ${`This removes the ${queue.length === 1 ? "task" : `${queue.length} tasks`} ` +
          `waiting. A running task carries on.`}
        </p>`,
      confirmLabel: "Clear queue",
      danger: true,
      run: () => act(name, "clear_tasks"),
    });

  return html`
    <section class="manager" data-manager=${name} data-state=${state} aria-label=${label}>
      <header class="manager-head">
        <h3 class="manager-name">${label}</h3>
        <span class="state-badge" data-state=${state} role="status">
          <span class="state-dot" aria-hidden="true"></span>
          ${STATE_LABELS[state]}
        </span>
        <div class="manager-actions">
          <button class="button button-small" onClick=${() => act(name, paused ? "resume" : "pause")}>
            ${paused ? html`<${PlayIcon} /> Resume` : html`<${PauseIcon} /> Pause`}
          </button>
        </div>
      </header>
      <${LastResult} manager=${manager} />
      <${RunningTask} manager=${manager} state=${state} onAbort=${abort} />
      <div class="queue-head">
        <span class="queue-count">
          ${queue.length === 0 ? "Nothing queued" : `${queue.length} queued`}
        </span>
        ${queue.length > 0 &&
        html`<button class="link-button" onClick=${clear}>Clear queue</button>`}
      </div>
      ${queue.length > 0 &&
      html`
        <ol class="queued-tasks" aria-label=${`${label}: queued tasks`}>
          ${queue.map(
            (task, index) => html`
              <${QueuedTask}
                key=${task.id}
                task=${task}
                index=${index}
                count=${queue.length}
                onMove=${(t, direction) =>
                  act(name, "move_queued_task", { task_id: t.id, direction })}
                onRemove=${(t) => act(name, "remove_queued_task", { task_id: t.id })}
              />
            `,
          )}
        </ol>
      `}
    </section>
  `;
}

export function QueueTab({ managers }) {
  const [asking, setAsking] = useState(null); // the question being asked
  const [error, setError] = useState("");
  const states = managers.states;

  const act = async (name, action, params) => {
    setError("");
    try {
      await managerAction(name, action, params);
    } catch (e) {
      setError(`Couldn't ${action.replaceAll("_", " ")}: ${e.message}`);
    } finally {
      managers.refresh();
    }
  };

  if (!states) return html`<p class="placeholder">Waiting for the task managers…</p>`;
  const names = Object.keys(states);
  return html`
    <div class="queue-tab">
      ${error && html`<p class="queue-action-error" role="alert">${error}</p>`}
      <div class="manager-grid" data-count=${names.length}>
        ${names.map(
          (name) => html`
            <${ManagerPanel}
              key=${name}
              name=${name}
              manager=${states[name]}
              single=${names.length === 1}
              act=${act}
              ask=${setAsking}
            />
          `,
        )}
      </div>
      ${asking &&
      html`
        <${ConfirmDialog}
          title=${asking.title}
          confirmLabel=${asking.confirmLabel}
          danger=${asking.danger}
          onCancel=${() => setAsking(null)}
          onConfirm=${() => {
            asking.run();
            setAsking(null);
          }}
        >
          ${asking.message}
        <//>
      `}
    </div>
  `;
}
