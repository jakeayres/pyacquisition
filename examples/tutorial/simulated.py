"""A simulated rig for the tutorial.

`SimulatedCryostat` and `SimulatedLockin` have the same queries and commands
as a Lakeshore 350 temperature controller and an SR 830 lock-in amplifier, so
that the tutorial can be followed without any hardware, and so that swapping
in the real instruments later changes nothing else in your experiment.

You do not need to read this file to follow the tutorial.
"""

import math
import random
import time

from pyacquisition.core.instrument import (
    SoftwareInstrument,
    mark_command,
    mark_query,
)
from pyacquisition.instruments.lakeshore.lakeshore_350 import (
    InputChannel,
    OutputChannel,
    State,
)


class SimulatedCryostat(SoftwareInstrument):
    """A simulated temperature controller, like a Lakeshore 350."""

    name = "Simulated Cryostat"

    def __init__(self, uid, temperature=20.0, lag=3.0):
        super().__init__(uid)
        self._lag = lag  # seconds the sample takes to follow the setpoint
        self._temperature = temperature  # what the thermometer reads
        self._setpoint = temperature  # the setpoint the controller is at now
        self._target = temperature  # the setpoint it is heading for
        self._ramp_on = False
        self._ramp_rate = 0.0  # kelvin per minute
        self._last = time.monotonic()

    def _advance(self):
        """Bring the simulation up to date. Each query and command calls it."""
        now = time.monotonic()
        dt, self._last = now - self._last, now
        if self._ramp_on and self._ramp_rate > 0:
            step = self._ramp_rate / 60.0 * dt
            self._setpoint += max(
                -step, min(step, self._target - self._setpoint)
            )
        else:
            self._setpoint = self._target
        # The sample follows the setpoint, a little behind it.
        self._temperature += (self._setpoint - self._temperature) * (
            1.0 - math.exp(-dt / self._lag)
        )

    @mark_query
    def get_temperature(self, input_channel: InputChannel) -> float:
        """Read the temperature of an input, in kelvin."""
        self._advance()
        return self._temperature + random.gauss(0.0, 0.003)

    @mark_command
    def set_ramp(
        self, output_channel: OutputChannel, state: State, rate: float
    ) -> int:
        """Turn the ramp on or off, and set its rate in kelvin per minute."""
        self._advance()
        self._ramp_on = state == State.ON
        self._ramp_rate = rate
        return 0

    @mark_query
    def get_ramp(self, output_channel: OutputChannel) -> float:
        """Read the ramp rate, in kelvin per minute."""
        return self._ramp_rate

    @mark_command
    def set_setpoint(
        self, output_channel: OutputChannel, setpoint: float
    ) -> int:
        """Set the temperature to head for, in kelvin."""
        self._advance()
        self._target = setpoint
        return 0

    @mark_query
    def get_setpoint(self, output_channel: OutputChannel) -> float:
        """Read the setpoint (K). While ramping, it is the value so far."""
        self._advance()
        return self._setpoint


class SimulatedLockin(SoftwareInstrument):
    """A simulated lock-in amplifier, like an SR 830, measuring a sample.

    The sample's signal falls away as it warms through 14 K.
    """

    name = "Simulated Lock-in"

    def __init__(self, uid, cryostat, transition=14.0, width=1.1):
        super().__init__(uid)
        self._cryostat = cryostat
        self._transition = transition
        self._width = width
        self._frequency = 17.0
        self._amplitude = 1.0

    def _kelvin(self):
        return self._cryostat.get_temperature(InputChannel.INPUT_A)

    @mark_query
    def get_x(self) -> float:
        """Read the in-phase component, in volts."""
        t = self._kelvin()
        signal = (
            2.4e-3
            * self._amplitude
            / (1.0 + math.exp((t - self._transition) / self._width))
        )
        return signal + random.gauss(0.0, 7e-6)

    @mark_query
    def get_y(self) -> float:
        """Read the quadrature component, in volts."""
        t = self._kelvin()
        signal = (
            0.55e-3
            * self._amplitude
            * math.exp(-(((t - self._transition) / 2.3) ** 2))
        )
        return signal + random.gauss(0.0, 9e-6)

    @mark_query
    def get_frequency(self) -> float:
        """Read the reference frequency, in hertz."""
        return self._frequency

    @mark_command
    def set_frequency(self, frequency: float) -> int:
        """Set the reference frequency, in hertz."""
        self._frequency = frequency
        return 0

    @mark_query
    def get_reference_amplitude(self) -> float:
        """Read the amplitude of the excitation, in volts."""
        return self._amplitude

    @mark_command
    def set_reference_amplitude(self, amplitude: float) -> int:
        """Set the excitation amplitude, in volts. The signal scales with it."""
        self._amplitude = amplitude
        return 0
