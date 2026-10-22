// SPDX-License-Identifier: MPL-2.0
// Copyright (C) 2023-2026 Jake Ayres
//
// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.

/* The front page. Its hero is the script beside the interface it makes, running
   in a frame (docs/demo/), in one pane of glass. For the hero, this script:

   - scales the frame, which is drawn at the interface's own size, to its window;
   - holds the demo's rows while the hero is out of view, so it costs nothing;
   - says how to copy the interface's files in, when they are missing (a local
     preview that hasn't made the copy, see CONTRIBUTING.md);
   - runs the tour: each step lights up some lines of the script and the parts of
     the interface they make, joined by a line. Hovering either side shows its
     step. Using the interface stops the tour for a while.

   The frame is served from the same site, so its document can be read here.
   Without this script the hero still shows the script and the interface.

   It also runs the "Or build it in a window" section's switcher: three tabs, each
   showing a picture of the setup page, which go round by themselves while the
   section is in view, unless it is being used or motion is reduced. */
(() => {
  "use strict";

  const APP_W = 1000; // the widest the interface is laid out
  const MIN_W = 880; // the narrowest it is laid out at: four value tiles in a row
  const SCALE = 0.8; // the scale it is drawn at, where it can be: legible, and not cramped
  const STEP = 2800; // milliseconds a step of the tour shows for
  const BACK_AFTER_HOVER = 1500; // before the tour carries on after a hover
  const BACK_AFTER_USE = 8000; // ... and after the interface was used
  const still = matchMedia("(prefers-reduced-motion: reduce)").matches;

  const chips = (name) => (doc) =>
    [...doc.querySelectorAll(".series-chip")].filter(
      (chip) => (chip.querySelector(".series-name")?.textContent ?? "").split(" (")[0] === name,
    );
  const first = (selector) => (doc) => [doc.querySelector(selector)].filter(Boolean);

  // Each step: the lines of the script (the first that has `from`, and the
  // `lines` from there), and what they make in the interface.
  const STEPS = [
    { from: "class MyExperiment", lines: 1, targets: [".brand-name"] },
    { from: "data_path", lines: 1, targets: [".file-control .topbar-chip"] },
    {
      from: 'Clock("clock")',
      lines: 3,
      targets: ['[data-column="time"]', first(".plot-panel .picker")],
    },
    {
      from: 'SR_830("lockin"',
      lines: 4,
      targets: ['[data-column="x"]', '[data-column="y"]', chips("x"), chips("y")],
    },
    { from: 'Lakeshore_350("lakeshore"', lines: 10, targets: ['[data-column="T"]', chips("T")] },
    { from: "if __name__", lines: 2, targets: [".rack-control", ".connection"] },
  ];

  function hero(stage) {
    const frame = stage.querySelector(".pa-window__view iframe");
    const view = frame.parentElement;
    const code = stage.querySelector(".pa-stage__code");
    const lines = [...code.querySelectorAll('code > span[id^="__span"]')];
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.classList.add("pa-tour");
    svg.setAttribute("aria-hidden", "true");
    stage.append(svg);

    // Which lines each step has.
    for (const step of STEPS) {
      const at = lines.findIndex((line) => line.textContent.includes(step.from));
      step.spans = at < 0 ? [] : lines.slice(at, at + step.lines);
    }

    // ---------------------------------------------------------------- scaling
    // The interface is laid out as wide as its window would make a scale of 0.8,
    // between 880 and 1000 pixels, and scaled to the window. In a narrow window
    // (a phone) it is laid out 880 wide, and only scaled. (At 880 its four value
    // tiles fit in a row, minmax(200px) each in app.css.)
    let scale = 1;
    const fit = () => {
      const width = view.clientWidth;
      if (!width) return;
      const app = Math.min(APP_W, Math.max(MIN_W, width / SCALE));
      scale = Math.min(1, width / app);
      stage.style.setProperty("--pa-scale", String(scale));
      stage.style.setProperty("--pa-app-w", String(Math.round(width / scale)));
    };
    new ResizeObserver(fit).observe(view);
    fit();

    // ------------------------------------------------- the demo, and its holds
    const demo = () => {
      try {
        return frame.contentWindow?.pyacquisitionDemo ?? null;
      } catch {
        return null;
      }
    };
    let onScreen = true;
    const holdIfAway = () => {
      if (onScreen) demo()?.release("away");
      else demo()?.hold("away");
    };
    new IntersectionObserver(([entry]) => {
      onScreen = entry.isIntersecting;
      holdIfAway();
      stage.closest(".pa-live")?.toggleAttribute("data-away", !onScreen);
      if (onScreen) draw();
    }).observe(stage);

    // While the page scrolls, the interface waits: it shares the page's main thread,
    // and scrolling goes more smoothly without its plots redrawing. It carries on a
    // moment after the scrolling stops.
    // The lights behind the glass stop drifting then too, and while the hero is out
    // of view: Chrome does work on the main thread for them on every frame.
    const band = stage.closest(".pa-live") ?? stage;
    let settle = null;
    window.addEventListener(
      "scroll",
      () => {
        demo()?.hold("scrolling");
        band.setAttribute("data-scrolling", "");
        clearTimeout(settle);
        settle = setTimeout(() => {
          demo()?.release("scrolling");
          band.removeAttribute("data-scrolling");
        }, 250);
      },
      { passive: true },
    );

    // ---------------------------------------------------------- click to use it
    // The interface's plots take the wheel, to pan, so the page would stop
    // scrolling under the pointer, and wait for the interface at every notch. So
    // the page scrolls over the frame until it is clicked, as over a map in a page,
    // and again once the pointer has left it.
    const shield = document.createElement("button");
    shield.type = "button";
    shield.className = "pa-window__shield";
    shield.setAttribute("aria-label", "Use the interface");
    shield.innerHTML = "<span>Click to try it</span>";
    view.append(shield);
    let leaving = null;
    shield.addEventListener("click", () => {
      view.classList.add("is-active");
      pause();
      show(null);
      frame.focus();
    });
    view.addEventListener("mouseenter", () => clearTimeout(leaving));
    view.addEventListener("mouseleave", () => {
      clearTimeout(leaving);
      leaving = setTimeout(() => view.classList.remove("is-active"), 400);
    });
    frame.addEventListener("load", () => {
      holdIfAway();
      listen();
    });

    const src = new URL(frame.getAttribute("src"), location.href);
    fetch(new URL("app/js/main.js", src), { method: "HEAD" })
      .then((response) => {
        if (!response.ok) missing();
      })
      .catch(missing);

    function missing() {
      view.innerHTML =
        '<div class="pa-window__missing"><p>The interface\'s files are copied in when the ' +
        "docs are built. To preview the demo, copy them from the repository's root:</p>" +
        "<code>uv run python -c \"import shutil; shutil.copytree('src/pyacquisition/gui/static', " +
        "'docs/demo/app', dirs_exist_ok=True)\"</code></div>";
      view.style.height = "auto";
    }

    // ---------------------------------------------------------------- the tour
    let shown = null; // the step shown, or null
    let used = false; // whether the interface has been used since the pointer came
    let auto = !still;
    let timer = null;
    let at = -1;

    function show(step) {
      if (step === shown) return;
      shown = step;
      for (const line of lines) line.classList.toggle("pa-on", !!step && step.spans.includes(line));
      stage.toggleAttribute("data-touring", !!step);
      draw();
    }

    function next() {
      at = (at + 1) % STEPS.length;
      show(STEPS[at]);
      timer = setTimeout(next, STEP);
    }

    function resume(after) {
      clearTimeout(timer);
      if (!auto) return;
      timer = setTimeout(next, after);
    }

    function pause() {
      clearTimeout(timer);
    }

    // The parts of the interface a step points at.
    function targets(step, doc) {
      const found = [];
      for (const target of step.targets) {
        if (typeof target === "function") found.push(...target(doc));
        else found.push(...doc.querySelectorAll(target));
      }
      return found;
    }

    function draw() {
      svg.replaceChildren();
      if (!shown || !onScreen) return;
      const doc = frame.contentDocument;
      if (!doc) return;
      const box = stage.getBoundingClientRect();
      const frameBox = frame.getBoundingClientRect();
      const viewBox = view.getBoundingClientRect();
      const ns = "http://www.w3.org/2000/svg";
      const add = (name, attributes) => {
        const element = document.createElementNS(ns, name);
        for (const [key, value] of Object.entries(attributes)) element.setAttribute(key, value);
        svg.append(element);
      };

      // Where the line leaves the script: its right edge, level with the lines.
      const spans = shown.spans.map((span) => span.getBoundingClientRect());
      const codeBox = code.getBoundingClientRect();
      const from =
        spans.length > 0
          ? {
              x: codeBox.right - box.left,
              y: (spans[0].top + spans.at(-1).bottom) / 2 - box.top,
            }
          : null;

      // One line, to the first part that shows; a box round each.
      let linked = false;
      for (const element of targets(shown, doc)) {
        const r = element.getBoundingClientRect();
        if (!r.width && !r.height) continue;
        const pad = 3;
        let left = frameBox.left + r.left * scale - pad;
        let top = frameBox.top + r.top * scale - pad;
        let right = frameBox.left + r.right * scale + pad;
        let bottom = frameBox.top + r.bottom * scale + pad;
        // Only what shows in the window.
        left = Math.max(left, viewBox.left);
        top = Math.max(top, viewBox.top);
        right = Math.min(right, viewBox.right);
        bottom = Math.min(bottom, viewBox.bottom);
        if (right <= left || bottom <= top) continue;
        add("rect", {
          class: "box",
          x: left - box.left,
          y: top - box.top,
          width: right - left,
          height: bottom - top,
          rx: 5,
        });
        if (from && !linked) {
          linked = true;
          const to = { x: left - box.left, y: (top + bottom) / 2 - box.top };
          const bend = Math.max(40, (to.x - from.x) / 2);
          const d = `M ${from.x} ${from.y} C ${from.x + bend} ${from.y}, ${to.x - bend} ${to.y}, ${to.x} ${to.y}`;
          add("path", { class: "halo", d }); // a soft glow, without a filter to repaint
          add("path", { class: "link", d });
          add("circle", { class: "end", cx: to.x, cy: to.y, r: 2.5 });
        }
      }
      if (from) add("circle", { class: "end", cx: from.x, cy: from.y, r: 2.5 });
    }

    // Redrawn four times a second while a step shows, as the interface updates
    // with each row: often enough to follow it, and no work on every frame. (The
    // boxes are drawn in the stage's own coordinates, so scrolling moves them with
    // it, and needs no redrawing.)
    setInterval(() => {
      if (shown && onScreen) draw();
    }, 250);

    // ------------------------------------------------------ hovering, using it
    const stepOfLine = (line) => STEPS.find((step) => step.spans.includes(line));

    code.addEventListener("mouseover", (event) => {
      const line = event.target.closest?.('span[id^="__span"]');
      const step = line && stepOfLine(line);
      pause();
      show(step ?? null);
    });
    code.addEventListener("mouseleave", () => {
      if (still) show(null);
      resume(BACK_AFTER_HOVER);
    });

    function listen() {
      const doc = frame.contentDocument;
      if (!doc) return;
      doc.addEventListener("mouseover", (event) => {
        pause();
        const step = STEPS.find((s) =>
          targets(s, doc).some((element) => element.contains(event.target)),
        );
        show(used ? null : step ?? null);
      });
      for (const type of ["pointerdown", "keydown", "wheel"]) {
        doc.addEventListener(
          type,
          () => {
            used = true;
            pause();
            show(null);
          },
          { passive: true },
        );
      }
    }
    view.addEventListener("mouseleave", () => {
      show(null);
      resume(used ? BACK_AFTER_USE : BACK_AFTER_HOVER);
      used = false;
    });

    // Start once the glass has risen into place, and the interface has drawn
    // what the tour points at.
    const begin = () => {
      const doc = frame.contentDocument;
      const settled = stage.getAnimations().every((a) => a.playState === "finished");
      if (settled && doc?.querySelector('[data-column="T"]')) resume(600);
      else setTimeout(begin, 300);
    };
    begin();
  }

  // ------------------------------------------------------------ the switcher
  const DWELL = 6000; // milliseconds each tab shows for, going round by itself

  function switcher(root) {
    const tabs = [...root.querySelectorAll('[role="tab"]')];
    const shots = tabs.map((tab) => document.getElementById(tab.getAttribute("aria-controls")));
    root.style.setProperty("--pa-dwell", `${DWELL}ms`);
    let at = 0;
    let timer = null;
    let inView = false;
    let busy = false; // hovered or focused

    function select(i, { focus = false } = {}) {
      at = (i + tabs.length) % tabs.length;
      tabs.forEach((tab, j) => {
        const on = j === at;
        tab.setAttribute("aria-selected", String(on));
        tab.tabIndex = on ? 0 : -1;
        shots[j].classList.toggle("is-on", on);
      });
      if (focus) tabs[at].focus();
      play();
    }

    // Goes round while in view and left alone. The bar under the open tab shows
    // how long until the next; it starts again from nothing each time.
    function play() {
      clearTimeout(timer);
      root.removeAttribute("data-playing");
      if (still || !inView || busy) return;
      void root.offsetWidth; // so the bar's animation starts again
      root.setAttribute("data-playing", "");
      timer = setTimeout(() => select(at + 1), DWELL);
    }

    tabs.forEach((tab, i) => tab.addEventListener("click", () => select(i)));
    root.querySelector('[role="tablist"]').addEventListener("keydown", (event) => {
      const step = { ArrowDown: 1, ArrowRight: 1, ArrowUp: -1, ArrowLeft: -1 }[event.key];
      if (step) {
        event.preventDefault();
        select(at + step, { focus: true });
      }
    });
    const hold = (on) => () => {
      busy = on;
      play();
    };
    root.addEventListener("mouseenter", hold(true));
    root.addEventListener("mouseleave", hold(false));
    root.addEventListener("focusin", hold(true));
    root.addEventListener("focusout", hold(false));
    new IntersectionObserver(
      ([entry]) => {
        inView = entry.isIntersecting;
        play();
      },
      { threshold: 0.4 },
    ).observe(root);
  }

  function init() {
    for (const stage of document.querySelectorAll(".pa-stage:not([data-ready])")) {
      stage.setAttribute("data-ready", "");
      hero(stage);
    }
    for (const root of document.querySelectorAll(".pa-switch:not([data-ready])")) {
      root.setAttribute("data-ready", "");
      switcher(root);
    }
  }

  if (window.document$ && typeof window.document$.subscribe === "function") window.document$.subscribe(init);
  else if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
