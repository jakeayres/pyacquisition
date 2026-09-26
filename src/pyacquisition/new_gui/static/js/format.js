// How values are written in the interface.

// A number with six significant figures, or in exponent form when very large or
// small. Anything else as text, and a missing value as a dash.
export function formatValue(value) {
  if (value === null || value === undefined) return "—";
  if (typeof value === "boolean") return value ? "true" : "false";
  if (typeof value !== "number") return String(value);
  if (!Number.isFinite(value)) return "—";
  const size = Math.abs(value);
  if (size !== 0 && (size >= 1e6 || size < 1e-3)) return value.toExponential(4);
  return value.toPrecision(6);
}

// The full value, for a tooltip.
export function exactValue(value) {
  return typeof value === "number" ? String(value) : formatValue(value);
}
