// The theme follows the OS until the toggle is used, and then stays as chosen for
// the session. It is applied as `data-theme` on <html> (see tokens.css).
import { useEffect, useLayoutEffect, useState } from "preact/hooks";
import { load, save } from "./session.js";

const darkQuery = matchMedia("(prefers-color-scheme: dark)");
const systemTheme = () => (darkQuery.matches ? "dark" : "light");

export function useTheme() {
  const [choice, setChoice] = useState(() => load("theme", null)); // null: follow the OS
  const [system, setSystem] = useState(systemTheme);

  useEffect(() => {
    const onChange = () => setSystem(systemTheme());
    darkQuery.addEventListener("change", onChange);
    return () => darkQuery.removeEventListener("change", onChange);
  }, []);

  const theme = choice ?? system;

  // A layout effect, so the theme is on the page before any component's own
  // effects run: the plot reads its colours from it when it is made again.
  useLayoutEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  useLayoutEffect(() => save("theme", choice), [choice]);

  const toggle = () => setChoice(theme === "dark" ? "light" : "dark");
  return { theme, toggle };
}
