// Keeps a store up to date with the experiment: connects to a stream, loads a
// snapshot, and applies the stream's events after it (the protocol in
// core/history.py, which core/log_history.py shares). It reconnects by itself,
// waiting longer after each failure, and loads a fresh snapshot every time, so a
// restarted experiment or a missed event is caught up with.
//
// The store has `load(snapshot)`, and `apply(event)`, which returns false if an
// event was missed.
import { get, getBinary, websocketUrl } from "./api.js";
import { parseSnapshot } from "./store.js";

const FIRST_RETRY = 500; // milliseconds
const LAST_RETRY = 5000;

export function startFeed(store, { stream, snapshot, onStatus = () => {} }) {
  let socket = null;
  let retry = FIRST_RETRY;
  let stopped = false;
  let timer = null;

  const connect = () => {
    let held = []; // events that arrive before the snapshot, applied after it
    onStatus("connecting");
    socket = new WebSocket(websocketUrl(stream));

    socket.onopen = async () => {
      try {
        store.load(await snapshot());
        for (const event of held) {
          if (!store.apply(event)) throw new Error("an event was missed");
        }
        held = null;
        retry = FIRST_RETRY;
        onStatus("live");
      } catch {
        socket.close(); // try again from the start
      }
    };

    socket.onmessage = (message) => {
      const event = JSON.parse(message.data);
      if (held) held.push(event);
      else if (!store.apply(event)) socket.close(); // missed one: start again
    };

    socket.onclose = () => {
      if (stopped) return;
      onStatus("reconnecting");
      timer = setTimeout(connect, retry);
      retry = Math.min(retry * 2, LAST_RETRY);
    };
  };

  connect();
  return () => {
    stopped = true;
    clearTimeout(timer);
    socket?.close();
  };
}

// The rows: /stream/data after a binary /history snapshot.
export const dataFeed = (store, options) =>
  startFeed(store, {
    ...options,
    stream: "/stream/data",
    snapshot: async () =>
      parseSnapshot(
        await getBinary("/history", { params: { format: "binary" }, timeout: 60000 }),
      ),
  });

// The log: /stream/logs after a /logs/history snapshot.
export const logFeed = (store, options) =>
  startFeed(store, {
    ...options,
    stream: "/stream/logs",
    snapshot: async () => (await get("/logs/history", { timeout: 10000 })).data,
  });
