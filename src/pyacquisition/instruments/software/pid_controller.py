from typing import TYPE_CHECKING

from ...core.instrument import SoftwareInstrument, mark_command, mark_query

if TYPE_CHECKING:
    from ...tasks.pid import PID


class PIDController(SoftwareInstrument):
    """The controls of a running `PID` task, as an instrument: its setpoint, gains,
    output limits, period and setpoint ramp, to change from the **Instruments** tab
    while it runs, and its live values, to read or record as measurements.

    A PID is made in code, so its controller is too. Each change takes effect on the
    PID's next cycle. Pausing, resuming and aborting it are the **Queue** tab's.

    Args:
        uid (str): The id of the instrument, as the interface shows it.
        pid (PID): The PID task it controls.

    Example:
        ```python
        pid = PID(read=resistance, write=heater, setpoint=1650.0, kp=1.0, ki=0.2)
        self.add_task_manager("control").add_task(pid)
        controller = PIDController("pid", pid)
        self.add_instrument(controller)
        self.add_measurement(Measurement("output", controller.get_output))
        ```
    """

    name = "PID Controller"

    def __init__(self, uid: str, pid: "PID"):
        super().__init__(uid)
        self._pid = pid

    # ------------------------------------------------------------ the setpoint
    @mark_query
    def get_setpoint(self) -> float:
        """The setpoint the PID holds.

        Returns:
            float: The setpoint, in the measured value's units.
        """
        return self._pid.setpoint

    @mark_command
    def set_setpoint(self, setpoint: float) -> None:
        """Sets the setpoint the PID holds. With a ramp rate, the PID ramps to it.

        Args:
            setpoint (float): The setpoint, in the measured value's units.
        """
        self._pid.setpoint = float(setpoint)

    @mark_query
    def get_ramped_setpoint(self) -> float:
        """The setpoint the PID's loop is using now: on its way to the setpoint at
        the ramp rate, or the setpoint itself with no ramp.

        Returns:
            float: The setpoint in use, or `nan` before the PID's first cycle.
        """
        return self._pid.ramped_setpoint

    @mark_query
    def get_ramp_rate(self) -> float:
        """How fast the setpoint in use moves to a new setpoint.

        Returns:
            float: The rate, in the setpoint's units per minute. 0 is no ramp.
        """
        return self._pid.ramp_rate

    @mark_command
    def set_ramp_rate(self, rate: float) -> None:
        """Sets how fast the setpoint in use moves to a new setpoint.

        Args:
            rate (float): The rate, in the setpoint's units per minute. 0 takes a
                new setpoint at once.

        Raises:
            ValueError: If the rate is negative.
        """
        if rate < 0:
            raise ValueError(f"The ramp rate must not be negative: {rate}")
        self._pid.ramp_rate = float(rate)

    # --------------------------------------------------------------- the gains
    @mark_query
    def get_p(self) -> float:
        """The proportional gain.

        Returns:
            float: The gain, in output per unit of error.
        """
        return self._pid.kp

    @mark_command
    def set_p(self, p: float) -> None:
        """Sets the proportional gain.

        Args:
            p (float): The gain, in output per unit of error.

        Raises:
            ValueError: If the gain is negative. For an output that lowers the
                value, the PID is `inverted`, and its gains stay positive.
        """
        self._pid.kp = _gain("p", p)

    @mark_query
    def get_i(self) -> float:
        """The integral gain.

        Returns:
            float: The gain, in output per (unit of error x second).
        """
        return self._pid.ki

    @mark_command
    def set_i(self, i: float) -> None:
        """Sets the integral gain.

        Args:
            i (float): The gain, in output per (unit of error x second).

        Raises:
            ValueError: If the gain is negative.
        """
        self._pid.ki = _gain("i", i)

    @mark_query
    def get_d(self) -> float:
        """The derivative gain.

        Returns:
            float: The gain, in output per (unit of error / second).
        """
        return self._pid.kd

    @mark_command
    def set_d(self, d: float) -> None:
        """Sets the derivative gain.

        Args:
            d (float): The gain, in output per (unit of error / second).

        Raises:
            ValueError: If the gain is negative.
        """
        self._pid.kd = _gain("d", d)

    @mark_query
    def get_pid(self) -> dict:
        """The three gains.

        Returns:
            dict: `p`, `i` and `d`.
        """
        return {"p": self.get_p(), "i": self.get_i(), "d": self.get_d()}

    @mark_command
    def set_pid(self, p: float, i: float, d: float) -> None:
        """Sets the three gains, with `set_p`, `set_i` and `set_d`. None is changed
        if any is refused.

        Args:
            p (float): The proportional gain.
            i (float): The integral gain.
            d (float): The derivative gain.

        Raises:
            ValueError: If a gain is negative.
        """
        for name, gain in (("p", p), ("i", i), ("d", d)):
            _gain(name, gain)
        self.set_p(p)
        self.set_i(i)
        self.set_d(d)

    # ------------------------------------------------------ the output and period
    @mark_query
    def get_output_limits(self) -> dict:
        """The limits the output is kept within.

        Returns:
            dict: `output_min` and `output_max`, each None for no limit.
        """
        return {"output_min": self._pid.output_min, "output_max": self._pid.output_max}

    @mark_command
    def set_output_limits(self, output_min: float, output_max: float) -> None:
        """Sets the limits the output is kept within.

        Args:
            output_min (float): The lowest output.
            output_max (float): The highest output.

        Raises:
            ValueError: If `output_min` is above `output_max`.
        """
        if output_min > output_max:
            raise ValueError(
                f"output_min, {output_min}, must not be above output_max, {output_max}"
            )
        self._pid.output_min = float(output_min)
        self._pid.output_max = float(output_max)

    @mark_query
    def get_period(self) -> float:
        """The time between the PID's cycles.

        Returns:
            float: The period, in seconds.
        """
        return self._pid.period

    @mark_command
    def set_period(self, seconds: float) -> None:
        """Sets the time between the PID's cycles.

        Args:
            seconds (float): The period, in seconds.

        Raises:
            ValueError: If the period isn't positive.
        """
        if not seconds > 0:
            raise ValueError(f"The period must be positive: {seconds}")
        self._pid.period = float(seconds)

    # -------------------------------------------------------------- live values
    @mark_query
    def get_value(self) -> float:
        """The measured value the PID last read.

        Returns:
            float: The value, or `nan` before its first cycle.
        """
        return self._pid.process_value

    @mark_query
    def get_output(self) -> float:
        """The output the PID last wrote.

        Returns:
            float: The output.
        """
        return self._pid.output

    @mark_query
    def get_error(self) -> float:
        """The PID's last error: the setpoint in use minus the measured value (the
        other way round if it is `inverted`).

        Returns:
            float: The error.
        """
        return self._pid.error


def _gain(name: str, gain: float) -> float:
    """A gain, refused if it is negative."""
    if gain < 0:
        raise ValueError(
            f"{name} must not be negative: {gain}. For an output that lowers the "
            "value, the PID is inverted, and its gains stay positive."
        )
    return float(gain)
