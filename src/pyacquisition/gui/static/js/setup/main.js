// The setup page (`pyacquisition new`), served by the setup server (core/setup.py).
import { render } from "preact";
import { html } from "../html.js";
import { App } from "./app.js";

render(html`<${App} />`, document.getElementById("app"));
