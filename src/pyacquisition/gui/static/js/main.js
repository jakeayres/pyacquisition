// SPDX-License-Identifier: MPL-2.0
// Copyright (C) 2023-2026 Jake Ayres
//
// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.

import { render } from "preact";
import { html } from "./html.js";
import { App } from "./shell.js";
import { keepLayout, restoreLayout } from "./layout.js";

// The layout from the last run first (layout.js), so the page draws as it was.
await restoreLayout();
keepLayout();
render(html`<${App} />`, document.getElementById("app"));
