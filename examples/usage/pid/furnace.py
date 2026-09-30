"""A simulated furnace, for Hold a temperature with PID: a heater's power in, and
a thermocouple's temperature out, with nothing to control it. At full power it
settles at 100 degrees C, and it takes about 20 s to respond."""

import time

from pyacquisition.core.instrument import (
    SoftwareInstrument,
    mark_command,
    mark_query,
)


class Furnace(SoftwareInstrument):
    """A simulated furnace: a heater's power in, the temperature out."""

    name = "Furnace"

    def __init__(self, uid):
        super().__init__(uid)
        self._temperature = 20.0
        self._power = 0.0
        self._last = time.monotonic()

    def _advance(self):
        now = time.monotonic()
        dt, self._last = now - self._last, now
        target = 20.0 + 0.8 * self._power  # 100 % settles at 100 degrees
        self._temperature += dt * (target - self._temperature) / 20.0

    @mark_query
    def temperature(self) -> float:
        """The furnace's temperature, in degrees C."""
        self._advance()
        return self._temperature

    @mark_command
    def set_power(self, percent: float) -> float:
        """Sets the heater's power, in percent."""
        self._advance()
        self._power = percent
        return percent
