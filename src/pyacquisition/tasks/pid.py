from ..core import Task
from ..core.logging import logger
import asyncio
import math
import time
from collections.abc import Callable
from dataclasses import dataclass


class PIDController:
    """
    A PID controller. It is a plain calculation: give it the setpoint, the
    measured value and the time since the last call, and it returns the output.
    Use `PID` to run one as a task.

    The output is `kp * error + integral + derivative`, where the error is the
    setpoint minus the measured value.

    - The integral is kept in units of the output, so changing `ki` while running
      does not make the output jump.
    - The derivative acts on the measured value, not on the error, so changing the
      setpoint does not kick the output.
    - The integral stops growing while the output is at a limit and the error would
      push it further (anti-windup), so the output comes off the limit as soon as
      the error changes sign.

    Attributes:
        kp (float): The proportional gain.
        ki (float): The integral gain, in output per (error x second).
        kd (float): The derivative gain, in output per (error / second).
        output_min (float | None): The lowest output, or `None` for no limit.
        output_max (float | None): The highest output, or `None` for no limit.
        derivative_filter (float): The time constant in seconds of a low-pass filter
            on the derivative. 0 does not filter, which amplifies noise.
        inverted (bool): False if raising the output raises the measured value (a
            heater). True if it lowers it (a cooler).
        max_dt (float | None): The most time in seconds that the integral counts for
            in one update, so a long gap (a pause, say) does not add a huge step.
        output (float): The last output.
        error (float): The last error.
        p_term (float), i_term (float), d_term (float): The parts of the last
            output, before it was limited.
    """

    def __init__(
        self,
        kp: float = 1.0,
        ki: float = 0.0,
        kd: float = 0.0,
        output_min: float | None = None,
        output_max: float | None = None,
        derivative_filter: float = 0.0,
        inverted: bool = False,
        max_dt: float | None = None,
    ) -> None:
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.output_min = output_min
        self.output_max = output_max
        self.derivative_filter = derivative_filter
        self.inverted = inverted
        self.max_dt = max_dt
        self.reset()

    def reset(self, output: float | None = None) -> None:
        """
        Starts again, forgetting everything that was built up.

        Args:
            output (float | None): Start from this output. The first update then
                returns it, and later updates carry on smoothly from it. Use it to
                take over from an output that is already applied. By default there
                is no such start, and the first output is `kp * error`.
        """
        self._start_output = output
        self._started = False
        self._integral = 0.0
        self._derivative = 0.0
        self._last_process_value = None
        self.output = 0.0 if output is None else output
        self.error = 0.0
        self.p_term = self.i_term = self.d_term = 0.0

    def update(self, setpoint: float, process_value: float, dt: float) -> float:
        """
        Calculates the next output.

        Args:
            setpoint (float): The value to hold.
            process_value (float): The measured value.
            dt (float): The time in seconds since the last update. It is not used
                by the first update.

        Returns:
            float: The output.

        Raises:
            ValueError: If the setpoint or the measured value is not a finite number.
        """
        if not math.isfinite(setpoint):
            raise ValueError(f"The setpoint is not a number: {setpoint}")
        if not math.isfinite(process_value):
            raise ValueError(f"The measured value is not a number: {process_value}")

        low = -math.inf if self.output_min is None else self.output_min
        high = math.inf if self.output_max is None else self.output_max
        sign = -1.0 if self.inverted else 1.0

        error = sign * (setpoint - process_value)
        p = self.kp * error

        if not self._started:
            self._started = True
            self._derivative = 0.0
            if self._start_output is None:
                self._integral = 0.0
            else:
                start = min(max(self._start_output, low), high)
                self._integral = start - p
            d = 0.0
        else:
            if not dt > 0:
                return self.output  # no time has passed, so there is nothing to do

            # The derivative of the error, with the setpoint held fixed.
            rate = -sign * (process_value - self._last_process_value) / dt
            alpha = dt / (self.derivative_filter + dt)
            self._derivative += alpha * (rate - self._derivative)
            d = self.kd * self._derivative

            integral_dt = dt if self.max_dt is None else min(dt, self.max_dt)
            candidate = self._integral + self.ki * error * integral_dt
            # Anti-windup: the integral may take the output up to a limit, but no
            # further. It can always move back the other way.
            if p + candidate + d > high:
                candidate = min(candidate, max(self._integral, high - p - d))
            elif p + candidate + d < low:
                candidate = max(candidate, min(self._integral, low - p - d))
            self._integral = candidate

        self._last_process_value = process_value
        self.output = min(max(p + self._integral + d, low), high)
        self.error = error
        self.p_term, self.i_term, self.d_term = p, self._integral, d
        return self.output


@dataclass
class PID(Task):
    """Hold a value at a setpoint with a PID controller.

    Every `period` seconds it reads the measured value, works out the output and
    writes it. It runs until it is stopped (or for `duration` seconds), and then
    writes `final_output`, so the output is left in a safe state however it ends.

    Its inputs are functions, so create it in your own code (it cannot be queued
    from the interface). The settings `setpoint`, `kp`, `ki`, `kd`, `output_min`,
    `output_max`, `period` and `derivative_filter` are read on every cycle, so
    change them while it runs by assigning to them.

    Run it on its own task manager to have it run for the whole experiment, or
    with `alongside()` to run it while something else happens. See the PID page.

    Attributes:
        read (Callable[[], float]): Returns the measured value, for example
            `thermometer.get_temperature`.
        write (Callable[[float], object]): Applies an output, for example
            `heater.set_power`.
        setpoint (float): The value to hold.
        kp (float): The proportional gain.
        ki (float): The integral gain, in output per (error x second).
        kd (float): The derivative gain, in output per (error / second).
        output_min (float | None): The lowest output, or `None` for no limit.
        output_max (float | None): The highest output, or `None` for no limit.
        period (float): The time in seconds between cycles.
        derivative_filter (float): The time constant in seconds of a low-pass filter
            on the derivative. 0 does not filter.
        inverted (bool): False if raising the output raises the measured value (a
            heater). True if it lowers it (a cooler).
        initial_output (float | None): The output that is already applied when the
            PID starts, so that it takes over smoothly. By default it starts from
            `kp * error`.
        final_output (float): Written when the PID ends, however it ends.
        duration (float): Stop after this many seconds. 0 runs until stopped.
        max_failures (int): Stop with an error after this many cycles in a row in
            which reading or writing failed. Until then, a failed cycle is logged
            and the output stays as it was.
        label (str): The name shown in the log. Give each PID its own.
        time_source (Callable[[], float]): Returns the time in seconds. Defaults to
            `time.monotonic`.
    """

    read: Callable[[], float]
    write: Callable[[float], object]
    setpoint: float
    kp: float = 1.0
    ki: float = 0.0
    kd: float = 0.0
    output_min: float | None = None
    output_max: float | None = None
    period: float = 1.0
    derivative_filter: float = 0.0
    inverted: bool = False
    initial_output: float | None = None
    final_output: float = 0.0
    duration: float = 0.0
    max_failures: int = 5
    label: str = "PID"
    time_source: Callable[[], float] = time.monotonic

    def __post_init__(self):
        super().__post_init__()
        if not callable(self.read) or not callable(self.write):
            raise TypeError("read and write must be functions.")
        if self.period <= 0:
            raise ValueError("period must be positive.")
        if self.duration < 0:
            raise ValueError("duration must not be negative.")
        if self.max_failures < 1:
            raise ValueError("max_failures must be at least 1.")
        if (
            self.output_min is not None
            and self.output_max is not None
            and self.output_min > self.output_max
        ):
            raise ValueError("output_min must not be above output_max.")

        self._controller = PIDController(inverted=self.inverted)
        self._process_value = math.nan
        self._failures = 0

    @property
    def name(self) -> str:
        return self.label

    @property
    def description(self) -> str:
        return f"Hold {self.setpoint} with a PID controller"

    @property
    def parameters(self) -> dict:
        """The settings, and the live values once it has read the measured value."""
        parameters = {
            "setpoint": self.setpoint,
            "kp": self.kp,
            "ki": self.ki,
            "kd": self.kd,
        }
        if math.isfinite(self._process_value):
            parameters["value"] = self._process_value
            parameters["output"] = self.output
            parameters["error"] = self.error
        return parameters

    @property
    def output(self) -> float:
        """The last output that was calculated."""
        return self._controller.output

    @property
    def process_value(self) -> float:
        """The last measured value, or `nan` if none has been read."""
        return self._process_value

    @property
    def error(self) -> float:
        """The last error: the setpoint minus the measured value."""
        return self._controller.error

    def _apply_settings(self) -> None:
        """Passes the settings, which may have changed, to the controller."""
        controller = self._controller
        controller.kp = self.kp
        controller.ki = self.ki
        controller.kd = self.kd
        controller.output_min = self.output_min
        controller.output_max = self.output_max
        controller.derivative_filter = self.derivative_filter
        controller.max_dt = 5 * self.period

    async def setup(self, experiment=None):
        self._controller.reset(self.initial_output)
        self._process_value = math.nan
        self._failures = 0

    async def run(self, experiment=None):
        started = next_cycle = last = self.time_source()
        yield f"Holding {self.setpoint} (period {self.period} s)"

        while True:
            now = self.time_source()
            if self.duration and now - started >= self.duration:
                break

            self._apply_settings()
            try:
                self._process_value = float(self.read())
                output = self._controller.update(
                    self.setpoint, self._process_value, now - last
                )
                self.write(output)
                self._failures = 0
            except Exception as e:
                self._failures += 1
                logger.warning(
                    f"[{self.name}] Cycle failed ({self._failures} of "
                    f"{self.max_failures}), output left as it was: {e}"
                )
                if self._failures >= self.max_failures:
                    raise RuntimeError(
                        f"[{self.name}] Stopped after {self._failures} failed "
                        f"cycles in a row. The last error: {e}"
                    ) from e
            last = now

            yield None

            # Keep to the schedule, and do not try to catch up if we fell behind.
            next_cycle = max(next_cycle + self.period, self.time_source())
            await asyncio.sleep(max(0.0, next_cycle - self.time_source()))

    async def teardown(self, experiment=None):
        try:
            self.write(self.final_output)
            logger.info(f"[{self.name}] Output set to {self.final_output}")
        except Exception as e:
            logger.error(
                f"[{self.name}] Could not set the final output {self.final_output}: {e}"
            )
