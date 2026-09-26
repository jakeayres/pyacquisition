// Dragging a queued task to a new place by its handle. While dragging, a line
// shows where it will go, and the dock scrolls when the pointer nears its top or
// bottom edge. Escape, or losing the pointer, puts it back.
//
// Places are gaps between rows: gap i is just before row i, and gap n (the row
// count) is after the last. Dropping row `from` in gap `gap` puts it at
// `dropIndex(from, gap)`.
import { useRef, useState } from "preact/hooks";

const EDGE = 36; // pixels from the scrolling area's edge where it starts to scroll
const SPEED = 10; // pixels scrolled a frame, there

export const dropIndex = (from, gap) => (gap > from ? gap - 1 : gap);

// The ids in their new order, with the one at `from` moved to `to`.
export function reorder(ids, from, to) {
  const next = [...ids];
  next.splice(to, 0, next.splice(from, 1)[0]);
  return next;
}

// `list` is a ref to the <ol> of rows (each `.queued-task`). `onPlace(id, from,
// to)` is called when a row is dropped somewhere new. Returns {drag, start}:
// `drag` is {id, from, gap} while dragging, and `start(event, id, index)` goes
// on the handle's pointerdown.
export function useQueueDrag(list, onPlace) {
  const [drag, setDrag] = useState(null);
  const live = useRef(null);

  const rows = () => [...(list.current?.querySelectorAll(":scope > .queued-task") ?? [])];

  const gapAt = (y) => {
    const all = rows();
    for (let i = 0; i < all.length; i++) {
      const box = all[i].getBoundingClientRect();
      if (y < box.top + box.height / 2) return i;
    }
    return all.length;
  };

  const update = () => {
    const d = live.current;
    const gap = gapAt(d.y);
    if (gap !== d.gap) {
      d.gap = gap;
      setDrag({ id: d.id, from: d.from, gap });
    }
  };

  // Scrolls while the pointer is held near an edge, a little each frame.
  const scroll = () => {
    const d = live.current;
    if (!d) return;
    const box = d.scroller.getBoundingClientRect();
    const step = d.y < box.top + EDGE ? -SPEED : d.y > box.bottom - EDGE ? SPEED : 0;
    if (step) {
      d.scroller.scrollTop += step;
      update();
    }
    d.frame = requestAnimationFrame(scroll);
  };

  const start = (event, id, index) => {
    if (event.button !== 0) return;
    event.preventDefault();
    const handle = event.currentTarget;
    handle.setPointerCapture(event.pointerId);
    live.current = {
      id,
      from: index,
      gap: index,
      y: event.clientY,
      scroller: handle.closest(".dock-panel") ?? document.documentElement,
    };
    setDrag({ id, from: index, gap: index });
    live.current.frame = requestAnimationFrame(scroll);
    document.body.classList.add("dragging-task");

    const move = (e) => {
      live.current.y = e.clientY;
      update();
    };
    const finish = (commit) => {
      handle.removeEventListener("pointermove", move);
      handle.removeEventListener("pointerup", drop);
      handle.removeEventListener("pointercancel", cancel);
      window.removeEventListener("keydown", escape, true);
      document.body.classList.remove("dragging-task");
      const d = live.current;
      if (!d) return;
      cancelAnimationFrame(d.frame);
      live.current = null;
      setDrag(null);
      const to = dropIndex(d.from, d.gap);
      if (commit && to !== d.from) onPlace(d.id, d.from, to);
    };
    const drop = () => finish(true);
    const cancel = () => finish(false);
    const escape = (e) => {
      if (e.key !== "Escape") return;
      e.stopPropagation();
      finish(false);
    };
    handle.addEventListener("pointermove", move);
    handle.addEventListener("pointerup", drop);
    handle.addEventListener("pointercancel", cancel);
    window.addEventListener("keydown", escape, true);
  };

  return { drag, start };
}
