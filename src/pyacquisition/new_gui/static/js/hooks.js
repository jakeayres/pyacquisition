import { useEffect, useLayoutEffect, useState } from "preact/hooks";

// Re-renders the component whenever the store changes (at most once a frame).
export function useStore(store) {
  const [, setVersion] = useState(store.version);
  useEffect(() => store.subscribe((changed) => setVersion(changed.version)), [store]);
  return store;
}

// A panel that pops over the page (the axis settings, the top bar's menus): while
// `open`, pressing anywhere outside `ref`'s element, or Escape, calls `close`.
// Listened for as soon as it opens (a layout effect), not after the next paint,
// so an Escape pressed straight away still closes it.
export function usePopover(ref, open, close) {
  useLayoutEffect(() => {
    if (!open) return;
    const outside = (event) => ref.current && !ref.current.contains(event.target) && close();
    const escape = (event) => event.key === "Escape" && close();
    document.addEventListener("pointerdown", outside);
    document.addEventListener("keydown", escape);
    return () => {
      document.removeEventListener("pointerdown", outside);
      document.removeEventListener("keydown", escape);
    };
  }, [open]);
}
