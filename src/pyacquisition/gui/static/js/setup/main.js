// The setup page (`pyacquisition new`), served by the setup server (core/setup.py).
// A placeholder for now: it shows the config file, and Run starts the experiment
// from it, in the same window.

const RUN_TIMEOUT = 120_000; // ms to wait for the experiment to answer, after Run
const POLL_PERIOD = 500; // ms between checks meanwhile

const $ = (id) => document.getElementById(id);
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function getJSON(url) {
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) throw new Error(`${url} answered ${response.status}`);
  return (await response.json()).data;
}

// Whether a server answers at `url`. One on another port answers opaquely,
// which is enough: the setup server isn't there.
async function answers(url, sameOrigin) {
  try {
    const response = await fetch(
      url,
      sameOrigin ? { cache: "no-store" } : { cache: "no-store", mode: "no-cors" },
    );
    return sameOrigin ? response.ok : true;
  } catch {
    return false; // refused: nothing there yet
  }
}

// After Run: goes to the experiment's page once it answers. If it stops before
// it starts, the setup server comes back, with the reason, and the page reloads
// to show it.
async function followRun(port) {
  const base = `${location.protocol}//${location.hostname}:${port}`;
  const sameOrigin = base === location.origin;
  const deadline = Date.now() + RUN_TIMEOUT;
  while (Date.now() < deadline) {
    await sleep(POLL_PERIOD);
    if (await answers(`${base}/experiment/info`, sameOrigin)) {
      location.href = `${base}/ui/`;
      return;
    }
    try {
      if ((await getJSON("/setup/config")).error) {
        location.reload();
        return;
      }
    } catch {
      // The setup server has gone, as it should while the experiment starts.
    }
  }
  $("setup-status").textContent =
    `The experiment hasn't answered at ${base}. See the console for why.`;
}

async function run() {
  $("setup-run").disabled = true;
  $("setup-error").hidden = true;
  $("setup-status").textContent = "Starting the experiment…";
  try {
    const response = await fetch("/setup/run", { method: "POST" });
    if (!response.ok) throw new Error(`Run answered ${response.status}`);
    await followRun((await response.json()).data.port);
  } catch (error) {
    $("setup-status").textContent = `Couldn't start the experiment: ${error.message}`;
    $("setup-run").disabled = false;
  }
}

// The window's close button (see gui/window.py): nothing is lost by closing yet.
window.pyacquisition = {
  ...window.pyacquisition,
  requestClose() {
    fetch("/setup/shutdown")
      .catch(() => {})
      .finally(() => window.pywebview?.api?.close());
    return true;
  },
};

async function start() {
  try {
    const setup = await getJSON("/setup/config");
    $("setup-path").textContent = setup.path;
    if (setup.error) {
      $("setup-error").textContent = `The experiment didn't start: ${setup.error}`;
      $("setup-error").hidden = false;
    }
    $("setup-run").disabled = false;
  } catch (error) {
    $("setup-status").textContent = `The setup server doesn't answer: ${error.message}`;
  }
}

$("setup-run").addEventListener("click", run);
start();
