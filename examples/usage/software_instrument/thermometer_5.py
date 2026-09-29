from pyacquisition.core.instrument import (
    BaseEnum,
    SoftwareInstrument,
    mark_command,
    mark_query,
)


class Sensor(BaseEnum):
    """Where the temperature is read."""

    SAMPLE = ("A", "Sample")
    STAGE = ("B", "Stage")


class Thermometer(SoftwareInstrument):
    """A thermometer, simulated, whose temperature follows a setpoint."""

    name = "Thermometer"

    def __init__(self, uid):
        super().__init__(uid)
        self._kelvin = 300.0
        self._setpoint = 300.0

    @mark_query
    def get_temperature(self, sensor: Sensor = Sensor.SAMPLE) -> float:
        """The temperature at a sensor, in kelvin."""
        if sensor is Sensor.STAGE:
            return self._setpoint
        self._kelvin += 0.05 * (self._setpoint - self._kelvin)
        return self._kelvin

    @mark_command
    def set_setpoint(self, kelvin: float) -> None:
        """Sets the temperature to go to, in kelvin."""
        self._setpoint = kelvin
