// SPDX-License-Identifier: MPL-2.0
// Copyright (C) 2023-2026 Jake Ayres
//
// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.

// `html` writes Preact elements as tagged templates, which need no build step:
//     html`<p class="note">${text}</p>`
import { h } from "preact";
import htm from "htm";

export const html = htm.bind(h);
