// SPDX-License-Identifier: MPL-2.0
// Copyright (C) 2023-2026 Jake Ayres
//
// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.

// About PyAcquisition: the version running, its license, the copyright and
// where its source is, from /about (core/about.py). The palette's action and
// the top bar's name open it, with the page event OPEN_ABOUT.
import { useEffect, useLayoutEffect, useRef, useState } from "preact/hooks";
import { html } from "./html.js";
import { get } from "./api.js";
import { openLink } from "./news.js";

// The page event that opens About.
export const OPEN_ABOUT = "pyacquisition:about";

const Link = ({ url, children }) => html`
  <a href=${url} target="_blank" rel="noopener noreferrer" onClick=${openLink}>${children}</a>
`;

// "Preact (MIT), uPlot (MIT) and htm (Apache-2.0)".
function listed(libraries) {
  const names = libraries.map((library) => `${library.name} (${library.license})`);
  return names.length > 1 ? `${names.slice(0, -1).join(", ")} and ${names.at(-1)}` : names.join("");
}

function AboutDialog({ about, onClose }) {
  const close = useRef(null);
  useLayoutEffect(() => {
    close.current?.focus();
    const onKey = (event) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
  return html`
    <div class="overlay" onPointerDown=${(e) => e.target === e.currentTarget && onClose()}>
      <div class="dialog about-dialog" role="dialog" aria-modal="true" aria-labelledby="about-title">
        <h2 id="about-title">About PyAcquisition</h2>
        ${about.error
          ? html`<p>The experiment didn't answer, so the version isn't known: ${about.error}</p>`
          : html`
              <p class="about-version">${about.version ? `Version ${about.version}` : "Version unknown"}</p>
              <p>Free software under the <${Link} url=${about.license_url}>${about.license_name}</${Link}>.</p>
              <p>${about.copyright}</p>
              <p>Source code: <${Link} url=${about.source_url}>${about.source_url.replace(/^https:\/\//, "")}</${Link}></p>
              <p>Its interface uses ${listed(about.libraries)}.</p>
            `}
        <div class="dialog-buttons">
          <button class="button" ref=${close} onClick=${onClose}>Close</button>
        </div>
      </div>
    </div>
  `;
}

// The dialog, shown when OPEN_ABOUT is sent, with what /about says then.
export function About() {
  const [about, setAbout] = useState(null);
  useEffect(() => {
    const onOpen = async () => {
      try {
        setAbout((await get("/about")).data);
      } catch (error) {
        setAbout({ error: error.message });
      }
    };
    window.addEventListener(OPEN_ABOUT, onOpen);
    return () => window.removeEventListener(OPEN_ABOUT, onOpen);
  }, []);
  return about && html`<${AboutDialog} about=${about} onClose=${() => setAbout(null)} />`;
}
