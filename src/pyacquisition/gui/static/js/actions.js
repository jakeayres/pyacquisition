// The palette's actions: what the interface's buttons and keys do, found and run
// from Ctrl+K like tasks and instrument calls. An action runs when it is picked,
// never queued. One that a task can do in its turn names it (`task`), and
// Shift+Enter queues that task instead.
//
// A later feature adds its own with `registerAction({...})`:
//
//   registerAction({
//     name: "new-file",               // the item's id is "action:new-file"
//     label: "New data file",         // or (context, each) => the label
//     tag: "Experiment",
//     description: "…",
//     keywords: "scribe step block",  // more words the search finds it by
//     fields: [],                     // as describeField gives them, or (context) => them
//     when: (context, each) => true,  // offered only when this is true
//     forEach: (context) => [...],    // one item for each of these (a task manager, a tab)
//     confirm: null,                  // or {title, message, confirmLabel, danger}, or a function
//     closes: true,                   // whether the palette closes after it runs
//     run: async (params, context, each) => {},
//     task: null,                     // or "newfile": what Shift+Enter queues
//   });
//
// `context` is what the shell hands the palette (see `Palette`): the task
// managers' states, the rack's, the column names, the theme and its toggle, the
// log, the saved sequences, the shortcuts' help and a way to ask to confirm.
import { get, loadSequence, managerAction } from "./api.js";
import { showLog } from "./dock/logs.js";
import { TAB_KEYS } from "./shortcuts.js";

const registered = new Map(); // by name, in the order registered

export function registerAction(action) {
  registered.set(action.name, action);
}

export function actions() {
  return [...registered.values()];
}

const send = (name, detail) => window.dispatchEvent(new CustomEvent(name, { detail }));
const title = (name) => name.charAt(0).toUpperCase() + name.slice(1);
const call = (value, ...args) => (typeof value === "function" ? value(...args) : value);

// Sends a page event that answers through `detail.done(problem)`, and throws
// the problem, if any, so the palette's form shows it.
function ask(name, detail) {
  let problem = null;
  let answered = false;
  send(name, {
    ...detail,
    done: (p) => {
      answered = true;
      problem = p;
    },
  });
  if (!answered) throw new Error("The plots aren't showing yet.");
  if (problem) throw new Error(problem);
}

// The endpoint that queues a task on a task manager (see forms.js' taskEndpoints).
export const taskPath = (manager, task) =>
  manager === "main" ? `/tasks/${task}` : `/managers/${manager}/tasks/${task}`;

// The actions as palette items (see palette.js), for the context. `tasks` are
// the main task manager's task endpoints, by name ("newfile"), for the actions
// that name one: its inputs are the action's.
export function actionItems(context, tasks = {}) {
  const items = [];
  for (const action of registered.values()) {
    const each = action.forEach ? action.forEach(context) : [undefined];
    for (const one of each) {
      if (action.when && !action.when(context, one)) continue;
      const task = action.task ? tasks[action.task] : null;
      const label = call(action.label, context, one);
      const fields = task ? task.fields : (call(action.fields, context, one) ?? []);
      items.push({
        id: one === undefined ? `action:${action.name}` : `action:${action.name}:${one}`,
        kind: "action",
        label,
        tag: action.tag,
        text: `${label} ${action.description ?? ""} ${action.keywords ?? ""} ${action.tag}`,
        description: action.description ?? "",
        fields,
        submitLabel: "Run",
        run: (params) => action.run(params, context, one),
        queue: task ? (params, manager) => get(taskPath(manager, action.task), { params }) : null,
        confirm: call(action.confirm, context, one) ?? null,
        closes: action.closes ?? true,
      });
    }
  }
  return items;
}

// ------------------------------------------------------------ the built-in ones
const managerNames = (context) => Object.keys(context.managers ?? { main: null });
const managerLabel = (context, name) => (managerNames(context).length > 1 ? ` (${title(name)})` : "");
const stateOf = (context, name) => context.managers?.[name] ?? {};
const queueWord = (context, name) =>
  managerNames(context).length > 1 ? `the ${title(name)} queue` : "the queue";

registerAction({
  name: "new-file",
  label: "New data file",
  tag: "Experiment",
  description: "Start a new data file now, with this title.",
  keywords: "scribe next step block title",
  task: "newfile",
  run: (params) =>
    get("/scribe/next_file", {
      params: { title: params.file_name, next_block: params.increment_block ?? "false" },
    }),
});

registerAction({
  name: "pause-measurements",
  label: "Pause measurements",
  tag: "Experiment",
  description: "Stop measuring and writing rows until they are resumed.",
  keywords: "rack stop hold",
  task: "pausemeasurements",
  when: (context) => context.rack?.paused === false,
  run: async (_, context) => {
    await get("/rack/pause/");
    context.refreshRack?.();
  },
});

registerAction({
  name: "resume-measurements",
  label: "Resume measurements",
  tag: "Experiment",
  description: "Start measuring and writing rows again.",
  keywords: "rack start continue",
  task: "resumemeasurements",
  when: (context) => context.rack?.paused === true,
  run: async (_, context) => {
    await get("/rack/resume/");
    context.refreshRack?.();
  },
});

registerAction({
  name: "set-period",
  label: "Set measurement period",
  tag: "Experiment",
  description: "The time between measurements, in seconds.",
  keywords: "rack interval rate every seconds",
  task: "setmeasurementperiod",
  run: async (params, context) => {
    await get("/rack/period/set/", { params: { period: params.period } });
    context.refreshRack?.();
  },
});

registerAction({
  name: "pause-queue",
  label: (context, name) => `Pause queue${managerLabel(context, name)}`,
  tag: "Queue",
  description: "Hold the queue: the running task pauses, and nothing new starts.",
  keywords: "task manager hold",
  forEach: managerNames,
  when: (context, name) => stateOf(context, name).status !== "Paused",
  run: (_, context, name) => managerAction(name, "pause").then(() => context.refreshManagers?.()),
});

registerAction({
  name: "resume-queue",
  label: (context, name) => `Resume queue${managerLabel(context, name)}`,
  tag: "Queue",
  description: "Let the queue carry on.",
  keywords: "task manager continue start",
  forEach: managerNames,
  when: (context, name) => stateOf(context, name).status === "Paused",
  run: (_, context, name) => managerAction(name, "resume").then(() => context.refreshManagers?.()),
});

registerAction({
  name: "abort",
  label: (context, name) => `Abort running task${managerLabel(context, name)}`,
  tag: "Queue",
  description: "Stop the running task, which tidies up after itself, and pause its queue.",
  keywords: "stop cancel task",
  forEach: managerNames,
  when: (context, name) => !!stateOf(context, name).current_task,
  confirm: (context, name) => ({
    title: `Abort ${stateOf(context, name).current_task?.name}?`,
    message:
      `The task stops at its next step and runs its teardown. ${title(queueWord(context, name))} ` +
      "is then paused, so nothing else starts until you resume it.",
    confirmLabel: "Abort",
    danger: true,
  }),
  run: (_, context, name) => managerAction(name, "abort").then(() => context.refreshManagers?.()),
});

registerAction({
  name: "clear-queue",
  label: (context, name) => `Clear queue${managerLabel(context, name)}`,
  tag: "Queue",
  description: "Remove the tasks waiting. A running task carries on.",
  keywords: "empty remove tasks",
  forEach: managerNames,
  when: (context, name) => (stateOf(context, name).queue?.length ?? 0) > 0,
  confirm: (context, name) => {
    const count = stateOf(context, name).queue.length;
    return {
      title: `Clear ${queueWord(context, name)}?`,
      message: `This removes the ${count === 1 ? "task" : `${count} tasks`} waiting. A running task carries on.`,
      confirmLabel: "Clear queue",
      danger: true,
    };
  },
  run: (_, context, name) => managerAction(name, "clear_tasks").then(() => context.refreshManagers?.()),
});

registerAction({
  name: "load-sequence",
  label: "Load saved sequence",
  tag: "Queue",
  description: "Add a saved sequence's tasks to the end of a queue.",
  keywords: "sequences saved tasks",
  when: (context) => (context.sequences?.length ?? 0) > 0,
  fields: (context) => {
    const names = context.sequences.map((s) => s.name);
    const managers = managerNames(context);
    const fields = [
      { name: "name", title: "Sequence", type: "choice", required: true, choices: names, labels: names,
        description: "" },
    ];
    if (managers.length > 1) {
      fields.push({ name: "manager", title: "Queue", type: "choice", required: false, default: "main",
        choices: managers, labels: managers.map(title), description: "" });
    }
    return fields;
  },
  run: async (params, context) => {
    await loadSequence(params.name, params.manager ?? "main");
    context.refreshManagers?.();
  },
});

const TAB_NAMES = { values: "Values", queue: "Queue", instruments: "Instruments", logs: "Logs" };
registerAction({
  name: "open-tab",
  label: (_, tab) => `Open the ${TAB_NAMES[tab]} tab`,
  tag: "View",
  description: "Show this tab of the dock.",
  keywords: "dock",
  forEach: () => TAB_KEYS,
  run: (_, __, tab) => send("pyacquisition:open-tab", tab),
});

registerAction({
  name: "toggle-dock",
  label: "Hide or show the dock",
  tag: "View",
  description: "The tabs under the plots.",
  keywords: "values queue instruments logs collapse",
  run: () => send("pyacquisition:toggle-dock"),
});

registerAction({
  name: "toggle-hold",
  label: "Hold the plots, or follow the data",
  tag: "View",
  description: "Every plot stays where it is, or follows the data again.",
  keywords: "freeze autoscale space",
  run: () => send("pyacquisition:toggle-hold"),
});

registerAction({
  name: "add-plot",
  label: "Add a plot",
  tag: "Plot",
  description: "Another plot, against the same x as the first.",
  keywords: "panel chart graph new",
  run: () => ask("pyacquisition:add-plot", {}),
});

registerAction({
  name: "add-series",
  label: "Add a column to a plot",
  tag: "Plot",
  description: "Plot one more column, on the plot numbered here.",
  keywords: "series trace chart graph",
  when: (context) => (context.columns?.length ?? 0) > 0,
  fields: (context) => [
    { name: "column", title: "Column", type: "choice", required: true, choices: context.columns,
      labels: context.columns, description: "" },
    { name: "plot", title: "Plot", type: "integer", required: false, default: 1,
      description: "Which plot, counting from 1." },
  ],
  run: (params) => ask("pyacquisition:add-series", { column: params.column, plot: Number(params.plot ?? 1) }),
});

registerAction({
  name: "theme",
  label: (context) => `Switch to the ${context.theme === "dark" ? "light" : "dark"} theme`,
  tag: "View",
  description: "The light or dark look.",
  keywords: "dark light colours",
  run: (_, context) => context.toggleTheme?.(),
});

// The newest error (or exception) in the log, if there is one.
export function lastError(logs) {
  const entries = logs?.entries ?? [];
  for (let i = entries.length - 1; i >= 0; i--) {
    if (entries[i].level === "error" || entries[i].level === "exception") return entries[i];
  }
  return null;
}

registerAction({
  name: "last-error",
  label: "Go to the last error",
  tag: "View",
  description: "Show the newest error in the Logs tab.",
  keywords: "logs problem failed exception",
  when: (context) => !!lastError(context.logs),
  run: (_, context) => {
    send("pyacquisition:open-tab", "logs");
    showLog(lastError(context.logs).seq);
  },
});

registerAction({
  name: "data-folder",
  label: "Open the data folder",
  tag: "Experiment",
  description: "Where the data files are written, in the file explorer.",
  keywords: "files directory explorer",
  when: () => !!window.pywebview?.api?.open_data_folder,
  run: () => window.pywebview.api.open_data_folder(),
});

registerAction({
  name: "shortcuts",
  label: "Show keyboard shortcuts",
  tag: "View",
  description: "The keys and what they do.",
  keywords: "help keys",
  run: (_, context) => context.showHelp?.(),
});

registerAction({
  name: "shut-down",
  label: "Shut down the experiment",
  tag: "Experiment",
  description: "Stop measuring and close the experiment, after asking.",
  keywords: "stop quit exit close",
  run: () => window.pyacquisition.requestClose("button"), // its dialog asks first
});
