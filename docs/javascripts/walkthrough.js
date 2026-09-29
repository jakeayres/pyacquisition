/* A walkthrough: files built up a few lines at a time as the page scrolls, beside a
   terminal, with each step's note placed against the lines it changes. Getting Started's
   pages are walkthroughs, and so is each Usage tutorial.

   A walkthrough is a .gs element holding a .gs-stage, which holds .gs-notes, which holds
   a <section class="gs-step"> for each step: its heading, its note and its code. The
   steps' own code blocks are the source. A block inside an aside (an admonition or a
   <details>) isn't: it stays where it is, as it would in any page.

   - A shell block's commands go into the terminal, and a text block is output there, a
     line for each line. A step's data-result adds one more line of output.
   - Any other block belongs to the file its title names (```python title="lab.py"),
     or, with no title, to the walkthrough's first file. A file is built in one of two
     modes:
     - merge: each block is a TOML snippet, merged into the file under its tables, as
       you would edit the real file. A line under a table that is already there goes at
       the end of it, and a new table goes after its family ([instruments.lockin] after
       [instruments]), or at the end. (1. The Config File)
     - versions: each block is the whole file as it is after the step, and the
       differences from the version before are shown: lines added, and lines removed.
       (0. Installation, and 2. The Python API)

   On the .gs element:

   - data-files="disk_space.py:versions lab.py:versions" lists the files, in order,
     each with its mode (versions if it has none). The file panel shows the file of the
     step in view, with a tab for each. data-files="" is a walkthrough in the terminal
     alone.
   - Or, for one file, data-file names it ("rig.toml" if it is left out), and
     data-mode="versions" sets its mode (merge if it is left out).
   - data-lines and data-term-lines are how many lines of the file and of the terminal
     are in view.

   A step with data-new-file makes a file that starts empty: the one it names, or the
   first. Otherwise a file is made by the first step that writes it. A step with no code
   of a file's shows the file of the step before it. A step with data-given shows its
   files as the reader already has them, the tutorial's starting point: none of their
   lines is new, and its note sits at the top.

   On a wide screen the panels are pinned while the page scrolls past the steps, and the
   note of the step in view is placed against the lines it adds, or at the top when it
   adds none. Otherwise, or without this script, the steps are an ordinary lesson, each
   with its code in place. docs/stylesheets/walkthrough.css has the styles. */
(() => {
  "use strict";

  const WIDE = "(min-width: 60em)";
  const reduced = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
  const esc = (s) => s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
  const make = (tag, cls, html) => {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (html !== undefined) e.innerHTML = html;
    return e;
  };

  // TOML, in the front page's code colours
  function colour(line) {
    if (/^\[[^\]]+\]$/.test(line.trim())) return `<span class="t-h">${esc(line)}</span>`;
    const re = /("[^"]*")|(#.*)|(-?\b\d+(?:\.\d+)?\b)|([{}[\],=])/g;
    let out = "", last = 0, m;
    while ((m = re.exec(line))) {
      out += esc(line.slice(last, m.index));
      const cls = m[1] ? "t-s" : m[2] ? "t-c" : m[3] ? "t-n" : "t-p";
      out += `<span class="${cls}">${esc(m[0])}</span>`;
      last = re.lastIndex;
    }
    return out + esc(line.slice(last));
  }

  // A rendered code block's lines, as text and as the highlighter coloured them. A line
  // the block highlights (hl_lines, for readers without the pinned file) is unwrapped.
  function linesOf(code) {
    const spans = [...code.children].filter((s) => s.id && s.id.startsWith("__span"));
    if (!spans.length) return code.textContent.replace(/\n$/, "").split("\n").map((text) => ({ text, html: esc(text) }));
    return spans.map((s) => {
      const copy = s.cloneNode(true);
      copy.querySelectorAll(".hll").forEach((h) => h.replaceWith(...h.childNodes));
      return { text: copy.textContent.replace(/\n$/, ""), html: copy.innerHTML.replace(/\n$/, "") };
    });
  }

  // A TOML file, merged from the steps' snippets. A row is shown from step `from`.
  function tables(rows) {
    const found = [];
    rows.forEach((row, i) => {
      const h = row.text.match(/^\[([^\]]+)\]$/);
      if (h) found.push({ name: h[1], end: i + 1 });
      else if (row.text && found.length) found[found.length - 1].end = i + 1;
    });
    return found;
  }
  function merge(rows, snippet, step) {
    const blocks = [];
    for (const raw of snippet.split("\n")) {
      const line = raw.replace(/\s+$/, "");
      const h = line.match(/^\[([^\]]+)\]$/);
      if (h) blocks.push({ name: h[1], header: line, lines: [] });
      else if (line && blocks.length) blocks[blocks.length - 1].lines.push(line);
    }
    const row = (text) => ({ text, html: colour(text), from: step, to: Infinity });
    for (const b of blocks) {
      const known = tables(rows);
      const same = known.find((t) => t.name === b.name);
      if (same) {
        rows.splice(same.end, 0, ...b.lines.map(row));
        continue;
      }
      const family = known.filter((t) => t.name.split(".")[0] === b.name.split(".")[0]).pop();
      const added = [b.header, ...b.lines].map(row);
      if (rows.length) added.unshift(row(""));
      rows.splice(family ? family.end : rows.length, 0, ...added);
    }
  }

  // A file from its versions: each line's rows are shown from the step that adds them
  // until the step that removes them. Deletions come before insertions, so an edited line
  // goes, and its new form appears where it was.
  function diff(a, b) {
    const n = a.length, m = b.length;
    const lcs = Array.from({ length: n + 1 }, () => new Array(m + 1).fill(0));
    for (let i = n - 1; i >= 0; i--) {
      for (let j = m - 1; j >= 0; j--) {
        lcs[i][j] = a[i] === b[j] ? lcs[i + 1][j + 1] + 1 : Math.max(lcs[i + 1][j], lcs[i][j + 1]);
      }
    }
    const ops = [];
    let i = 0, j = 0;
    while (i < n && j < m) {
      if (a[i] === b[j]) ops.push({ op: "keep", i: i++, j: j++ });
      else if (lcs[i + 1][j] >= lcs[i][j + 1]) ops.push({ op: "del", i: i++ });
      else ops.push({ op: "ins", j: j++ });
    }
    while (i < n) ops.push({ op: "del", i: i++ });
    while (j < m) ops.push({ op: "ins", j: j++ });
    return compact(ops, n, b);
  }
  // A run of new lines can often be placed more than one way: of two blank lines, either
  // can be the new one. Each run moves up as far as the file allows, joining any run it
  // meets, so that what a step adds is one block, highlighted together.
  function compact(ops, n, b) {
    const m = b.length;
    const added = new Array(m).fill(false);
    const kept = []; // the old lines kept, in order: moving a run keeps their order
    for (const op of ops) {
      if (op.op === "ins") added[op.j] = true;
      else if (op.op === "keep") kept.push(op.i);
    }
    for (let j = 0; j < m; ) {
      if (!added[j]) { j++; continue; }
      let s = j, e = j;
      while (e < m && added[e]) e++;
      while (s > 0 && !added[s - 1] && b[s - 1] === b[e - 1]) {
        added[--s] = true;
        added[--e] = false;
        while (s > 0 && added[s - 1]) s--;
      }
      j = e;
    }
    // The operations again, deletions first where lines change, as before
    const out = [];
    let i = 0, k = 0;
    const gone = (upto) => { while (i < upto) out.push({ op: "del", i: i++ }); };
    gone(kept.length ? kept[0] : n);
    for (let j = 0; j < m; j++) {
      if (added[j]) { out.push({ op: "ins", j }); continue; }
      const at = kept[k++];
      out.push({ op: "keep", i: at, j });
      i = at + 1;
      gone(k < kept.length ? kept[k] : n);
    }
    return out;
  }
  function versions(rows, blocks) {
    let alive = [];
    for (const { step, code } of blocks) {
      const next = linesOf(code);
      const now = [];
      let after = null;
      for (const op of diff(alive.map((r) => r.text), next.map((l) => l.text))) {
        if (op.op === "keep") {
          after = alive[op.i];
          now.push(after);
        } else if (op.op === "del") {
          after = alive[op.i];
          after.to = step;
        } else {
          const row = { ...next[op.j], from: step, to: Infinity };
          rows.splice(after ? rows.indexOf(after) + 1 : 0, 0, row);
          now.push(row);
          after = row;
        }
      }
      alive = now;
    }
  }

  // The files a walkthrough declares (see the top of this file)
  function declared(root) {
    if (root.hasAttribute("data-files")) {
      return root.dataset.files.split(/\s+/).filter(Boolean).map((entry) => {
        const [name, mode] = entry.split(":");
        return { name, mode: mode === "merge" ? "merge" : "versions" };
      });
    }
    return [{ name: root.dataset.file || "rig.toml", mode: root.dataset.mode === "versions" ? "versions" : "merge" }];
  }
  // A step's own code blocks that match: not those in an aside, which stay where they are
  const own = (step, selector) => [...step.querySelectorAll(selector)].filter((b) => !b.closest(".admonition, details"));
  const titleOf = (block) => block.querySelector(".filename")?.textContent.trim() || "";

  function mount(root) {
    if (root.dataset.ready) return;
    root.dataset.ready = "1";
    const stage = root.querySelector(".gs-stage");
    const steps = [...root.querySelectorAll(".gs-notes > .gs-step")];
    if (!stage || !steps.length) return;
    const fileLines = +(root.dataset.lines || 15), termLines = +(root.dataset.termLines || 7);
    root.style.setProperty("--steps", steps.length);
    root.style.setProperty("--file-lines", fileLines);

    // The files: each step's blocks sorted into them, and each built in its mode
    const files = declared(root).map((f) => ({ ...f, rows: [], blocks: [], madeAt: -1, made: false }));
    const writes = new Array(steps.length).fill(-1); // the file each step writes, if any
    steps.forEach((el, i) => {
      for (const block of own(el, "div.highlight:not(.language-bash):not(.language-text)")) {
        const title = titleOf(block);
        const k = title ? files.findIndex((f) => f.name === title) : files.length ? 0 : -1;
        if (k < 0) {
          console.warn(`walkthrough: a block for ${title || "a file"}, which the walkthrough doesn't list`);
          continue;
        }
        files[k].blocks.push({ step: i, code: block.querySelector("code") });
        writes[i] = k;
      }
      if (el.hasAttribute("data-new-file") && files.length) {
        const k = Math.max(0, files.findIndex((f) => f.name === el.getAttribute("data-new-file")));
        if (files[k].madeAt < 0) files[k].madeAt = i;
      }
    });
    for (const f of files) {
      const first = f.blocks.length ? f.blocks[0].step : -1;
      if (f.madeAt < 0 || (first >= 0 && first < f.madeAt)) f.madeAt = first;
      if (f.mode === "versions") versions(f.rows, f.blocks);
      else f.blocks.forEach(({ step, code }) => merge(f.rows, code.textContent, step));
    }
    // The file each step shows: the one it writes, or the one before
    const shows = [];
    steps.forEach((_, i) => { shows[i] = writes[i] >= 0 ? writes[i] : i > 0 ? shows[i - 1] : 0; });

    // The terminal: each step's commands and output, in the order they are on the page
    const term = [];
    steps.forEach((el, i) => {
      for (const block of own(el, "div.language-bash, div.language-text")) {
        const text = block.querySelector("code").textContent.replace(/\n$/, "");
        if (block.classList.contains("language-text")) {
          for (const out of text.split("\n")) term.push({ html: `<span class="t-out">${esc(out)}</span>`, from: i, to: Infinity });
          continue;
        }
        for (const cmd of text.trim().split("\n")) {
          const html = cmd.startsWith("#") ? `<span class="t-c">${esc(cmd)}</span>` : `<span class="t-prompt">$</span> ${esc(cmd)}`;
          term.push({ html, from: i, to: Infinity });
        }
      }
      if (el.dataset.result) term.push({ html: `<span class="t-out">${esc(el.dataset.result)}</span>`, from: i, to: Infinity });
    });

    // The panels: the file, with a tab for each when there are several, and the terminal
    const panel = (kind, nameHtml) => {
      const p = make("div", `gs-panel gs-panel--${kind}`, `<div class="gs-panel__name">${nameHtml}</div>`);
      const body = make("div", "gs-panel__body highlight");
      p.append(body);
      return [p, body];
    };
    const line = (html, from, to) => {
      const r = make("div", "gs-line is-hidden", `<span>${html || " "}</span>`);
      r.dataset.from = from;
      r.dataset.to = to;
      return r;
    };
    const panels = make("div", "gs-panels");
    panels.setAttribute("aria-hidden", "true");
    let fileBody = null, empty = null, tabs = [];
    if (files.length) {
      const names = files.length > 1
        ? files.map((f) => `<span class="gs-tab">${esc(f.name)}</span>`).join("")
        : esc(files[0].name);
      const [filePanel, body] = panel("file", names);
      fileBody = body;
      if (files.length > 1) filePanel.firstChild.classList.add("gs-tabs");
      tabs = [...filePanel.querySelectorAll(".gs-tab")];
      for (const f of files) {
        f.scroller = make("div", "gs-scroll is-away");
        f.blank = line("", -1, Infinity); // an empty file's one line
        f.rowEls = f.rows.map((r) => line(r.html, r.from, r.to));
        f.scroller.append(f.blank, ...f.rowEls);
        fileBody.append(f.scroller);
      }
      empty = make("div", "gs-empty", "Not made yet");
      fileBody.append(empty);
      panels.append(filePanel);
      root.style.setProperty("--term-lines", termLines);
    } else {
      // The terminal alone, as tall as the file and the terminal would be together
      root.style.setProperty("--term-lines", fileLines + termLines + 3);
      root.classList.add("gs--terminal");
    }
    const [termPanel, termBody] = panel("term", "Terminal");
    const termRows = term.map((t) => line(t.html, t.from, t.to));
    termBody.append(...termRows);
    panels.append(termPanel);
    stage.prepend(panels);

    // Showing a step
    const given = steps.map((s) => s.hasAttribute("data-given"));
    let active = -1, current = -1; // the step in view, and the file shown
    let target = [], up = false;
    const shownAt = (r, i) => +r.dataset.from <= i && i < +r.dataset.to;
    function reveal(rows, i, animate) {
      let order = 0;
      for (const r of rows) {
        const was = r.classList.contains("is-hidden");
        const shown = shownAt(r, i), added = +r.dataset.from === i && !given[i];
        r.classList.toggle("is-hidden", !shown);
        r.classList.toggle("is-new", added && shown);
        r.classList.remove("is-typing");
        if (added && shown && was && animate && !reduced()) {
          r.style.setProperty("--delay", `${0.1 + order++ * 0.05}s`);
          void r.offsetWidth;
          r.classList.add("is-typing");
        }
      }
      return given[i] ? [] : rows.filter((r) => +r.dataset.from === i && shownAt(r, i) && r.textContent.trim());
    }
    function show(i) {
      const forward = i > active;
      active = i;
      steps.forEach((s, j) => s.classList.toggle("is-active", j === i));

      let newInFile = [];
      if (files.length) {
        const k = shows[i];
        files.forEach((f, j) => {
          f.made = f.madeAt >= 0 && i >= f.madeAt;
          const added = reveal(f.rowEls, i, forward && j === k);
          const written = f.rowEls.some((r) => shownAt(r, i));
          f.blank.classList.toggle("is-hidden", !f.made || written);
          if (j === k) newInFile = added;
        });
        const f = files[k];
        if (k !== current) {
          files.forEach((g, j) => g.scroller.classList.toggle("is-away", j !== k));
          if (current >= 0 && !reduced()) {
            f.scroller.classList.remove("is-arriving");
            void f.scroller.offsetWidth;
            f.scroller.classList.add("is-arriving");
          }
          current = k;
        }
        tabs.forEach((t, j) => {
          t.classList.toggle("is-shown", j === k);
          t.classList.toggle("is-unmade", !files[j].made);
        });
        empty.classList.toggle("is-hidden", f.made);
        fileBody.querySelectorAll(".gs-caret").forEach((c) => c.remove());
        const written = f.rowEls.some((r) => shownAt(r, i));
        const caretAt = newInFile[newInFile.length - 1] || (f.made && !written ? f.blank : null);
        if (caretAt) caretAt.firstChild.append(make("span", "gs-caret"));
      }
      const newInTerm = reveal(termRows, i, forward);

      target = newInFile.length ? newInFile : newInTerm;
      up = !newInFile.length;
      steps[i].classList.toggle("is-unanchored", !target.length);
      setTimeout(scrollFile, 0);
      follow(700);
    }

    // The file scrolls, as an editor would, to keep the new lines in view. It goes by where
    // the lines will be, a line apart, since those being shown or hidden are still growing
    // or shrinking: after a jump of several steps, most of them are. When the new lines
    // can't all be in view (an import at the top, and code further down), the longest run
    // of them is.
    function scrollFile() {
      if (current < 0) return;
      const scroller = files[current].scroller;
      const rows = target.length && !up ? target : [];
      const shown = [...scroller.children].filter((r) => !r.classList.contains("is-hidden"));
      const lh = parseFloat(getComputedStyle(fileBody).lineHeight);
      // In the body's own coordinates, padding included, before any scrolling
      const height = fileBody.clientHeight, pad = parseFloat(getComputedStyle(fileBody).paddingTop);
      const most = Math.max(0, shown.length * lh + 2 * pad - height);
      let offset = 0;
      if (rows.length && most > 0) {
        let from = shown.indexOf(rows[0]), to = shown.indexOf(rows[rows.length - 1]);
        if ((to - from + 1) * lh > height - 2 * pad) {
          // The runs of new lines, blank ones included, and the longest of them
          const runs = [];
          shown.forEach((r, j) => {
            if (!r.classList.contains("is-new")) return;
            const run = runs[runs.length - 1];
            if (run && run[1] === j - 1) run[1] = j;
            else runs.push([j, j]);
          });
          [from, to] = runs.reduce((a, b) => (b[1] - b[0] > a[1] - a[0] ? b : a));
        }
        const top = from * lh, bottom = (to + 1) * lh;
        offset = clamp((top + bottom) / 2 - height / 2, 0, most);
      } else {
        offset = Math.min(+scroller.dataset.offset || 0, most);
      }
      scroller.dataset.offset = offset;
      scroller.style.transform = `translateY(${-offset}px)`;
      follow(600);
    }

    // The note beside the lines it adds, its bar at least as tall as they are. It starts
    // at their first line, or hangs above their last (the terminal's, or when there is
    // no room below), and moves as little as it must to stay in the window. Its tab
    // points at the line it starts or ends at. A step that adds no lines has its note at
    // the top, with no tab.
    function place() {
      if (active < 0) return;
      const note = steps[active];
      if (!target.length) {
        note.style.setProperty("--span", "0px");
        note.style.setProperty("--top", "0px");
        return;
      }
      const box = stage.getBoundingClientRect();
      // The lines' extent within what their panel shows, from the stage's top
      const view = (up ? termBody : fileBody).getBoundingClientRect();
      const first = Math.max(target[0].getBoundingClientRect().top, view.top) - box.top;
      const last = Math.min(target[target.length - 1].getBoundingClientRect().bottom, view.bottom) - box.top;
      const row = target[0].offsetHeight;
      const span = Math.max(0, last - first);
      const height = Math.max(span, note.offsetHeight);
      const room = window.innerHeight - box.top - 16;
      const hang = up || first + height > room;
      const top = clamp(hang ? last - height : first, 0, Math.max(0, room - height));
      const tab = clamp((hang ? last - row / 2 : first + row / 2) - top, row / 2, height - row / 2);
      note.style.setProperty("--span", `${span}px`);
      note.style.setProperty("--top", `${top}px`);
      note.style.setProperty("--tab", `${tab}px`);
    }
    let until = 0, frame = 0;
    function follow(ms) {
      until = Math.max(until, performance.now() + ms);
      if (!frame) frame = requestAnimationFrame(tick);
    }
    function tick(now) {
      frame = 0;
      place();
      if (now < until) frame = requestAnimationFrame(tick);
    }

    // Which step: how far the page has scrolled through the pinned stage
    const live = () => root.classList.contains("gs--live");
    const pinnedAt = () => parseFloat(getComputedStyle(stage).top) || 0;
    const travel = () => root.offsetHeight - stage.offsetHeight;
    const stepOf = (id) => steps.findIndex((s) => s.querySelector(`[id="${CSS.escape(id)}"]`));
    const tocLinks = steps.map((s) => {
      const id = s.querySelector("h2[id]")?.id;
      return id ? document.querySelector(`.md-nav a.md-nav__link[href="#${CSS.escape(id)}"]`) : null;
    });
    function onScroll() {
      if (!live()) return;
      const done = (pinnedAt() - root.getBoundingClientRect().top) / travel();
      const i = Math.floor(clamp(done, 0, 0.9999) * steps.length);
      if (i !== active) show(i);
      // The note is placed for where the stage is: until it is pinned, that changes as the
      // page scrolls, within one step (the first, shown as the page loads).
      else follow(0);
      // The contents: before the steps nothing is current, and after them all are passed.
      const at = done < 0 ? -1 : done >= 1 ? steps.length : i;
      tocLinks.forEach((a, j) => {
        a?.classList.toggle("gs-done", j < at);
        a?.classList.toggle("gs-now", j === at);
      });
    }
    function scrollToStep(i, smooth) {
      const top = window.scrollY + root.getBoundingClientRect().top - pinnedAt() + ((i + 0.5) / steps.length) * travel();
      window.scrollTo({ top, behavior: smooth && !reduced() ? "smooth" : "auto" });
    }

    // The contents' links to a step's heading go to where that step is shown.
    document.addEventListener("click", (e) => {
      const a = e.target.closest && e.target.closest('a[href^="#"]');
      if (!a || !live()) return;
      const id = decodeURIComponent(a.getAttribute("href").slice(1));
      const i = stepOf(id);
      if (i < 0) return;
      e.preventDefault();
      history.replaceState(null, "", `#${id}`);
      scrollToStep(i, true);
    }, true);

    const wide = window.matchMedia(WIDE);
    function setLive() {
      root.classList.toggle("gs--live", wide.matches);
      tocLinks.forEach((a, j) => {
        if (!a) return;
        if (wide.matches) a.dataset.gsStep = j;
        else delete a.dataset.gsStep;
      });
      active = -1;
      onScroll();
    }
    wide.addEventListener("change", setLive);
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", () => follow(0));
    // Opening or closing an aside in a note changes its height: place it again.
    root.addEventListener("toggle", () => follow(300), true);
    setLive();

    // A link straight to a step: after the browser's own jump to the heading, which
    // lands wherever the pinned heading happens to be.
    function toHash() {
      const i = stepOf(decodeURIComponent(location.hash.slice(1)));
      if (i >= 0 && live()) scrollToStep(i, false);
    }
    window.addEventListener("hashchange", toHash);
    if (document.readyState === "complete") setTimeout(toHash, 50);
    else window.addEventListener("load", () => setTimeout(toHash, 50));
  }

  // The screenshot's numbered pins pop in when it comes into view.
  function pins() {
    const shot = document.querySelector(".gs-shot");
    if (!shot || shot.dataset.ready || reduced() || !("IntersectionObserver" in window)) return;
    shot.dataset.ready = "1";
    shot.classList.add("is-armed");
    const seen = new IntersectionObserver((es) => {
      if (es.some((e) => e.isIntersecting)) {
        shot.classList.add("is-shown");
        seen.disconnect();
      }
    }, { threshold: 0.4 });
    seen.observe(shot);
  }

  function init() {
    document.querySelectorAll(".gs").forEach(mount);
    pins();
  }
  if (window.document$ && typeof window.document$.subscribe === "function") window.document$.subscribe(init);
  else if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
