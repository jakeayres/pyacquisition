# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2023-2026 Jake Ayres
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Following one column of the rows as they arrive, and whether it has settled,
for the tasks that wait on the data (`WaitForValue` and `WaitForStable`)."""

import math
import time
from collections import deque

# Where the time of a reading comes from. Tests replace it.
clock = time.monotonic


def slope(points) -> float | None:
    """The slope of the least-squares line through `(seconds, value)` points, in
    the value's units per second, or None if there are fewer than two times."""
    points = list(points)
    n = len(points)
    if n < 2:
        return None
    mean_t = sum(t for t, _ in points) / n
    mean_v = sum(v for _, v in points) / n
    spread = sum((t - mean_t) ** 2 for t, _ in points)
    if spread == 0:
        return None
    return sum((t - mean_t) * (v - mean_v) for t, v in points) / spread


def _beyond(amount: float, limit: float) -> bool:
    """Whether `amount` is over `limit`, by more than the rounding of floats:
    readings are often rounded to an instrument's resolution, so 7.5 - 7.3 is
    on the edge of a band 0.2 wide, not outside it."""
    return amount > limit and not math.isclose(amount, limit, rel_tol=1e-9)


def columns(experiment) -> list[str]:
    """The names of the experiment's columns: its measurements, its calculations'
    columns and its traces' columns, as `/experiment/columns` lists them."""
    return [column["name"] for column in experiment._column_info()]


class _Arrivals:
    """Where the rows are put, as a consumer's `queue` is, noting when each one
    arrived."""

    def __init__(self):
        self.items = deque()

    def put_nowait(self, message) -> None:
        self.items.append((clock(), message))

    async def put(self, message) -> None:
        self.put_nowait(message)


class Readings:
    """
    The values of one column of the rows, as they arrive, each with the time it
    arrived (rows carry no time of their own).

    Use it in a `with` block: it follows the rows from when the block starts
    until it ends, however it ends.

    Example:
        ```python
        with Readings(experiment, "T") as readings:
            await self.sleep(10)
            for seconds, kelvin in readings.new():
                ...
        ```
    """

    def __init__(self, experiment, column: str):
        """
        Args:
            experiment (Experiment): The experiment, whose rows are followed.
            column (str): The name of the column: a measurement, or a calculation's
                or a trace's column.

        Raises:
            ValueError: If the experiment has no column of that name, among
                those it knows of and those the rows have had.
        """
        units = {info["name"]: info["unit"] for info in experiment._column_info()}
        # A calculation that doesn't name its columns is known by its rows.
        for name in experiment._history.latest:
            units.setdefault(name, None)
        if column not in units:
            raise ValueError(
                f"There is no column called {column!r}: there is "
                + (", ".join(repr(name) for name in units) or "none")
                + "."
            )
        self.column = column
        self.unit = units[column] or ""
        self._history = experiment._history
        self.queue = _Arrivals()

    def __enter__(self) -> "Readings":
        self._history.subscribe(self)
        return self

    def __exit__(self, *exc) -> None:
        if self in self._history._subscribers:
            self._history.unsubscribe(self)

    def new(self) -> list[tuple[float, float]]:
        """The `(seconds, value)` of each reading that has arrived since the last
        call. A row without a number for the column (a failed measurement) is
        skipped, and so are other events, such as a new file."""
        found = []
        while self.queue.items:
            seconds, event = self.queue.items.popleft()
            if event.get("type") != "row":
                continue
            value = event["values"].get(self.column)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                continue
            if math.isfinite(value):
                found.append((seconds, float(value)))
        return found

    def clear(self) -> None:
        """Drops the readings that have arrived and not been taken."""
        self.queue.items.clear()


class Stability:
    """
    Whether readings have settled: in a band for a whole `hold`, and drifting no
    faster than `max_drift`.

    The band is `tolerance` either side of `target`, or, with no target, any
    band `2 * tolerance` wide, wherever it sits. A reading outside the band
    starts the time in it again from the next one. Times are in seconds, and
    `max_drift` is per second.

    Example:
        ```python
        check = Stability(tolerance=0.005, hold=300, max_drift=0.001 / 60, target=10)
        for seconds, kelvin in readings.new():
            check.add(seconds, kelvin)
        if check.stable:
            ...
        ```
    """

    def __init__(
        self,
        tolerance: float,
        hold: float,
        max_drift: float = 0.0,
        target: float | None = None,
    ):
        """
        Args:
            tolerance (float): How far from the target, or from the middle of the
                band, a reading may be.
            hold (float): How many seconds the readings must stay in the band.
            max_drift (float): The fastest that a line through the readings of
                the last `hold` may rise or fall, per second. 0 isn't checked.
            target (float | None): The value to settle at, or None for anywhere.
        """
        if not tolerance > 0:
            raise ValueError("tolerance must be above 0.")
        if not hold > 0:
            raise ValueError("hold must be above 0.")
        if max_drift < 0:
            raise ValueError("max_drift must not be negative.")
        self.tolerance = tolerance
        self.hold = hold
        self.max_drift = max_drift
        self.target = target
        self._points = deque()

    def add(self, seconds: float, value: float) -> None:
        """Adds a reading, taken at `seconds`."""
        self._points.append((seconds, value))
        # The readings of the last `hold` are kept, and the one before them, so
        # that a stretch in the band can reach a whole `hold`.
        while len(self._points) > 1 and self._points[1][0] <= seconds - self.hold:
            self._points.popleft()

    def clear(self) -> None:
        """Forgets every reading, to start again."""
        self._points.clear()

    @property
    def in_band_for(self) -> float:
        """Seconds from the oldest reading of the latest stretch in the band to
        the newest reading. 0 with one reading, or none."""
        if not self._points:
            return 0.0
        newest = oldest = self._points[-1][0]
        low = high = None
        for seconds, value in reversed(self._points):
            if self.target is not None:
                if not self.in_band(value):
                    break
            else:
                low = value if low is None else min(low, value)
                high = value if high is None else max(high, value)
                if _beyond(high - low, 2 * self.tolerance):
                    break
            oldest = seconds
        return newest - oldest

    @property
    def drift(self) -> float | None:
        """The slope of a line through the readings of the last `hold`, per
        second, or None with fewer than two."""
        return slope(self._points)

    @property
    def drifting_too_fast(self) -> bool:
        """Whether the drift is checked and is above `max_drift`."""
        drift = self.drift
        return bool(self.max_drift) and (drift is None or abs(drift) > self.max_drift)

    def in_band(self, value: float) -> bool:
        """Whether a reading is within `tolerance` of the target. Every reading
        is, with no target."""
        return self.target is None or not _beyond(
            abs(value - self.target), self.tolerance
        )

    @property
    def stable(self) -> bool:
        """Whether the readings have been in the band for a whole `hold`, and
        aren't drifting too fast."""
        return self.in_band_for >= self.hold and not self.drifting_too_fast
