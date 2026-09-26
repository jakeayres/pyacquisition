// The colour of each quantity, the same everywhere: its tile in the Values tab,
// and its line in every plot.
//
// Quantities take the eight series colours (tokens.css) in the experiment's
// column order, so a quantity keeps its colour as long as the experiment's
// columns stay the same. A time column is nearly always the x axis, so it is
// left neutral rather than spend a colour; so is any quantity past the eighth,
// since the palette is never stretched with made-up colours.

export const PALETTE_SIZE = 8;

// A column that holds a time, such as `time`, `time_ms` or `timestamp`.
export function isTimeColumn(name) {
  return /^(time|timestamp)(_|$)|_time$/i.test(name);
}

// Each column's colour slot, 1 to 8, or null for the neutral colour.
export function colourSlots(columns) {
  const slots = new Map();
  let next = 1;
  for (const name of columns) {
    if (isTimeColumn(name) || next > PALETTE_SIZE) slots.set(name, null);
    else slots.set(name, next++);
  }
  return slots;
}

// The CSS colour for a slot, which follows the theme.
export function colourVar(slot) {
  return slot ? `var(--series-${slot})` : "var(--series-other)";
}
