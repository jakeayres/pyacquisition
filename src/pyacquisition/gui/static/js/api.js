// Requests to the experiment's API server, which also serves this page.

export async function get(path, { params, timeout = 5000 } = {}) {
  const query = params ? `?${new URLSearchParams(params)}` : "";
  const response = await fetch(`${path}${query}`, {
    signal: AbortSignal.timeout(timeout),
  });
  if (!response.ok) throw await failure(path, response);
  return response.json();
}

// The error for a request that failed, saying what the server said: FastAPI
// gives a bad input as a list of problems, each naming the input, which are
// also kept as `error.problems` ([{name, message}]) so a form can show each by
// its field. Any other reason it gives as text is shown as it is.
async function failure(path, response) {
  const status = response.status;
  try {
    const { detail } = await response.json();
    if (typeof detail === "string") return new Error(detail);
    if (Array.isArray(detail)) {
      const problems = detail.map((problem) => {
        const where = (problem?.loc ?? []).map(String);
        const name = ["query", "path"].includes(where[0]) ? where.at(-1) : "";
        return { name, message: problem?.msg ?? "invalid" };
      });
      const error = new Error(
        problems.map((p) => (p.name ? `${p.name}: ${p.message}` : p.message)).join("\n"),
      );
      error.problems = problems;
      return error;
    }
  } catch {
    // Not JSON: fall through to the status.
  }
  if (status >= 500) {
    return new Error(`The server had an error handling the request (HTTP ${status}).`);
  }
  return new Error(`${path} failed with status ${status}`);
}

// Posts `body` as JSON, and gives the JSON answer.
export async function post(path, body, { timeout = 5000 } = {}) {
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(timeout),
  });
  if (!response.ok) throw await failure(path, response);
  return response.json();
}

// A Python script that draws a plot with matplotlib, from its settings (see
// /experiment/plot_script): {x, series: [{name, colour}], marks, log_x, log_y,
// x_limits, y_limits, previous}.
export async function plotScript(body) {
  const { data } = await post("/experiment/plot_script", body);
  return data;
}

export async function getBinary(path, { params, timeout = 5000 } = {}) {
  const query = params ? `?${new URLSearchParams(params)}` : "";
  const response = await fetch(`${path}${query}`, {
    signal: AbortSignal.timeout(timeout),
  });
  if (!response.ok) throw await failure(path, response);
  return response.arrayBuffer();
}

// The address of a websocket on the server that served this page.
export function websocketUrl(path) {
  const scheme = location.protocol === "https:" ? "wss:" : "ws:";
  return `${scheme}//${location.host}${path}`;
}

// Each column's kind, source and unit (see /experiment/columns).
export async function columnInfo() {
  const { data } = await get("/experiment/columns");
  return data;
}

// Whether the experiment answers.
export async function ping() {
  try {
    return (await get("/ping", { timeout: 1000 })) === "pong";
  } catch {
    return false;
  }
}

// Every task manager's state, by name, main first (see /managers/state): its
// status, running task, whether it is aborting, its last result and its queue.
export async function managerStates() {
  const { data } = await get("/managers/state", { timeout: 3000 });
  return data;
}

// The address of an action on a task manager: the main one keeps the original
// paths (/task_manager/...), and the others are under /managers/<name>/.
export const managerPath = (name, action) =>
  name === "main"
    ? `/task_manager/${action}`
    : `/managers/${encodeURIComponent(name)}/${action}`;

// pause, resume, abort, clear_tasks, remove_queued_task or move_queued_task.
export const managerAction = (name, action, params) =>
  get(managerPath(name, action), { params });

// Saved sequences (see core/sequences.py): [{name, saved, tasks}].
export async function sequences() {
  const { data } = await get("/sequences");
  return data;
}

// Saves a task manager's queue as a sequence: {saved, skipped}. A name that is
// taken fails with status 409, unless `overwrite`.
export async function saveSequence(name, manager, { includeRunning = true, overwrite = false } = {}) {
  const query = new URLSearchParams({ name, manager, include_running: includeRunning, overwrite });
  const response = await fetch(`/sequences/save?${query}`, { signal: AbortSignal.timeout(5000) });
  if (!response.ok) {
    const error = await failure("/sequences/save", response);
    error.status = response.status;
    throw error;
  }
  return response.json();
}

export const loadSequence = (name, manager) => get("/sequences/load", { params: { name, manager } });
export const deleteSequence = (name) => get("/sequences/delete", { params: { name } });

// The running task of each task manager, as "name" for the main one and
// "name (manager)" for the others.
export async function runningTasks() {
  const { data } = await get("/managers/state", { timeout: 2000 });
  return Object.entries(data)
    .filter(([, state]) => state.current_task)
    .map(([manager, state]) =>
      manager === "main"
        ? state.current_task.name
        : `${state.current_task.name} (${manager})`,
    );
}

// What the interface shows about the experiment, such as its name.
export async function experimentInfo() {
  const { data } = await get("/experiment/info");
  return data;
}

export async function shutdownExperiment() {
  await get("/experiment/shutdown");
}

// Where the data is written, and what the next file would be called (see
// /scribe/state).
export async function scribeState() {
  const { data } = await get("/scribe/state");
  return data;
}

export async function nextFile(title, nextBlock = false) {
  await get("/scribe/next_file", { params: { title, next_block: nextBlock } });
}

// {paused, period}
export async function rackState() {
  const { paused, period, loop_time } = await get("/rack/state", { timeout: 2000 });
  return { paused, period, loop_time };
}

export const pauseRack = () => get("/rack/pause/");
export const resumeRack = () => get("/rack/resume/");
export const setRackPeriod = (period) => get("/rack/period/set/", { params: { period } });
