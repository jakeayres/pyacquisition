// `html` writes Preact elements as tagged templates, which need no build step:
//     html`<p class="note">${text}</p>`
import { h } from "preact";
import htm from "htm";

export const html = htm.bind(h);
