// The setup page (`pyacquisition new`): an experiment's config, built from
// forms, with the file it makes shown beside them and checked as it changes.
// Sections down the left, the one picked in the middle, and the file on the right.
import { useEffect, useRef, useState } from "preact/hooks";
import { html } from "../html.js";
import { useTheme } from "../theme.js";
import { ConfirmDialog } from "../confirm.js";
import { LogoMark, MoonIcon, PlayIcon, SunIcon } from "../icons.js";
import * as api from "./api.js";
import { InstrumentsSection } from "./instruments.js";
import { MeasurementsSection } from "./measurements.js";
import { OptionsSection } from "./options.js";
import { Preview } from "./preview.js";

const CHECK_AFTER = 250; // ms after the last change before it is checked
const RUN_TIMEOUT = 120_000; // ms to wait for the experiment to answer, after Run
const POLL_PERIOD = 500; // ms between checks meanwhile

const SECTIONS = [
  { id: "instruments", label: "Instruments" },
  { id: "measurements", label: "Measurements" },
  { id: "options", label: "Options" },
];

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

// Whether a server answers at `url`. One on another port answers opaquely,
// which is enough: the setup server isn't there.
async function answers(url, sameOrigin) {
  try {
    const response = await fetch(url, {
      cache: "no-store",
      ...(sameOrigin ? {} : { mode: "no-cors" }),
    });
    return sameOrigin ? response.ok : true;
  } catch {
    return false;
  }
}

// After Run: goes to the experiment's page once it answers. If it stops before
// it starts, the setup server comes back with the reason, and the page reloads
// to show it.
async function followRun(port) {
  const base = `${location.protocol}//${location.hostname}:${port}`;
  const sameOrigin = base === location.origin;
  const deadline = Date.now() + RUN_TIMEOUT;
  while (Date.now() < deadline) {
    await sleep(POLL_PERIOD);
    if (await answers(`${base}/experiment/info`, sameOrigin)) {
      location.href = `${base}/ui/`;
      return true;
    }
    try {
      if ((await api.setupConfig()).error) {
        location.reload();
        return true;
      }
    } catch {
      // The setup server has gone, as it should while the experiment starts.
    }
  }
  return false;
}

// The config, checked a moment after each change: {checked, stale}, where
// `stale` says the config has changed since.
function useChecked(config) {
  const [checked, setChecked] = useState(null);
  const [checkedFor, setCheckedFor] = useState(null);
  const text = JSON.stringify(config);
  useEffect(() => {
    if (config === null) return;
    let current = true;
    const timer = setTimeout(async () => {
      try {
        const result = await api.check(config);
        if (current) {
          setChecked(result);
          setCheckedFor(text);
        }
      } catch {
        // Not answering: the next change tries again.
      }
    }, CHECK_AFTER);
    return () => {
      current = false;
      clearTimeout(timer);
    };
  }, [text]);
  return { checked, stale: checkedFor !== text };
}

function TopBar({ setup, dirty, status, canSave, canRun, onSave, onRun, theme, onToggleTheme }) {
  const next = theme === "dark" ? "light" : "dark";
  return html`
    <header class="topbar">
      <div class="brand" title="PyAcquisition">
        <${LogoMark} />
        <span class="brand-name">Setup</span>
      </div>
      <div class="topbar-middle">
        <span class="setup-path" title=${setup.path}>${setup.path}</span>
        <span class="setup-status" role="status">
          ${status || (dirty ? "Unsaved changes" : setup.exists ? "Saved" : "Not saved yet")}
        </span>
      </div>
      <div class="topbar-actions">
        <button
          class="icon-button"
          aria-label="Switch to the ${next} theme"
          title="Switch to the ${next} theme"
          onClick=${onToggleTheme}
        >
          ${theme === "dark" ? html`<${SunIcon} />` : html`<${MoonIcon} />`}
        </button>
        <button
          class="button button-small ${canSave ? "button-primary" : ""}"
          disabled=${!canSave}
          onClick=${onSave}
        >
          Save
        </button>
        <button
          class="button button-small button-primary"
          disabled=${!canRun}
          title=${canRun ? "Start the experiment from the file" : "Save the file, with no problems, to run it"}
          onClick=${onRun}
        >
          <${PlayIcon} /> Run
        </button>
      </div>
    </header>
  `;
}

export function App() {
  const { theme, toggle } = useTheme();
  const [described, setDescribed] = useState(null);
  const [setup, setSetup] = useState(null);
  const [config, setConfig] = useState(null);
  // The config as the file has it, as JSON: for a file not made yet, as it began.
  const [saved, setSaved] = useState(null);
  const [failure, setFailure] = useState("");
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);
  const [asking, setAsking] = useState(false); // whether to close without saving
  const [closed, setClosed] = useState(false);
  const [section, setSection] = useState(SECTIONS[0].id);
  const { checked, stale } = useChecked(config);

  useEffect(() => {
    Promise.all([api.describe(), api.setupConfig()]).then(
      ([d, s]) => {
        setDescribed(d);
        setSetup(s);
        setConfig(s.config);
        setSaved(JSON.stringify(s.config));
      },
      (e) => setFailure(`The setup server doesn't answer: ${e.message}`),
    );
  }, []);

  const dirty = config !== null && JSON.stringify(config) !== saved;
  const problems = checked?.problems ?? [];
  const clean = checked !== null && !stale && problems.length === 0;
  const canSave = !busy && dirty && clean;
  const canRun = !busy && !dirty && setup?.exists && clean;

  // The window's close button (see gui/window.py) asks first if there are
  // unsaved changes. So does closing a browser tab.
  const dirtyRef = useRef(dirty);
  dirtyRef.current = dirty;
  useEffect(() => {
    window.pyacquisition = {
      ...window.pyacquisition,
      requestClose() {
        if (dirtyRef.current) setAsking(true);
        else close();
        return true;
      },
    };
    const onBeforeUnload = (event) => {
      if (dirtyRef.current) event.preventDefault();
    };
    window.addEventListener("beforeunload", onBeforeUnload);
    return () => window.removeEventListener("beforeunload", onBeforeUnload);
  }, []);

  const close = async () => {
    setAsking(false);
    await api.shutdown();
    if (window.pywebview?.api) window.pywebview.api.close();
    else setClosed(true); // a browser tab, which only its user can close
  };

  const save = async () => {
    setBusy(true);
    setStatus("Saving…");
    try {
      const result = await api.save(config);
      if (result.ok) {
        setSaved(JSON.stringify(config));
        setSetup((s) => ({ ...s, exists: true }));
        setStatus("");
      } else {
        setStatus("Not saved: it has problems.");
      }
    } catch (e) {
      setStatus(`Not saved: ${e.message}`);
    } finally {
      setBusy(false);
    }
  };

  const runExperiment = async () => {
    setBusy(true);
    setStatus("Starting the experiment…");
    try {
      if (!(await followRun(await api.run()))) {
        setStatus("The experiment hasn't answered. See the console for why.");
      }
    } catch (e) {
      setStatus(`Couldn't start the experiment: ${e.message}`);
      setBusy(false);
    }
  };

  if (failure) return html`<p class="setup-failure" role="alert">${failure}</p>`;
  if (closed) {
    return html`
      <div class="empty-state">
        <h2>The setup page has closed</h2>
        <p>You can close this tab.</p>
      </div>
    `;
  }
  if (!described || !setup) return html`<p class="setup-note setup-loading">Loading…</p>`;

  return html`
    <div class="setup-app">
      <${TopBar}
        setup=${setup}
        dirty=${dirty}
        status=${status}
        canSave=${canSave}
        canRun=${canRun}
        onSave=${save}
        onRun=${runExperiment}
        theme=${theme}
        onToggleTheme=${toggle}
      />
      ${setup.error &&
      html`<p class="setup-banner" role="alert">The experiment didn't start: ${setup.error}</p>`}
      <div class="setup-body">
        <nav class="setup-nav" aria-label="Sections">
          ${SECTIONS.map(
            (s) => html`
              <button
                class="setup-nav-item"
                aria-current=${section === s.id ? "page" : undefined}
                onClick=${() => setSection(s.id)}
              >
                ${s.label}
              </button>
            `,
          )}
        </nav>
        <main class="setup-main">
          ${section === "instruments" &&
          html`<${InstrumentsSection}
            described=${described}
            config=${config}
            problems=${problems}
            onChange=${setConfig}
          />`}
          ${section === "measurements" &&
          html`<${MeasurementsSection}
            described=${described}
            config=${config}
            problems=${problems}
            onChange=${setConfig}
          />`}
          ${section === "options" &&
          html`<${OptionsSection}
            options=${described.options}
            config=${config}
            problems=${problems}
            onChange=${setConfig}
          />`}
        </main>
        <${Preview} checked=${checked} stale=${stale} />
      </div>
    </div>
    ${asking &&
    html`
      <${ConfirmDialog}
        title="Close without saving?"
        confirmLabel="Close without saving"
        danger
        onConfirm=${close}
        onCancel=${() => setAsking(false)}
      >
        <p>The changes you haven't saved will be lost.</p>
      <//>
    `}
  `;
}
