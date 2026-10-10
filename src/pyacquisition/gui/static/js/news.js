// News on startup (core/news.py): a card in a corner when the page opens, with
// what's new since the last version seen on this PC, a newer version, a fix the
// running version needs, or news from the maker; and What's new, which lists
// them all. The server decides what to show and remembers what has been seen.
// A message is data, drawn here: its text is plain, with Markdown links and
// `code` its only markup, so a feed can never put HTML in the page.
import { useEffect, useLayoutEffect, useRef, useState } from "preact/hooks";
import { html } from "./html.js";
import { get, post } from "./api.js";
import {
  ArrowUpCircleIcon,
  CloseIcon,
  CopyIcon,
  MegaphoneIcon,
  SparkleIcon,
  WarningIcon,
} from "./icons.js";

// The browser tests shorten the waits below, with a scale set before the page
// loads. It is 1 otherwise.
const SCALE = globalThis.pyacquisitionNewsTimeScale ?? 1;
const PENDING_AGAIN = 3000 * SCALE; // ms between asks while a fetch is going
const PENDING_TRIES = 20; // asks while it is, at most
const WAITING_AGAIN = 15000 * SCALE; // ms between asks while the maker's news waits for a task

// The page event that opens What's new (the palette's action sends it).
export const OPEN_WHATS_NEW = "pyacquisition:whats-new";

// A Markdown link to an https address, or `code`.
const MARKUP = /\[([^\]\n]+)\]\((https:\/\/[^\s)]+)\)|`([^`\n]+)`/g;

// Opens a link in the system's browser from the window, which would otherwise
// follow it and leave the experiment. From a browser, it opens a new tab.
export function openLink(event) {
  const api = window.pywebview?.api;
  if (api?.open_link) {
    event.preventDefault();
    api.open_link(event.currentTarget.href);
  }
}

const Link = ({ url, children }) => html`
  <a href=${url} target="_blank" rel="noopener noreferrer" onClick=${openLink}>${children}</a>
`;

// A line of text, with its links and code drawn, and everything else as text.
function Inline({ text }) {
  const parts = [];
  let at = 0;
  for (const match of text.matchAll(MARKUP)) {
    if (match.index > at) parts.push(text.slice(at, match.index));
    parts.push(
      match[3] !== undefined
        ? html`<code>${match[3]}</code>`
        : html`<${Link} url=${match[2]}>${match[1]}<//>`,
    );
    at = match.index + match[0].length;
  }
  if (at < text.length) parts.push(text.slice(at));
  return parts;
}

const Points = ({ points }) => html`
  <ul class="news-points">
    ${points.map((point) => html`<li><${Inline} text=${point} /></li>`)}
  </ul>
`;

// Paragraphs, between blank lines. A paragraph whose lines all start "- " is a list.
function Text({ text }) {
  if (!text) return null;
  return text.split(/\n\s*\n/).map((block) => {
    const lines = block
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean);
    if (lines.length && lines.every((line) => line.startsWith("- "))) {
      return html`<${Points} points=${lines.map((line) => line.slice(2))} />`;
    }
    return html`<p class="news-text"><${Inline} text=${lines.join(" ")} /></p>`;
  });
}

// A command to run, such as an update's, with a button to copy it. The
// recommended one (uv's, as the docs install with) stands out.
function Command({ label, command, recommended }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(command);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // It can still be selected and copied by hand.
    }
  };
  return html`
    <div class="news-command" data-recommended=${recommended ? "true" : "false"}>
      <div class="news-command-head">
        <span class="news-command-label">${label}</span>
        ${recommended && html`<span class="news-badge">Recommended</span>`}
        <span class="news-copied" role="status">${copied ? "Copied" : ""}</span>
      </div>
      <div class="news-command-line">
        <code>${command}</code>
        <button
          class="icon-button"
          aria-label="Copy the ${label} command"
          title="Copy"
          onClick=${copy}
        >
          <${CopyIcon} />
        </button>
      </div>
    </div>
  `;
}

const ICONS = {
  whats_new: SparkleIcon,
  update: ArrowUpCircleIcon,
  fix: WarningIcon,
  news: MegaphoneIcon,
};

// What kind of news it is: its icon and its label. Its colour, the kind's, is
// the card's header band (app.css).
function Kind({ message }) {
  const Icon = ICONS[message.kind];
  return html`
    <span class="news-kind" data-kind=${message.kind}>
      ${Icon && html`<${Icon} />`}
      ${message.label}${message.important ? " · Important" : ""}
    </span>
  `;
}

function Message({ message }) {
  const several = message.sections.length > 1;
  return html`
    <h3 class="news-title">${message.title}</h3>
    ${message.image &&
    html`<img class="news-image" src=${message.image.src} alt=${message.image.alt} />`}
    <${Text} text=${message.text} />
    ${message.sections.map(
      (section) => html`
        ${several && html`<h4 class="news-version">${section.version}</h4>`}
        <${Points} points=${section.points} />
      `,
    )}
    ${message.commands.length > 0 &&
    html`<div class="news-commands">
      ${message.commands.map((c) => html`<${Command} key=${c.label} ...${c} />`)}
    </div>`}
    ${message.link &&
    html`<p class="news-link"><${Link} url=${message.link.url}>${message.link.label}<//></p>`}
  `;
}

// A fix or an update comes back each run until "Don't show again"; closing
// anything else is for good (the server decides, at /news/close).
function Card({ message, more, onClose, onNever, onMore, onNoMaker }) {
  return html`
    <section class="news-card" data-kind=${message.kind} aria-label="News">
      <div class="news-card-head">
        <${Kind} message=${message} />
        <button class="icon-button" aria-label="Close" title="Close" onClick=${onClose}>
          <${CloseIcon} />
        </button>
      </div>
      <div class="news-card-body"><${Message} message=${message} /></div>
      ${(more > 0 || message.kind === "news" || message.comes_back) &&
      html`
        <div class="news-card-foot">
          ${message.comes_back &&
          html`<button class="link-button" onClick=${onNever}>Don't show again</button>`}
          ${message.kind === "news" &&
          html`<button class="link-button" onClick=${onNoMaker}>
            Don't show news from the maker
          </button>`}
          ${more > 0 &&
          html`<button class="link-button news-more" onClick=${onMore}>${more} more</button>`}
        </div>
      `}
    </section>
  `;
}

const OFF_NOTES = {
  off: "News is turned off on this PC (PYACQUISITION_NEWS is off), so nothing is fetched.",
  updates: "News from the maker is turned off on this PC (PYACQUISITION_NEWS is updates).",
};

function WhatsNew({ news, onClose, onChoose }) {
  const close = useRef(null);
  // A layout effect, so an Escape pressed as soon as it opens is heard.
  useLayoutEffect(() => {
    close.current?.focus();
    const onKey = (event) => event.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
  const all = news?.all ?? [];
  return html`
    <div class="overlay" onPointerDown=${(e) => e.target === e.currentTarget && onClose()}>
      <div class="dialog news-dialog" role="dialog" aria-modal="true" aria-labelledby="whats-new-title">
        <h2 id="whats-new-title">What's new</h2>
        <div class="news-list">
          ${all.length
            ? all.map(
                (message) => html`
                  <article class="news-item" key=${message.id} data-kind=${message.kind}>
                    <${Kind} message=${message} />
                    <${Message} message=${message} />
                  </article>
                `,
              )
            : html`<p>${news ? "Nothing new." : "Loading…"}</p>`}
        </div>
        ${news?.mode === "all"
          ? html`<label class="news-choice">
              <input
                type="checkbox"
                checked=${news.maker_news}
                onChange=${(e) => onChoose(e.currentTarget.checked)}
              />
              Show news from the maker
            </label>`
          : news && html`<p class="form-help">${OFF_NOTES[news.mode]}</p>`}
        <div class="dialog-buttons">
          <button class="button" ref=${close} onClick=${onClose}>Close</button>
        </div>
      </div>
    </div>
  `;
}

// The card, and What's new when it is asked for. `fixed` puts the card in the
// window's corner (the setup page), rather than in the plot area's.
export function News({ fixed = false }) {
  const [news, setNews] = useState(null);
  const [open, setOpen] = useState(false);
  const [closed, setClosed] = useState(() => new Set()); // closed, and not asked again since
  const [showing, setShowing] = useState(null); // the id of the message on the card

  // Asks once, then again while a fetch is still going, or while the maker's
  // news waits for a running task to end.
  useEffect(() => {
    let stopped = false;
    let timer = null;
    let tries = 0;
    const load = async () => {
      try {
        const { data } = await get("/news");
        if (stopped) return;
        setNews(data);
        if (data.pending && tries < PENDING_TRIES) {
          tries += 1;
          timer = setTimeout(load, PENDING_AGAIN);
        } else if (data.waiting) {
          timer = setTimeout(load, WAITING_AGAIN);
        }
      } catch {
        // No news is fine: the page works without it.
      }
    };
    load();
    return () => {
      stopped = true;
      clearTimeout(timer);
    };
  }, []);

  useEffect(() => {
    const onOpen = () => setOpen(true);
    window.addEventListener(OPEN_WHATS_NEW, onOpen);
    return () => window.removeEventListener(OPEN_WHATS_NEW, onOpen);
  }, []);

  const reload = () =>
    get("/news")
      .then(({ data }) => setNews(data))
      .catch(() => {});
  const hide = (id, path) => {
    setClosed((before) => new Set(before).add(id));
    post(path, { id }).catch(() => {});
  };
  const dismiss = (id) => hide(id, "/news/close");
  const never = (id) => hide(id, "/news/seen");
  const choose = (makerNews) =>
    post("/news/choices", { maker_news: makerNews })
      .then(reload)
      .catch(() => {});

  // The card keeps its message until it is closed, even if something more
  // important arrives (a fetch that ends while it is being read), and then
  // shows the most important of the rest.
  const shown = (news?.show ?? []).filter((message) => !closed.has(message.id));
  const first = shown.find((message) => message.id === showing) ?? shown[0];
  useEffect(() => {
    if (first && first.id !== showing) setShowing(first.id);
  }, [first?.id]);
  return html`
    <div class="news-anchor ${fixed ? "news-anchor-fixed" : ""}">
      ${first &&
      html`<${Card}
        key=${first.id}
        message=${first}
        more=${shown.length - 1}
        onClose=${() => dismiss(first.id)}
        onNever=${() => never(first.id)}
        onMore=${() => setOpen(true)}
        onNoMaker=${() => {
          dismiss(first.id);
          choose(false);
        }}
      />`}
    </div>
    ${open && html`<${WhatsNew} news=${news} onClose=${() => setOpen(false)} onChoose=${choose} />`}
  `;
}
