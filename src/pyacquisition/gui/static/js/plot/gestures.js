// Zooming and panning a uPlot with the pointer and the wheel, for both kinds
// of panel (plot.js and trace-panel.js):
//
// - left-drag draws a box and zooms into it (a thin box zooms one axis only,
//   and a tiny one is a click);
// - right-drag, middle-drag or Shift+left-drag pans;
// - scrolling pans (up and down pans y, sideways or Shift with a wheel pans x,
//   so a trackpad pans both at once), and Ctrl zooms about the pointer (a
//   trackpad's pinch, too);
// - a double-click turns autoscaling back on.
//
// The panel is told of each new view (`setView`), and of where the pointer is
// over the plot (`onPointer`, null when it leaves), for its readout.
import { panned, valueAt, zoomedAbout } from "./draw.js";

const THIN = 10; // a drag box thinner than this (px) zooms one axis only
const CLICK = 4; // a drag box smaller than this both ways is a click
const LINE_PIXELS = 16; // a scroll given in lines, in pixels
const WHEEL_ZOOM = 1.2; // per wheel notch, with Ctrl

// `scalesNow()` gives what the axes show ({x, y}, each {min, max, log});
// `setView({x, y})` holds a new view; `fitY(x)` gives a y scale fitted to what
// is within an x range (for a zoom of x only); `onAutoscale()` lets go of the
// view; `onPointer(point, now)` is told where the pointer is (`now` when the
// readout should follow at once), and `onGesture()` when a drag starts.
// Returns `active()`, whether a drag is under way.
export function attachGestures(u, { scalesNow, setView, fitY, onAutoscale, onPointer, onGesture }) {
  const selection = document.createElement("div");
  selection.className = "plot-selection";
  u.over.append(selection);
  let gesture = null;

  const local = (event) => {
    const rect = u.over.getBoundingClientRect();
    return { x: event.clientX - rect.left, y: event.clientY - rect.top };
  };

  const onDown = (event) => {
    const point = local(event);
    const pan =
      event.button === 2 || event.button === 1 || (event.button === 0 && event.shiftKey);
    if (!pan && event.button !== 0) return;
    event.preventDefault();
    u.over.setPointerCapture(event.pointerId);
    gesture = { kind: pan ? "pan" : "zoom", start: point, scales: scalesNow() };
    onGesture?.();
  };

  const onMove = (event) => {
    const point = local(event);
    if (!gesture) {
      onPointer(point, false);
      return;
    }
    const width = u.over.clientWidth;
    const height = u.over.clientHeight;
    if (gesture.kind === "pan") {
      setView({
        x: panned(gesture.scales.x, -(point.x - gesture.start.x) / width),
        y: panned(gesture.scales.y, (point.y - gesture.start.y) / height),
      });
      return;
    }
    const left = Math.max(0, Math.min(point.x, gesture.start.x));
    const top = Math.max(0, Math.min(point.y, gesture.start.y));
    const right = Math.min(width, Math.max(point.x, gesture.start.x));
    const bottom = Math.min(height, Math.max(point.y, gesture.start.y));
    const thinY = bottom - top < THIN;
    const thinX = right - left < THIN;
    // A thin box zooms one axis only: shown across the whole of the other.
    Object.assign(selection.style, {
      display: "block",
      left: `${thinX && !thinY ? 0 : left}px`,
      width: `${thinX && !thinY ? width : right - left}px`,
      top: `${thinY && !thinX ? 0 : top}px`,
      height: `${thinY && !thinX ? height : bottom - top}px`,
    });
    gesture.box = { left, top, right, bottom, thinX, thinY };
  };

  const onUp = (event) => {
    if (!gesture) return;
    const done = gesture;
    gesture = null;
    selection.style.display = "none";
    if (done.kind !== "zoom" || !done.box) return;
    const { left, top, right, bottom, thinX, thinY } = done.box;
    if (right - left < CLICK && bottom - top < CLICK) return; // a click
    const width = u.over.clientWidth;
    const height = u.over.clientHeight;
    const { x: xs, y: ys } = done.scales;
    let nextX = xs;
    let nextY = ys;
    if (!thinX || thinY) {
      nextX = { ...xs, min: valueAt(xs, left / width), max: valueAt(xs, right / width) };
    }
    if (!thinY || thinX) {
      nextY = { ...ys, min: valueAt(ys, 1 - bottom / height), max: valueAt(ys, 1 - top / height) };
    } else {
      nextY = fitY(nextX); // only x was zoomed: fit y
    }
    setView({ x: nextX, y: nextY });
    onPointer(local(event), true);
  };

  const onWheel = (event) => {
    event.preventDefault();
    const scales = scalesNow(); // what is shown, whatever set it
    const width = u.over.clientWidth;
    const height = u.over.clientHeight;
    const perLine = event.deltaMode === 1 ? LINE_PIXELS : event.deltaMode === 2 ? height : 1;
    let dx = event.deltaX * perLine;
    let dy = event.deltaY * perLine;
    if (event.shiftKey && dx === 0) [dx, dy] = [dy, 0]; // a wheel, sideways
    if (dx === 0 && dy === 0) return;
    if (event.ctrlKey) {
      const point = local(event);
      const factor = WHEEL_ZOOM ** Math.sign(dy || dx);
      setView({
        x: zoomedAbout(scales.x, factor, point.x / width),
        y: zoomedAbout(scales.y, factor, 1 - point.y / height),
      });
      return;
    }
    setView({ x: panned(scales.x, dx / width), y: panned(scales.y, -dy / height) });
  };

  u.over.addEventListener("pointerdown", onDown);
  u.over.addEventListener("pointermove", onMove);
  u.over.addEventListener("pointerup", onUp);
  u.over.addEventListener("pointercancel", onUp);
  u.over.addEventListener("pointerleave", () => onPointer(null, true));
  u.over.addEventListener("wheel", onWheel, { passive: false });
  u.over.addEventListener("dblclick", () => onAutoscale?.());
  // The right button pans, so the browser's menu stays away from the plot.
  u.over.addEventListener("contextmenu", (event) => event.preventDefault());

  return { active: () => gesture !== null };
}
