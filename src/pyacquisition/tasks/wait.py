from ..core import Task
from ..core.instrument import BaseEnum, resolve_enum_kwargs
from .readings import Readings, Stability, columns, slope
import datetime
from collections import deque
from dataclasses import dataclass
from typing import ClassVar

# How often the time left is reported, in seconds.
REPORT_EVERY = 300
# How often the progress is updated for the interface, in seconds.
TICK = 1.0
# How often the tasks that wait on a measurement look at its new readings, in
# seconds. They arrive once per measurement period.
POLL = 0.5
# How far back `WaitForValue` looks for the rate it is approaching at, in seconds.
RATE_OVER = 60.0


async def _pass(task, seconds, tick):
    """Sleeps for `seconds` of the task's running time, a `TICK` at a time,
    calling `tick(step)` after each one, so the progress can follow."""
    left = seconds
    while left > 0:
        step = min(TICK, left)
        await task.sleep(step)
        left -= step
        tick(step)


@dataclass
class WaitFor(Task):
    """A task that waits for a specified amount of time.

    The time does not pass while the task is paused, so it is the time that the
    task spends running.

    Attributes:
        hours (int): The number of hours to wait. Default is 0.
        minutes (int): The number of minutes to wait. Default is 0.
        seconds (int): The number of seconds to wait. Default is 0.

    Class Attributes:
        name (str): The name of the task.
        help (str): A brief description of the task.
    """

    hours: int = 0
    minutes: int = 0
    seconds: int = 0

    @property
    def description(self) -> str:
        return f"Wait for {self.hours} hours, {self.minutes} minutes, and {self.seconds} seconds."

    async def run(self, experiment):
        total = remaining = self.hours * 3600 + self.minutes * 60 + self.seconds
        self.log(f"Waiting for {remaining} seconds")
        waited = 0.0

        def tick(step):
            nonlocal waited
            waited += step
            self.set_progress(waited / total, remaining=total - waited)

        if total > 0:
            self.set_progress(0, remaining=total)
        while remaining > 0:
            # wait until the next multiple of five minutes is left, and report it
            step = min(remaining, remaining % REPORT_EVERY or REPORT_EVERY)
            await _pass(self, step, tick)
            remaining -= step
            if remaining > 0:
                self.log(f"{datetime.timedelta(seconds=int(remaining))} remaining")


@dataclass
class WaitUntil(Task):
    """Wait until hh:mm (next occurrence)

    The clock keeps running while the task is paused, so it waits until that time
    however long it was paused for.
    """

    hour: int = 0
    minute: int = 0

    @property
    def description(self) -> str:
        return f"Wait until {self.hour}:{self.minute}."

    async def run(self, experiment):
        now = datetime.datetime.now()
        target_time = now.replace(
            hour=self.hour, minute=self.minute, second=0, microsecond=0
        )

        # If the target time is earlier than the current time, move it to the next day
        if target_time <= now:
            target_time += datetime.timedelta(days=1)

        self.log(f"Waiting until {target_time.strftime('%H:%M')}")
        total = (target_time - datetime.datetime.now()).total_seconds()

        def tick(step=0):
            # By the clock, which runs on while the task is paused.
            left = max(0.0, (target_time - datetime.datetime.now()).total_seconds())
            self.set_progress(1 - left / total, remaining=left)

        tick()
        while True:
            remaining = (target_time - datetime.datetime.now()).total_seconds()
            if remaining <= 0:
                break
            await _pass(self, min(remaining, REPORT_EVERY), tick)
            remaining = (target_time - datetime.datetime.now()).total_seconds()
            if remaining > 0:
                self.log(f"{datetime.timedelta(seconds=int(remaining))} remaining")


def _duration(seconds: float) -> str:
    """Seconds as `m:ss`, or `h:mm:ss` from an hour."""
    hours, rest = divmod(round(max(0.0, seconds)), 3600)
    minutes, seconds = divmod(rest, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


def _number(value: float, unit: str = "") -> str:
    """A reading as it is shown, with its unit if it has one."""
    return f"{value:g} {unit}".strip()


def _timeout(minutes: float) -> float | None:
    """A timeout in minutes, as `wait_until` takes it: seconds, or None for none."""
    return minutes * 60 if minutes else None


class Condition(BaseEnum):
    """Which side of the threshold `WaitForValue` waits for the reading to be."""

    BELOW = ("below", "Below")
    ABOVE = ("above", "Above")


class _WaitOnReadings(Task):
    """What the tasks that wait on a measurement share: the readings they follow,
    which a resume starts again, a timeout that fails the task unless
    `continue_on_timeout` is set, and a note for paused measurements."""

    input_choices: ClassVar[dict] = {"measurement": columns}

    def _check_timeout(self) -> None:
        if self.timeout < 0:
            raise ValueError("timeout must not be negative.")

    async def setup(self, experiment=None):
        self._readings = None
        self._restart()

    def _restart(self) -> None:
        """Forgets what has been seen, to start watching again."""
        self._latest = None  # the newest reading, (seconds, value)

    def on_resume(self, experiment=None):
        # Readings weren't looked at while it was paused, so no one can say what
        # the measurement did: it starts watching again.
        if self._readings is not None:
            self._readings.clear()
        self._restart()

    def _waiting_note(self, experiment) -> str | None:
        """A note for when no reading has come in, or None if one has."""
        if experiment._rack.paused:
            return "Measurements are paused"
        if self._latest is None:
            return f"Waiting for a reading of {self.measurement}"
        return None

    @property
    def goal(self) -> str:
        """What it waits for, such as "T is below 2"."""
        raise NotImplementedError

    @property
    def description(self) -> str:
        return f"Wait until {self.goal}"

    async def _wait(self, experiment, done) -> None:
        """Follows the measurement until `done()`, for at most `timeout` minutes."""
        with Readings(experiment, self.measurement) as readings:
            self._readings = readings
            self.log(f"Waiting until {self.goal}")
            try:
                await self.wait_until(
                    done, poll=POLL, timeout=_timeout(self.timeout), what=self.goal
                )
            except TimeoutError:
                latest = "no reading came in"
                if self._latest is not None:
                    latest = f"it is {_number(self._latest[1], readings.unit)}"
                message = (
                    f"Gave up after {self.timeout:g} min waiting until {self.goal}: "
                    f"{latest}."
                )
                if not self.continue_on_timeout:
                    raise TimeoutError(message) from None
                self.log(f"{message} Carrying on.", "warning")


@dataclass
class WaitForValue(_WaitOnReadings):
    """Wait until a measurement passes a value

    It looks at each new reading of the measurement as the rows arrive, so once
    per measurement period. If the reading is past the threshold already, it
    finishes at once. If the time runs out, the task fails, which pauses the
    queue, unless `continue_on_timeout` is set.

    Attributes:
        measurement (str): The column to watch: a measurement, or a
            calculation's column. The form lists a calculation's columns when
            it names them, by its `columns` or its `units`.
        condition (Condition): Whether to wait for the reading to be `BELOW` or
            `ABOVE` the threshold.
        threshold (float): The value to pass, in the measurement's units.
        hold (float): How many seconds the reading must stay past the
            threshold, so that one noisy reading doesn't end the wait. 0 ends it
            at the first.
        timeout (float): How many minutes to wait before giving up. 0 waits as
            long as it takes.
        continue_on_timeout (bool): When the time runs out, log a warning and
            carry on with the queue, instead of failing, which pauses it.

    Example:
        ```python
        await self.run_subtask(WaitForValue("T", "BELOW", 2.0, timeout=120))
        ```
    """

    measurement: str
    condition: Condition
    threshold: float
    hold: float = 0.0
    timeout: float = 0.0
    continue_on_timeout: bool = False

    def __post_init__(self):
        super().__post_init__()
        self.condition = resolve_enum_kwargs(
            WaitForValue, {"condition": self.condition}
        )["condition"]
        if not isinstance(self.condition, Condition):
            raise ValueError("condition must be BELOW or ABOVE.")
        if self.hold < 0:
            raise ValueError("hold must not be negative.")
        self._check_timeout()

    @property
    def goal(self) -> str:
        return f"{self.measurement} is {self.condition.label.lower()} {self.threshold:g}"

    def _restart(self) -> None:
        super()._restart()
        self._first = None  # the first value seen, where the progress starts
        self._past_since = None  # when the readings went past the threshold
        self._recent = deque()  # the readings of the last minute, for the rate

    def _past(self, value: float) -> bool:
        if self.condition is Condition.BELOW:
            return value < self.threshold
        return value > self.threshold

    def _passed(self, experiment) -> bool:
        """Takes the new readings, says how far along it is, and returns whether
        the reading has been past the threshold for `hold`."""
        for seconds, value in self._readings.new():
            self._latest = (seconds, value)
            if self._first is None:
                self._first = value
            if not self._past(value):
                self._past_since = None
            elif self._past_since is None:
                self._past_since = seconds
            self._recent.append((seconds, value))
            while self._recent[0][0] < seconds - RATE_OVER:
                self._recent.popleft()

        note = self._waiting_note(experiment)
        if self._latest is None:
            self.set_progress(0, note=note)
            return False
        now, value = self._latest
        unit = self._readings.unit
        if self._past_since is not None:
            held = now - self._past_since
            if held >= self.hold:
                self.set_progress(1, note=f"{self.measurement} is {_number(value, unit)}")
                return True
            self.set_progress(
                1,
                remaining=self.hold - held,
                note=note or f"Past {_number(self.threshold, unit)} for {held:.0f} of {self.hold:g} s",
            )
            return False

        span = self.threshold - self._first
        fraction = (value - self._first) / span if span else 0.0
        rate = slope(self._recent)
        remaining = None
        if rate:
            remaining = (self.threshold - value) / rate
            remaining = remaining + self.hold if remaining > 0 else None
        to_go = f"{abs(self.threshold - value):.3g} {unit}".strip()
        self.set_progress(
            max(0.0, min(1.0, fraction)), remaining=remaining, note=note or f"{to_go} to go"
        )
        return False

    async def run(self, experiment):
        await self._wait(experiment, lambda: self._passed(experiment))


@dataclass
class WaitForStable(_WaitOnReadings):
    """Wait until a measurement is stable

    It looks at each new reading of the measurement as the rows arrive, so once
    per measurement period. The measurement is stable when, for the last `hold`
    minutes, every reading has been within `tolerance` of `target` (or, with no
    target, has fitted in a band twice `tolerance` wide, wherever it sits), and
    a straight line through those readings rises or falls by no more than
    `max_drift` a minute.

    A reading outside the band starts the time again from the next one. A
    failed reading is skipped. Pausing the task starts the time again when it
    resumes. If the time runs out, the task fails, which pauses the queue,
    unless `continue_on_timeout` is set.

    Attributes:
        measurement (str): The column to watch: a measurement, or a
            calculation's column. The form lists a calculation's columns when
            it names them, by its `columns` or its `units`.
        tolerance (float): How far a reading may be from the target, or from the
            middle of the band, in the measurement's units.
        hold (float): How many minutes the readings must stay in the band.
        max_drift (float): How fast the readings may rise or fall, in the
            measurement's units per minute. 0 doesn't check it.
        target (float | None): The value to be stable at, such as a setpoint.
            Left out, the readings may settle anywhere.
        timeout (float): How many minutes to wait before giving up. 0 waits as
            long as it takes.
        continue_on_timeout (bool): When the time runs out, log a warning and
            carry on with the queue, instead of failing, which pauses it.

    Example:
        ```python
        await self.run_subtask(RampTemperature("lakeshore", "OUTPUT_1", 10, 2))
        await self.run_subtask(
            WaitForStable("T", tolerance=0.005, hold=5, max_drift=0.001, target=10)
        )
        ```
    """

    measurement: str
    tolerance: float
    hold: float
    max_drift: float = 0.0
    target: float | None = None
    timeout: float = 0.0
    continue_on_timeout: bool = False

    def __post_init__(self):
        super().__post_init__()
        # It checks tolerance, hold and max_drift.
        self._check = Stability(
            self.tolerance, self.hold * 60, self.max_drift / 60, self.target
        )
        self._check_timeout()

    @property
    def goal(self) -> str:
        band = f"±{self.tolerance:g}"
        if self.target is not None:
            band = f"{self.tolerance:g} of {self.target:g}"
        return f"{self.measurement} is stable within {band} for {self.hold:g} min"

    def _restart(self) -> None:
        super()._restart()
        self._check.clear()

    def _settled(self, experiment) -> bool:
        """Takes the new readings, says how far along it is, and returns whether
        the measurement is stable."""
        check = self._check
        for seconds, value in self._readings.new():
            self._latest = (seconds, value)
            check.add(seconds, value)

        note = self._waiting_note(experiment)
        if self._latest is None:
            self.set_progress(0, note=note)
            return False
        value = self._latest[1]
        unit = self._readings.unit
        per_minute = f" {unit}/min" if unit else " a minute"
        drift = check.drift
        drifting = "" if drift is None else f", drifting {drift * 60:.2g}{per_minute}"
        if check.stable:
            self.set_progress(1, note=f"Stable at {_number(value, unit)}{drifting}")
            return True

        hold = check.hold
        in_band = min(check.in_band_for, hold)
        if note is None and not check.in_band(value):
            note = (
                f"{self.measurement} is {_number(value, unit)}, outside "
                f"{self.target:g} ± {_number(self.tolerance, unit)}"
            )
        if note is None and in_band >= hold:  # long enough, but drifting
            note = (
                f"In the band for {_duration(hold)}{drifting}, faster than "
                f"{self.max_drift:g}{per_minute}"
            )
            self.set_progress(1, note=note)
            return False
        self.set_progress(
            in_band / hold,
            remaining=hold - in_band,
            note=note
            or f"In the band for {_duration(in_band)} of {_duration(hold)}{drifting}",
        )
        return False

    async def run(self, experiment):
        await self._wait(experiment, lambda: self._settled(experiment))
