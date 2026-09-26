// The app shell: a slim top bar, the plot area filling the window, and the dock.
import { useEffect, useState } from "preact/hooks";
import { html } from "./html.js";
import { columnInfo, experimentInfo } from "./api.js";
import { DataStore } from "./store.js";
import { startFeed } from "./feed.js";
import { ValuesTab } from "./dock/values.js";
import { useConnection } from "./connection.js";
import { useTheme } from "./theme.js";
import { Dock } from "./dock.js";
import { CloseDialog } from "./close-dialog.js";
import { LogoMark, MoonIcon, SunIcon } from "./icons.js";
import { PlotArea } from "./plot/area.js";

const CONNECTION_LABELS = {
  connecting: "Connecting…",
  connected: "Connected",
  disconnected: "Disconnected",
};

// The dock's tabs. Each milestone replaces one placeholder with the real thing.
const placeholder = (text) => html`<p class="placeholder">${text}</p>`;
const dockTabs = ({ store, columns }) => [
  {
    id: "values",
    label: "Values",
    content: html`<${ValuesTab} store=${store} columns=${columns} />`,
  },
  {
    id: "queue",
    label: "Queue",
    content: placeholder("The task queue arrives in milestone 9."),
  },
  {
    id: "instruments",
    label: "Instruments",
    content: placeholder("Instrument queries and commands arrive in milestone 14."),
  },
  {
    id: "logs",
    label: "Logs",
    content: placeholder("The live log arrives in milestone 7."),
  },
];

// The data, kept up to date for as long as the page is open. The store is also
// `window.pyacquisition.store`, for the browser tests and for poking at in the
// developer tools.
function useData() {
  const [store] = useState(() => new DataStore());
  useEffect(() => {
    window.pyacquisition = { ...window.pyacquisition, store };
    return startFeed(store, {
      onStatus: (status) => {
        store.status = status; // connecting, live or reconnecting
        store.changed();
      },
    });
  }, [store]);
  return store;
}

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

function TopBar({ name, connection, theme, onToggleTheme }) {
  const next = theme === "dark" ? "light" : "dark";
  return html`
    <header class="topbar">
      <div class="brand" title="PyAcquisition">
        <${LogoMark} />
        <span class="brand-name">${name ?? "PyAcquisition"}</span>
      </div>
      <div class="topbar-middle"></div>
      <div class="topbar-actions">
        <span class="connection" data-state=${connection} role="status">
          <span class="connection-dot"></span>
          ${CONNECTION_LABELS[connection]}
        </span>
        <button
          class="icon-button"
          aria-label="Switch to the ${next} theme"
          title="Switch to the ${next} theme"
          onClick=${onToggleTheme}
        >
          ${theme === "dark" ? html`<${SunIcon} />` : html`<${MoonIcon} />`}
        </button>
      </div>
    </header>
  `;
}

export function App() {
  const connection = useConnection();
  const name = useExperimentName(connection);
  const { theme, toggle } = useTheme();
  const store = useData();
  const columns = useColumns(connection);
  return html`
    <div class="app">
      <${TopBar}
        name=${name}
        connection=${connection}
        theme=${theme}
        onToggleTheme=${toggle}
      />
      <${PlotArea} store=${store} columns=${columns} theme=${theme} />
      <${Dock} tabs=${dockTabs({ store, columns })} />
    </div>
    <${CloseDialog} />
  `;
}
