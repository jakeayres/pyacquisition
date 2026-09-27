// How far along a running task is (see Task.set_progress on the server): a
// bar, the step or percentage, what it is doing, how long it has run and how
// long is left. In full on the running task in the Queue tab, and compact in the
// top bar.
import { html } from "./html.js";
import { formatDuration } from "./format.js";

// Below this fraction it is too early to estimate the time left from the time
// taken so far.
const ESTIMATE_FROM = 0.03;

// The seconds left, and whether they are an estimate: what the task said, or
// else worked out from how long it has taken to get this far.
export function remainingOf(task) {
  const progress = task?.progress;
  if (!progress) return { seconds: null, estimated: false };
  if (progress.remaining !== null && progress.remaining !== undefined) {
    return { seconds: progress.remaining, estimated: false };
  }
  const { fraction } = progress;
  if (fraction >= ESTIMATE_FROM && fraction < 1 && task.elapsed > 0) {
    return { seconds: (task.elapsed * (1 - fraction)) / fraction, estimated: true };
  }
  return { seconds: null, estimated: false };
}

const whole = (n) => (Number.isInteger(n) ? String(n) : String(Number(n.toFixed(1))));

// "3 of 5", or "40%".
export function progressLabel(progress) {
  if (progress.steps) return `${whole(progress.step)} of ${whole(progress.steps)}`;
  return `${Math.round(progress.fraction * 100)}%`;
}

// "1:05 left", or "About 1:05 left" for an estimate; "" if not known.
export function leftLabel(task) {
  const { seconds, estimated } = remainingOf(task);
  if (seconds === null) return "";
  return `${estimated ? "About " : ""}${formatDuration(seconds)} left`;
}

export function ProgressBar({ progress, label, small = false }) {
  const percent = Math.round(progress.fraction * 100);
  return html`
    <div
      class="progress ${small ? "progress-small" : ""}"
      role="progressbar"
      aria-label=${label}
      aria-valuemin="0"
      aria-valuemax="100"
      aria-valuenow=${percent}
      aria-valuetext=${progressLabel(progress)}
    >
      <span class="progress-fill" style=${{ width: `${percent}%` }}></span>
    </div>
  `;
}

// The running task's progress and time, and its subtasks' progress, for the
// card in the Queue tab.
export function TaskProgress({ task }) {
  const progress = task.progress;
  const left = leftLabel(task);
  return html`
    <div class="task-progress">
      ${progress && html`<${ProgressBar} progress=${progress} label=${`${task.name} progress`} />`}
      <div class="task-progress-line">
        ${progress && html`<span class="progress-amount">${progressLabel(progress)}</span>`}
        ${progress?.note && html`<span class="progress-note">${progress.note}</span>`}
        <span class="progress-times">
          ${task.elapsed !== null && task.elapsed !== undefined &&
          html`<span class="progress-elapsed">Running for ${formatDuration(task.elapsed)}</span>`}
          ${left && html`<span class="progress-left">${left}</span>`}
        </span>
      </div>
      ${(task.subtasks ?? []).map(
        (subtask) => html`
          <div class="subtask-progress" key=${subtask.name}>
            <span class="subtask-name">${subtask.name}</span>
            ${subtask.progress &&
            html`
              <${ProgressBar} progress=${subtask.progress} label=${`${subtask.name} progress`} small />
              <span class="progress-amount">${progressLabel(subtask.progress)}</span>
              ${subtask.progress.note && html`<span class="progress-note">${subtask.progress.note}</span>`}
            `}
          </div>
        `,
      )}
    </div>
  `;
}

// The running tasks, compact, for the top bar: the first one's name, how far
// along it is and the time left, and how many others are running. Pressing it
// opens the Queue tab. Nothing is shown while nothing runs.
export function RunningSummary({ states }) {
  if (!states) return null;
  const running = Object.entries(states).filter(([, state]) => state.current_task);
  if (running.length === 0) return null;
  const [, first] = running[0];
  const task = first.current_task;
  const left = leftLabel(task);
  const open = () =>
    window.dispatchEvent(new CustomEvent("pyacquisition:open-tab", { detail: "queue" }));
  const parts = [task.name, task.progress && progressLabel(task.progress), left].filter(Boolean);
  return html`
    <button
      class="topbar-chip running-summary"
      aria-label=${`Running: ${parts.join(", ")}${running.length > 1 ? `, and ${running.length - 1} more` : ""}`}
      title="Show the queue"
      onClick=${open}
    >
      <span class="running-name">${task.name}</span>
      ${task.progress &&
      html`
        <${ProgressBar} progress=${task.progress} label=${`${task.name} progress`} small />
        <span class="progress-amount">${progressLabel(task.progress)}</span>
      `}
      ${left && html`<span class="progress-left">${left}</span>`}
      ${running.length > 1 && html`<span class="running-more">+${running.length - 1}</span>`}
    </button>
  `;
}
