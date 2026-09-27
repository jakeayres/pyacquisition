// The dock along the bottom: a strip of tabs, and the open tab's panel above
// the rest of the window. It can be resized by dragging its top edge (or with the
// arrow keys on it), and collapsed to just the tab strip. Its height, the open tab
// and whether it is collapsed last for the session.
import { useEffect, useLayoutEffect, useRef, useState } from "preact/hooks";
import { html } from "./html.js";
import { load, save } from "./session.js";
import { ChevronDownIcon, ChevronUpIcon } from "./icons.js";

const KEY_STEP = 16; // pixels per arrow key press on the resize handle
const KEY_STEP_LARGE = 64; // with Shift

function cssPixels(name) {
  return parseFloat(getComputedStyle(document.documentElement).getPropertyValue(name));
}

// The heights the dock may take while open: at least its minimum, and never so
// tall that the plots get less than theirs.
function limits() {
  const min = cssPixels("--dock-min-height");
  const max =
    window.innerHeight - cssPixels("--topbar-height") - cssPixels("--plot-min-height");
  return { min, max: Math.max(min, max) };
}

const clamp = (height) => {
  const { min, max } = limits();
  return Math.round(Math.min(max, Math.max(min, height)));
};

export function Dock({ tabs }) {
  const [saved] = useState(() => load("dock", {}));
  const [active, setActive] = useState(
    tabs.some((tab) => tab.id === saved.active) ? saved.active : tabs[0].id,
  );
  const [collapsed, setCollapsed] = useState(saved.collapsed ?? false);
  const [height, setHeight] = useState(() =>
    clamp(saved.height ?? window.innerHeight * 0.3),
  );
  const [resizing, setResizing] = useState(false);
  const tabRefs = useRef({});

  // Saved as the change is made (a layout effect), not after the next paint, so
  // a reload straight afterwards keeps it.
  useLayoutEffect(
    () => save("dock", { active, collapsed, height }),
    [active, collapsed, height],
  );

  // Something elsewhere (the top bar's running task) asks for a tab to open.
  useEffect(() => {
    const open = (event) => {
      if (tabs.some((tab) => tab.id === event.detail)) {
        setActive(event.detail);
        setCollapsed(false);
      }
    };
    window.addEventListener("pyacquisition:open-tab", open);
    return () => window.removeEventListener("pyacquisition:open-tab", open);
  }, [tabs.map((tab) => tab.id).join()]);

  // A smaller window can leave the dock too tall for it.
  useEffect(() => {
    const onResize = () => setHeight((current) => clamp(current));
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  useEffect(() => {
    document.body.classList.toggle("resizing-dock", resizing);
  }, [resizing]);

  // Clicking the open tab collapses the dock, and any tab opens it.
  const select = (id) => {
    if (id === active && !collapsed) {
      setCollapsed(true);
    } else {
      setActive(id);
      setCollapsed(false);
    }
  };

  const onTabKey = (event, index) => {
    const moves = { ArrowRight: 1, ArrowLeft: -1 };
    if (!(event.key in moves)) return;
    event.preventDefault();
    const next = tabs[(index + moves[event.key] + tabs.length) % tabs.length];
    setActive(next.id);
    setCollapsed(false);
    tabRefs.current[next.id]?.focus();
  };

  const startResize = (event) => {
    if (event.button !== 0) return;
    event.preventDefault();
    const handle = event.currentTarget;
    const startY = event.clientY;
    const startHeight = collapsed ? limits().min : height;
    handle.setPointerCapture(event.pointerId);
    setResizing(true);

    const move = (e) => {
      const wanted = startHeight + (startY - e.clientY);
      // Dragged most of the way down: collapse, as a collapse button would.
      if (wanted < limits().min / 2) {
        setCollapsed(true);
      } else {
        setCollapsed(false);
        setHeight(clamp(wanted));
      }
    };
    const end = () => {
      handle.removeEventListener("pointermove", move);
      handle.removeEventListener("pointerup", end);
      handle.removeEventListener("pointercancel", end);
      setResizing(false);
    };
    handle.addEventListener("pointermove", move);
    handle.addEventListener("pointerup", end);
    handle.addEventListener("pointercancel", end);
  };

  const onHandleKey = (event) => {
    const step = event.shiftKey ? KEY_STEP_LARGE : KEY_STEP;
    const { min, max } = limits();
    const changes = {
      ArrowUp: () => clamp(height + step),
      ArrowDown: () => clamp(height - step),
      Home: () => min,
      End: () => max,
    };
    if (event.key in changes) {
      event.preventDefault();
      setCollapsed(false);
      setHeight(changes[event.key]());
    } else if (event.key === "Enter") {
      event.preventDefault();
      setCollapsed(!collapsed);
    }
  };

  const { min, max } = limits();
  const current = tabs.find((tab) => tab.id === active);

  return html`
    <section
      class="dock ${collapsed ? "collapsed" : ""} ${resizing ? "resizing" : ""}"
      style=${{ "--dock-height": `${height}px` }}
    >
      <div
        class="dock-resize"
        role="separator"
        aria-orientation="horizontal"
        aria-label="Resize the dock"
        aria-valuemin=${min}
        aria-valuemax=${max}
        aria-valuenow=${collapsed ? 0 : height}
        tabindex="0"
        onPointerDown=${startResize}
        onDblClick=${() => setCollapsed(!collapsed)}
        onKeyDown=${onHandleKey}
      ></div>
      <div class="dock-tabs" role="tablist" aria-label="Dock">
        ${tabs.map(
          (tab, index) => html`
            <button
              key=${tab.id}
              ref=${(element) => (tabRefs.current[tab.id] = element)}
              class="dock-tab"
              role="tab"
              id="dock-tab-${tab.id}"
              aria-selected=${tab.id === active}
              aria-controls="dock-panel"
              tabindex=${tab.id === active ? 0 : -1}
              onClick=${() => select(tab.id)}
              onKeyDown=${(event) => onTabKey(event, index)}
            >
              ${tab.label}
            </button>
          `,
        )}
        <div class="dock-tabs-end">
          <button
            class="icon-button"
            aria-label=${collapsed ? "Show the dock" : "Hide the dock"}
            title=${collapsed ? "Show the dock" : "Hide the dock"}
            aria-expanded=${!collapsed}
            onClick=${() => setCollapsed(!collapsed)}
          >
            ${collapsed ? html`<${ChevronUpIcon} />` : html`<${ChevronDownIcon} />`}
          </button>
        </div>
      </div>
      <div
        class="dock-panel ${current.fill ? "dock-panel-fill" : ""}"
        id="dock-panel"
        role="tabpanel"
        aria-labelledby="dock-tab-${active}"
      >
        ${current.content}
      </div>
    </section>
  `;
}
