// The app shell: a slim top bar, the plot area filling the window, and the dock.
import { useEffect, useState } from "preact/hooks";
import { html } from "./html.js";
import { columnInfo, experimentInfo } from "./api.js";
import { DataStore } from "./store.js";
import { LogStore } from "./logs.js";
import { dataFeed, logFeed } from "./feed.js";
import { ValuesTab } from "./dock/values.js";
import { LogsTab } from "./dock/logs.js";
import { InstrumentsTab } from "./dock/instruments.js";
import { QueueTab, useManagers } from "./dock/queue.js";
import { RunningSummary } from "./progress.js";
import { AlertBell, AlertStore, AlertToasts, useAlertWatch } from "./alerts.js";
import { useConnection } from "./connection.js";
import { useStore } from "./hooks.js";
import {
  FileControl,
  RackControl,
  ShutdownButton,
  useRack,
  useScribe,
} from "./controls.js";
import { useTheme } from "./theme.js";
import { Dock } from "./dock.js";
import { CloseDialog } from "./close-dialog.js";
import { KeyboardIcon, LogoMark, MoonIcon, SunIcon } from "./icons.js";
import { ShortcutHelp, useShortcuts } from "./shortcuts.js";
import { Palette } from "./palette.js";
import { ConfirmDialog } from "./confirm.js";
import { PlotArea } from "./plot/area.js";

const CONNECTION_LABELS = {
  connecting: "Connecting…",
  connected: "Connected",
  disconnected: "Disconnected",
};

// The dock's tabs. A tab that `fill`s its panel scrolls itself, with no
// padding around it.
const dockTabs = ({ store, logs, columns, managers }) => [
  {
    id: "values",
    label: "Values",
    content: html`<${ValuesTab} store=${store} columns=${columns} />`,
  },
  {
    id: "queue",
    label: "Queue",
    content: html`<${QueueTab} managers=${managers} />`,
  },
  {
    id: "instruments",
    label: "Instruments",
    fill: true,
    content: html`<${InstrumentsTab} managers=${managers} />`,
  },
  {
    id: "logs",
    label: "Logs",
    fill: true,
    content: html`<${LogsTab} store=${logs} />`,
  },
];

// A store, kept up to date by a feed for as long as the page is open, whichever
// tab is showing. It is also `window.pyacquisition[name]`, for the browser tests
// and for poking at in the developer tools.
function useFed(name, Store, feed) {
  const [store] = useState(() => new Store());
  useEffect(() => {
    window.pyacquisition = { ...window.pyacquisition, [name]: store };
    return feed(store, {
      onStatus: (status) => {
        store.status = status; // connecting, live or reconnecting
        store.changed();
      },
    });
  }, [store]);
  return store;
}

const useData = () => useFed("store", DataStore, dataFeed);
const useLogs = () => useFed("logs", LogStore, logFeed);

// What the experiment says about each column (its source and unit), fetched
// again each time it connects, as it may have restarted with other columns.
function useColumns(connection) {
  const [columns, setColumns] = useState(null);
  useEffect(() => {
    if (connection !== "connected") return;
    columnInfo().then(setColumns, () => {});
  }, [connection]);
  return columns;
}

// The experiment's name, fetched once it answers.
function useExperimentName(connection) {
  const [name, setName] = useState(null);
  useEffect(() => {
    if (connection !== "connected" || name) return;
    experimentInfo().then((info) => setName(info.name), () => {});
  }, [connection, name]);
  useEffect(() => {
    document.title = name ? `${name} · PyAcquisition` : "PyAcquisition";
  }, [name]);
  return name;
}

function TopBar({ name, connection, theme, onToggleTheme, onHelp, store, managers, rack, alerts }) {
  useStore(store); // for the data file, which the data stream announces
  const file = store.current.file;
  const scribe = useScribe(connection, file);
  const next = theme === "dark" ? "light" : "dark";
  return html`
    <header class="topbar">
      <div class="brand" title="PyAcquisition">
        <${LogoMark} />
        <span class="brand-name">${name ?? "PyAcquisition"}</span>
      </div>
      <div class="topbar-middle">
        <${FileControl} scribe=${scribe} file=${file} />
        <${RackControl} rack=${rack.state} onChanged=${rack.refresh} />
        <${RunningSummary} states=${managers.states} />
      </div>
      <div class="topbar-actions">
        <${AlertBell} alerts=${alerts} />
        <span class="connection" data-state=${connection} role="status">
          <span class="connection-dot"></span>
          ${CONNECTION_LABELS[connection]}
        </span>
        <button
          class="icon-button"
          aria-label="Keyboard shortcuts"
          title="Keyboard shortcuts (?)"
          onClick=${onHelp}
        >
          <${KeyboardIcon} />
        </button>
        <button
          class="icon-button"
          aria-label="Switch to the ${next} theme"
          title="Switch to the ${next} theme"
          onClick=${onToggleTheme}
        >
          ${theme === "dark" ? html`<${SunIcon} />` : html`<${MoonIcon} />`}
        </button>
        <${ShutdownButton} />
      </div>
    </header>
  `;
}

export function App() {
  const connection = useConnection();
  const name = useExperimentName(connection);
  const { theme, toggle } = useTheme();
  const store = useData();
  const logs = useLogs();
  const managers = useManagers(connection);
  const rack = useRack(connection);
  const columns = useColumns(connection);
  const [alerts] = useState(() => new AlertStore());
  useAlertWatch({ alerts, connection, store, logs, managers, rack });
  const [palette, setPalette] = useState(false);
  const [help, setHelp] = useState(false);
  // A question an action asks before it runs (abort, clear the queue): its
  // answer resolves the promise the palette waits on.
  const [asking, setAsking] = useState(null);
  const confirm = (question) => new Promise((resolve) => setAsking({ ...question, resolve }));
  const answer = (yes) => {
    asking.resolve(yes);
    setAsking(null);
  };
  useShortcuts({
    onToggleTheme: toggle,
    onPalette: () => setPalette((open) => !open),
    onHelp: () => setHelp(true),
  });
  return html`
    <div class="app">
      <${TopBar}
        name=${name}
        connection=${connection}
        theme=${theme}
        onToggleTheme=${toggle}
        onHelp=${() => setHelp(true)}
        store=${store}
        managers=${managers}
        rack=${rack}
        alerts=${alerts}
      />
      <${PlotArea} store=${store} columns=${columns} theme=${theme} />
      <${Dock} tabs=${dockTabs({ store, logs, columns, managers })} />
    </div>
    <${AlertToasts} alerts=${alerts} />
    ${palette &&
    html`<${Palette}
      managers=${managers.states}
      onQueued=${managers.refresh}
      onClose=${() => setPalette(false)}
      context=${{
        managers: managers.states,
        refreshManagers: managers.refresh,
        rack: rack.state,
        refreshRack: rack.refresh,
        columns: store.columns,
        theme,
        toggleTheme: toggle,
        logs,
        showHelp: () => setHelp(true),
        confirm,
      }}
    />`}
    ${asking &&
    html`<${ConfirmDialog}
      title=${asking.title}
      confirmLabel=${asking.confirmLabel}
      danger=${asking.danger}
      onCancel=${() => answer(false)}
      onConfirm=${() => answer(true)}
    >
      <p>${asking.message}</p>
    <//>`}
    ${help && html`<${ShortcutHelp} onClose=${() => setHelp(false)} />`}
    <${CloseDialog} />
  `;
}
