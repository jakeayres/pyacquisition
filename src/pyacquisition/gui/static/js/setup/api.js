// Requests to the setup server (core/setup.py), which serves this page.
import { get } from "../api.js";

export const describe = async () => (await get("/setup/describe")).data;
export const setupConfig = async () => (await get("/setup/config", { timeout: 10000 })).data;

// A config sent as JSON. Answers with {status, data}; a refusal (422) is an
// answer too, with the problems in its data.
async function post(path, body, { timeout = 10000 } = {}) {
  const response = await fetch(path, {
    method: "POST",
    headers: body === undefined ? {} : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
    signal: AbortSignal.timeout(timeout),
  });
  if (!response.ok && response.status !== 422) {
    throw new Error(`${path} answered ${response.status}`);
  }
  return { ok: response.ok, ...(await response.json()) };
}

// {problems: [{where, message}], toml}
export const check = async (config) => (await post("/setup/check", config)).data;
// {ok, data: {problems, toml}}
export const save = (config) => post("/setup/save", config);
// {reply, matches, expected, missing, error} for an instrument asked *IDN?.
export const test = async (instrument) =>
  (await post("/setup/test", instrument, { timeout: 30000 })).data;
// The port the experiment will listen on.
export const run = async () => (await post("/setup/run")).data.port;
export const shutdown = () => fetch("/setup/shutdown").catch(() => {});
