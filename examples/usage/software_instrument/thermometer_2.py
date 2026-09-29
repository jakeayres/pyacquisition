from pyacquisition.core.instrument import SoftwareInstrument, mark_query


class Thermometer(SoftwareInstrument):
    """A thermometer, simulated, whose temperature follows a setpoint."""

    name = "Thermometer"

    def __init__(self, uid):
        super().__init__(uid)
        self._kelvin = 300.0

    @mark_query
    def get_temperature(self) -> float:
        """The temperature, in kelvin."""
        return self._kelvin
