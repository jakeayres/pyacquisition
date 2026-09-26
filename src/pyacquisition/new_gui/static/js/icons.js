// Icons, drawn in `currentColor` so they take the colour of their text.
import { html } from "./html.js";

const stroke = (paths, { width = 2 } = {}) => html`
  <svg
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width=${width}
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
  >
    ${paths}
  </svg>
`;

export const LogoMark = () => html`
  <svg class="brand-mark" viewBox="0 0 20 20" aria-hidden="true">
    <rect width="20" height="20" rx="5" fill="currentColor" />
    <path
      d="M4 11h2.5l2-5 3 9 2-5.5H16"
      fill="none"
      stroke="var(--on-accent)"
      stroke-width="1.8"
      stroke-linecap="round"
      stroke-linejoin="round"
    />
  </svg>
`;

export const SunIcon = () =>
  stroke(html`
    <circle cx="12" cy="12" r="4" />
    <path
      d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"
    />
  `);

export const MoonIcon = () =>
  stroke(html`<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />`);

export const ChevronDownIcon = () => stroke(html`<path d="M6 9l6 6 6-6" />`);

export const ChevronUpIcon = () => stroke(html`<path d="M18 15l-6-6-6 6" />`);

export const EyeIcon = () =>
  stroke(html`
    <path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7S1 12 1 12z" />
    <circle cx="12" cy="12" r="3" />
  `);

export const EyeOffIcon = () =>
  stroke(html`
    <path
      d="M9.9 4.24A10.4 10.4 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19M6.61 6.61A18.4 18.4 0 0 0 1 12s4 8 11 8a10.4 10.4 0 0 0 5.39-1.61"
    />
    <path d="M1 1l22 22" />
  `);

// Two axes with their ticks: the axis settings (limits, log scales). Drawn a
// little finer than the other icons, so the ticks stay apart at 16 px.
export const AxesIcon = () =>
  stroke(
    html`
      <path d="M4 3v17h17" />
      <path d="M4 8.5h3.5M4 14h3.5" />
      <path d="M10 20v-3.5M15.5 20v-3.5" />
    `,
    { width: 1.75 },
  );

export const CopyIcon = () =>
  stroke(html`
    <rect x="9" y="9" width="12" height="12" rx="2" />
    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
  `);

export const CloseIcon = () => stroke(html`<path d="M18 6L6 18M6 6l12 12" />`);

export const SearchIcon = () =>
  stroke(html`
    <circle cx="11" cy="11" r="7" />
    <path d="M20 20l-3.5-3.5" />
  `);

export const ArrowDownIcon = () => stroke(html`<path d="M12 5v14M6 13l6 6 6-6" />`);

export const ChartIcon = () =>
  stroke(html`
    <path d="M3 3v18h18" />
    <path d="M7 15l4-4 3 3 5-6" />
  `);
