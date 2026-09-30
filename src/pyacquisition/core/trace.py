"""Traces: a measurement that is a whole array, such as a network analyser's
sweep or a spectrometer's counts, taken with the rows, on a clock of its own, or
on demand, and saved beside the data file (see `trace_scribe.py`).

`TraceData` is one trace as an instrument gives it: one or more channels of
values over one axis.
"""

from dataclasses import dataclass, field

import numpy as np

# Names a channel can't have: the trace file's own datasets, beside the channels
# in each trace's group (see trace_scribe.py).
RESERVED = {
    "trace",
    "point",
    "time",
    "time_start",
    "rows",
    "rows_start",
    "points",
    "x",
    "x_start",
    "x_stop",
}
RESERVED_PREFIXES = ("row.", "row_start.")


def _check_name(name: str, what: str) -> None:
    if not isinstance(name, str) or not name.strip():
        raise ValueError(f"A {what} needs a name, not {name!r}.")
    if name in RESERVED or name.startswith(RESERVED_PREFIXES):
        raise ValueError(
            f"A {what} can't be called {name!r}: the trace file uses that name itself."
        )


@dataclass(frozen=True)
class TraceData:
    """One trace, as a driver's trace method returns it.

    Args:
        channels: The values, by channel name: one array, or several of the same
            length over the same axis (`{"X": x, "Y": y}`). Each is one
            dimensional and real. float32 is kept as it is; anything else is
            stored as float64.
        x: The axis. A linear one as its ends, `(start, stop)`, which is all the
            file keeps of it, or the value at every point, as an array as long as
            the channels.
        x_name: What the axis is, such as `"frequency"` or `"time"`.
        x_unit: The axis's unit, such as `"Hz"`, or None.
        unit: The channels' unit, such as `"dB"`, or None.

    Raises:
        ValueError: If the channels are empty, not one dimensional, of different
            lengths, or not numbers; if an explicit axis isn't as long as them;
            or if a channel's name is one the trace file keeps for itself.

    Example:
        ```python
        TraceData({"S21": values}, x=(1e9, 2e9), x_name="frequency",
                  x_unit="Hz", unit="dB")
        ```
    """

    channels: dict
    x: tuple | np.ndarray
    x_name: str = "x"
    x_unit: str | None = None
    unit: str | None = None
    points: int = field(init=False)

    def __post_init__(self):
        if not isinstance(self.channels, dict) or not self.channels:
            raise ValueError("A trace needs at least one channel, as {name: values}.")
        channels = {}
        for name, values in self.channels.items():
            _check_name(name, "channel")
            array = np.asarray(values)
            if array.ndim != 1:
                raise ValueError(
                    f"Channel {name!r} must be one dimensional, not of shape {array.shape}."
                )
            if not (np.issubdtype(array.dtype, np.integer) or np.issubdtype(array.dtype, np.floating)):
                raise ValueError(f"Channel {name!r} must be real numbers, not {array.dtype}.")
            channels[name] = array if array.dtype == np.float32 else array.astype(np.float64)
        lengths = {len(values) for values in channels.values()}
        if len(lengths) > 1:
            raise ValueError(f"A trace's channels must be as long as each other, not {sorted(lengths)}.")
        (points,) = lengths
        if points == 0:
            raise ValueError("A trace needs at least one point.")

        if isinstance(self.x, tuple):
            if len(self.x) != 2:
                raise ValueError("A linear axis is (start, stop).")
            x = (float(self.x[0]), float(self.x[1]))
        else:
            x = np.asarray(self.x, dtype=np.float64)
            if x.shape != (points,):
                raise ValueError(
                    f"An explicit axis must have a value for each of the {points} points, "
                    f"not the shape {x.shape}."
                )
        object.__setattr__(self, "channels", channels)
        object.__setattr__(self, "x", x)
        object.__setattr__(self, "points", points)

    @property
    def linear(self) -> bool:
        """Whether the axis is linear, given as its ends."""
        return isinstance(self.x, tuple)

    def axis(self) -> np.ndarray:
        """The axis's value at every point."""
        if self.linear:
            return np.linspace(self.x[0], self.x[1], self.points)
        return self.x

    @property
    def nbytes(self) -> int:
        """Roughly how much memory it takes."""
        size = sum(values.nbytes for values in self.channels.values())
        return size + (0 if self.linear else self.x.nbytes)
