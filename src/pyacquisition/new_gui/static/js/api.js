// Requests to the experiment's API server, which also serves this page.

export async function get(path, { params, timeout = 5000 } = {}) {
  const query = params ? `?${new URLSearchParams(params)}` : "";
  const response = await fetch(`${path}${query}`, {
    signal: AbortSignal.timeout(timeout),
  });
  if (!response.ok) throw await failure(path, response);
  return response.json();
}

// The error for a request that failed: the server's own reason where it gives
// one as text (FastAPI's `detail`), which is worth showing as it is.
async function failure(path, response) {
  try {
    const { detail } = await response.json();
    if (typeof detail === "string") return new Error(detail);
  } catch {
    // Not JSON: fall through to the status.
  }
  return new Error(`${path} failed with status ${response.status}`);
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
  const { paused, period } = await get("/rack/state", { timeout: 2000 });
  return { paused, period };
}

export const pauseRack = () => get("/rack/pause/");
export const resumeRack = () => get("/rack/resume/");
export const setRackPeriod = (period) => get("/rack/period/set/", { params: { period } });
