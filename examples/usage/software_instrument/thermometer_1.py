from pyacquisition.core.instrument import SoftwareInstrument


class Thermometer(SoftwareInstrument):
    """A thermometer, simulated, whose temperature follows a setpoint."""

    name = "Thermometer"
