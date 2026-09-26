import { useEffect, useState } from "preact/hooks";

// Re-renders the component whenever the store changes (at most once a frame).
export function useStore(store) {
  const [, setVersion] = useState(store.version);
  useEffect(() => store.subscribe((changed) => setVersion(changed.version)), [store]);
  return store;
}
