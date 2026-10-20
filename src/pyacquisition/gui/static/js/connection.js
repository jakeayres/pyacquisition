// SPDX-License-Identifier: MPL-2.0
// Copyright (C) 2023-2026 Jake Ayres
//
// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.

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
