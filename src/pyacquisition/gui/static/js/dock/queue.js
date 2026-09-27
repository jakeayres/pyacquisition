// The Queue tab: each task manager, with its state, the task it is running and
// the tasks waiting, and their controls: pause and resume, abort (after asking), and remove or move a queued task. Clearing the
// queue is here too, after asking, and so are dragging a task to a new place and
// duplicating one (milestone 11).
//
// The state is polled (useManagers), and fetched again straight after anything
// done here, so it shows at once.
import { useLayoutEffect, useRef, useState } from "preact/hooks";
import { html } from "../html.js";
import { usePolled } from "../hooks.js";
import { managerAction, managerStates } from "../api.js";
import { ConfirmDialog } from "../confirm.js";
import { AddTaskDialog } from "./add-task.js";
import { LoadSequenceDialog, SaveSequenceDialog } from "./sequences.js";
import { dropIndex, reorder, useQueueDrag } from "./queue-drag.js";
import { TaskProgress } from "../progress.js";
import {
  ChevronDownIcon,
  ChevronUpIcon,
  CloseIcon,
  CopyIcon,
  GripIcon,
  PauseIcon,
  PlayIcon,
  PlusIcon,
  StopIcon,
} from "../icons.js";

const CHECK = 1000; // milliseconds between checks of the task managers
// How long a new order made here is shown before the server's is trusted again,
// if the server never catches up (the move was refused, say).
const PENDING_FOR = 3000;

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

// The tasks in the order of `ids`, with any not in it (queued since) after them.
function inOrder(tasks, ids) {
  const byId = new Map(tasks.map((t) => [t.id, t]));
  const ordered = ids.filter((id) => byId.has(id)).map((id) => byId.get(id));
  return [...ordered, ...tasks.filter((t) => !ids.includes(t.id))];
}

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

// What a queued query read, short enough for the last result's line.
function resultValue(value) {
  const text = typeof value === "object" ? JSON.stringify(value) : formatParameter(value);
  return text.length > 80 ? `${text.slice(0, 79)}…` : text;
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
      Last: <span class="queue-last-name">${last.name}</span> ${last.outcome}${last.value !== null &&
      last.value !== undefined
        ? html` → <span class="queue-last-value">${resultValue(last.value)}</span>`
        : ""}${last.error
        ? html`: <span class="queue-error-inline">${last.error}</span>`
        : ""}
    </p>
  `;
}

function RunningTask({ manager, state, onAbort, onDuplicate }) {
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
          class="icon-button running-again"
          aria-label=${`Queue ${task.name} again`}
          title="Queue again, to run next"
          onClick=${() => onDuplicate(task)}
        >
          <${CopyIcon} />
        </button>
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
      <${TaskProgress} task=${task} />
    </div>
  `;
}

function QueuedTask({ task, index, count, drag, onDragStart, onKey, onMove, onRemove, onDuplicate }) {
  const dragged = drag?.id === task.id;
  // The line where a dragged task would go: before this row, or after the last.
  const moves = drag && dropIndex(drag.from, drag.gap) !== drag.from;
  const lineBefore = moves && drag.gap === index;
  const lineAfter = moves && drag.gap === count && index === count - 1;
  return html`
    <li
      class="queued-task ${dragged ? "dragged" : ""} ${lineBefore ? "drop-before" : ""} ${lineAfter ? "drop-after" : ""}"
      data-task-id=${task.id}
    >
      <button
        class="drag-handle"
        aria-label=${`Drag ${task.name} to a new place`}
        title="Drag to reorder (or use the arrow keys)"
        onPointerDown=${(event) => onDragStart(event, task.id, index)}
        onKeyDown=${(event) => onKey(event, task, index)}
      >
        <${GripIcon} />
      </button>
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
          class="icon-button"
          aria-label=${`Duplicate ${task.name}`}
          title="Duplicate (the copy goes straight after it)"
          onClick=${() => onDuplicate(task)}
        >
          <${CopyIcon} />
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

function ManagerPanel({ name, manager, single, act, ask, onAdd, onSequence }) {
  const state = stateOf(manager);
  const paused = manager.status === "Paused";
  const label = single ? "Task queue" : title(name);
  const list = useRef(null);
  const refocus = useRef(null); // the task whose handle had the focus, as it moved

  // A new order made here is shown at once, until the server's state has it.
  // Checked at each render, which the polling brings every second.
  const [pending, setPending] = useState(null); // {ids, since}
  const served = manager.queue ?? [];
  const showing =
    pending &&
    pending.ids.join() !== served.map((t) => t.id).join() &&
    Date.now() - pending.since < PENDING_FOR;
  const queue = showing ? inOrder(served, pending.ids) : served;
  const ids = queue.map((t) => t.id);

  const place = (id, from, to) => {
    setPending({ ids: reorder(ids, from, to), since: Date.now() });
    act(name, "place_queued_task", { task_id: id, index: to });
  };
  const { drag, start } = useQueueDrag(list, place);

  // On a handle: the arrow keys move the task a place, and Home and End to
  // either end, keeping the focus on it as it goes.
  const onKey = (event, task, index) => {
    const to = { ArrowUp: index - 1, ArrowDown: index + 1, Home: 0, End: queue.length - 1 }[event.key];
    if (to === undefined) return;
    event.preventDefault();
    if (to < 0 || to >= queue.length || to === index) return;
    refocus.current = task.id;
    place(task.id, index, to);
  };
  useLayoutEffect(() => {
    if (!refocus.current) return;
    list.current?.querySelector(`[data-task-id="${refocus.current}"] .drag-handle`)?.focus();
    refocus.current = null;
  });

  const duplicate = (task) => act(name, "duplicate_queued_task", { task_id: task.id });

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
          <button
            class="button button-small"
            aria-label=${single ? "Add a task" : `Add a task to ${label}`}
            onClick=${() => onAdd(name, label)}
          >
            <${PlusIcon} /> Add task
          </button>
          <button class="button button-small" onClick=${() => act(name, paused ? "resume" : "pause")}>
            ${paused ? html`<${PlayIcon} /> Resume` : html`<${PauseIcon} /> Pause`}
          </button>
        </div>
      </header>
      <${LastResult} manager=${manager} />
      <${RunningTask} manager=${manager} state=${state} onAbort=${abort} onDuplicate=${duplicate} />
      <div class="queue-head">
        <span class="queue-count">
          ${queue.length === 0 ? "Nothing queued" : `${queue.length} queued`}
        </span>
        <div class="queue-head-actions">
          ${(queue.length > 0 || manager.current_task) &&
          html`
            <button
              class="link-button link-button-plain"
              aria-label=${single ? "Save as a sequence" : `Save ${label} as a sequence`}
              onClick=${() =>
                onSequence({
                  kind: "save",
                  name,
                  label,
                  running: manager.current_task?.name ?? null,
                  count: queue.length,
                })}
            >
              Save…
            </button>
          `}
          <button
            class="link-button link-button-plain"
            aria-label=${single ? "Load a sequence" : `Load a sequence onto ${label}`}
            onClick=${() => onSequence({ kind: "load", name, label })}
          >
            Load…
          </button>
          ${queue.length > 0 &&
          html`<button class="link-button" onClick=${clear}>Clear queue</button>`}
        </div>
      </div>
      ${queue.length > 0 &&
      html`
        <ol class="queued-tasks ${drag ? "dragging" : ""}" ref=${list} aria-label=${`${label}: queued tasks`}>
          ${queue.map(
            (task, index) => html`
              <${QueuedTask}
                key=${task.id}
                task=${task}
                index=${index}
                count=${queue.length}
                drag=${drag}
                onDragStart=${start}
                onKey=${onKey}
                onDuplicate=${duplicate}
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
  const [adding, setAdding] = useState(null); // {name, label} of the manager being added to
  const [sequence, setSequence] = useState(null); // {kind: "save" or "load", name, label, ...}
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
              onAdd=${(name, label) => setAdding({ name, label })}
              onSequence=${setSequence}
            />
          `,
        )}
      </div>
      ${sequence?.kind === "save" &&
      html`
        <${SaveSequenceDialog}
          manager=${sequence.name}
          label=${names.length === 1 ? "" : sequence.label}
          running=${sequence.running}
          count=${sequence.count}
          onClose=${() => setSequence(null)}
        />
      `}
      ${sequence?.kind === "load" &&
      html`
        <${LoadSequenceDialog}
          manager=${sequence.name}
          label=${names.length === 1 ? "" : sequence.label}
          onLoaded=${managers.refresh}
          onClose=${() => setSequence(null)}
        />
      `}
      ${adding &&
      html`
        <${AddTaskDialog}
          manager=${adding.name}
          label=${names.length === 1 ? "" : adding.label}
          onAdded=${managers.refresh}
          onClose=${() => setAdding(null)}
        />
      `}
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
