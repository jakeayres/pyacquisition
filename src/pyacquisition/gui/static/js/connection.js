import { useEffect, useState } from "preact/hooks";
import { ping } from "./api.js";

const PERIOD = 1000; // milliseconds between checks

// "connecting" until the experiment first answers, then "connected" or
// "disconnected".
export function useConnection() {
  const [state, setState] = useState("connecting");

  useEffect(() => {
    let stopped = false;
    let timer;
    const check = async () => {
      const answered = await ping();
      if (stopped) return;
      setState((previous) =>
        answered
          ? "connected"
          : previous === "connecting"
            ? "connecting"
            : "disconnected",
      );
      timer = setTimeout(check, PERIOD);
    };
    check();
    return () => {
      stopped = true;
      clearTimeout(timer);
    };
  }, []);

  return state;
}
