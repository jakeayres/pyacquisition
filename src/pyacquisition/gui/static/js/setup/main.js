// SPDX-License-Identifier: MPL-2.0
// Copyright (C) 2023-2026 Jake Ayres
//
// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.

// The setup page (`pyacquisition new`), served by the setup server (core/setup.py).
import { render } from "preact";
import { html } from "../html.js";
import { App } from "./app.js";

render(html`<${App} />`, document.getElementById("app"));
