import { render } from "preact";
import { html } from "./html.js";
import { App } from "./shell.js";
import { keepLayout, restoreLayout } from "./layout.js";

// The layout from the last run first (layout.js), so the page draws as it was.
await restoreLayout();
keepLayout();
render(html`<${App} />`, document.getElementById("app"));
