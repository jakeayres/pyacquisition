// The experiment's controls, in the top bar: the data file (and starting a new
// one), the measurements (pause, resume and how often), and shutting down.
import { useEffect, useRef, useState } from "preact/hooks";
import { html } from "./html.js";
import { usePolled, usePopover } from "./hooks.js";
import {
  nextFile,
  pauseRack,
  rackState,
  resumeRack,
  scribeState,
  setRackPeriod,
} from "./api.js";
import {
  CopyIcon,
  FileIcon,
  FolderIcon,
  PauseIcon,
  PlayIcon,
  PowerIcon,
} from "./icons.js";

const RACK_CHECK = 2000; // milliseconds between checks of the measurements
// Characters a data file's title can't have, as the server checks too
// (core/scribe.py).
const FORBIDDEN = '<>:"/\\|?*';

// What is wrong with a title, or "" if it can be used.
export function titleProblem(title) {
  if (!title.trim()) return "Give the file a title.";
  const bad = [...new Set([...title].filter((c) => FORBIDDEN.includes(c) || c < " "))];
  if (bad.length) return `A title can't contain ${bad.join(" ")}`;
  return "";
}

// A period in seconds, as it is shown: "0.25 s", "2 s".
export const formatPeriod = (seconds) => `${Number(seconds.toPrecision(3))} s`;

// Whether the measurements are paused, and their period, checked every so often
// while connected (something else, such as a task, may change them), and at
// once after a change made here.
export function useRack(connection) {
  const { value, refresh } = usePolled(connection, rackState, RACK_CHECK);
  return { state: value, refresh };
}

// Where the data is written (see /scribe/state), fetched on connecting and
// whenever the data file changes (`file`, from the data stream).
export function useScribe(connection, file) {
  const [state, setState] = useState(null);
  useEffect(() => {
    if (connection !== "connected") return;
    scribeState().then(setState, () => {});
  }, [connection, file]);
  return state;
}

// A button in the top bar that opens a small panel under it.
function TopbarMenu({ label, title, className = "", button, children, open, setOpen }) {
  const menu = useRef(null);
  usePopover(menu, open, () => setOpen(false));
  // The panel's first field takes the focus as it opens.
  useEffect(() => {
    if (open) menu.current?.querySelector(".popover [autofocus]")?.focus();
  }, [open]);
  return html`
    <div class="topbar-menu ${className}" ref=${menu}>
      <button
        class="topbar-chip"
        aria-label=${label}
        aria-expanded=${open}
        title=${title}
        onClick=${() => setOpen(!open)}
      >
        ${button}
      </button>
      ${open &&
      html`<div class="popover" role="dialog" aria-label=${label}>${children}</div>`}
    </div>
  `;
}

// The data file: its name in the top bar, and under it the folder and a form
// to start a new file.
export function FileControl({ scribe, file }) {
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [newBlock, setNewBlock] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);
  const shown = file ?? scribe?.file;

  const toggle = (next) => {
    setOpen(next);
    if (next) {
      setError("");
      setCopied(false);
    }
  };

  const problem = titleProblem(title);
  const pattern = scribe?.[newBlock ? "next_block" : "next_step"];
  const next = pattern && !problem ? pattern.replace("{title}", title) : null;

  const start = async () => {
    if (problem) return setError(problem);
    setBusy(true);
    try {
      await nextFile(title, newBlock);
      setTitle("");
      setNewBlock(false);
      setOpen(false);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(scribe.directory);
      setCopied(true);
    } catch {
      // Not allowed here; the path can still be selected and copied by hand.
    }
  };

  const canOpenFolder = !!window.pywebview?.api?.open_data_folder;

  return html`
    <${TopbarMenu}
      className="file-control"
      label="Data file"
      title=${scribe ? `${shown ?? "No data file"}, in ${scribe.directory}` : "Data file"}
      open=${open}
      setOpen=${toggle}
      button=${html`
        <${FileIcon} />
        <span class="topbar-chip-text">${shown ?? "No data file"}</span>
      `}
    >
      <div class="popover-section">
        <div class="popover-label">Folder</div>
        <div class="folder-row">
          <span class="folder-path">${scribe?.directory ?? "…"}</span>
          <button
            class="icon-button"
            aria-label="Copy the folder's path"
            title="Copy the path"
            disabled=${!scribe}
            onClick=${copy}
          >
            <${CopyIcon} />
          </button>
          ${canOpenFolder &&
          html`
            <button
              class="icon-button"
              aria-label="Open the folder"
              title="Open the folder"
              onClick=${() => window.pywebview.api.open_data_folder()}
            >
              <${FolderIcon} />
            </button>
          `}
        </div>
        ${copied && html`<span class="popover-note" role="status">Copied</span>`}
      </div>
      <form
        class="popover-section"
        onSubmit=${(event) => {
          event.preventDefault();
          start();
        }}
      >
        <div class="popover-label">New file</div>
        <label class="field">
          <span>Title</span>
          <input
            class="text-input"
            autofocus
            value=${title}
            placeholder="sweep up"
            onInput=${(event) => {
              setTitle(event.currentTarget.value);
              setError("");
            }}
          />
        </label>
        <label class="check">
          <input
            type="checkbox"
            checked=${newBlock}
            onChange=${(event) => setNewBlock(event.currentTarget.checked)}
          />
          Start a new block
        </label>
        <p class="popover-note">
          ${next ? html`Next file: <span class="file-name">${next}</span>` : " "}
        </p>
        ${error && html`<p class="popover-error" role="alert">${error}</p>`}
        <div class="popover-buttons">
          <button type="button" class="button" onClick=${() => setOpen(false)}>Cancel</button>
          <button type="submit" class="button button-primary" disabled=${busy}>
            ${busy ? "Starting…" : "Start new file"}
          </button>
        </div>
      </form>
    <//>
  `;
}

// The measurements: whether they are running and how often, with a button to
// pause or resume them, and a panel to change the period.
export function RackControl({ rack, onChanged }) {
  const [open, setOpen] = useState(false);
  const [period, setPeriod] = useState("");
  const [error, setError] = useState("");
  const paused = rack?.paused ?? false;

  const toggle = (next) => {
    setOpen(next);
    if (next) {
      setPeriod(rack ? String(rack.period) : "");
      setError("");
    }
  };

  const pauseOrResume = async () => {
    try {
      await (paused ? resumeRack() : pauseRack());
    } finally {
      onChanged();
    }
  };

  const apply = async () => {
    const seconds = Number(period);
    if (period.trim() === "" || !(seconds > 0) || !isFinite(seconds)) {
      return setError("Give a number of seconds above zero.");
    }
    try {
      await setRackPeriod(seconds);
      setOpen(false);
    } catch (e) {
      setError(e.message);
    } finally {
      onChanged();
    }
  };

  const status = !rack ? "…" : paused ? "Paused" : `Every ${formatPeriod(rack.period)}`;
  return html`
    <div class="rack-control" data-paused=${paused}>
      <${TopbarMenu}
        label="Measurements"
        title=${paused ? "Measurements are paused" : "Measuring"}
        open=${open}
        setOpen=${toggle}
        button=${html`
          <span class="rack-dot" aria-hidden="true"></span>
          <span class="topbar-chip-text">${status}</span>
        `}
      >
        <form
          class="popover-section"
          onSubmit=${(event) => {
            event.preventDefault();
            apply();
          }}
        >
          <div class="popover-label">Measurement period</div>
          <div class="period-row">
            <input
              class="text-input period-input"
              aria-label="Seconds between measurements"
              inputmode="decimal"
              autofocus
              value=${period}
              onInput=${(event) => {
                setPeriod(event.currentTarget.value);
                setError("");
              }}
            />
            <span class="period-unit">s</span>
            <button type="submit" class="button button-primary">Apply</button>
          </div>
          ${error && html`<p class="popover-error" role="alert">${error}</p>`}
        </form>
      <//>
      <button
        class="icon-button"
        aria-label=${paused ? "Resume measurements" : "Pause measurements"}
        title=${paused ? "Resume measurements" : "Pause measurements"}
        disabled=${!rack}
        onClick=${pauseOrResume}
      >
        ${paused ? html`<${PlayIcon} />` : html`<${PauseIcon} />`}
      </button>
    </div>
  `;
}

// Shuts the experiment down, after asking (close-dialog.js).
export function ShutdownButton() {
  return html`
    <button
      class="icon-button shutdown-button"
      aria-label="Stop the experiment"
      title="Stop the experiment"
      onClick=${() => window.pyacquisition.requestClose("button")}
    >
      <${PowerIcon} />
    </button>
  `;
}
