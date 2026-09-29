from pyacquisition.core.instrument import (
    Instrument,
    mark_command,
    mark_query,
)


class Keithley_2400(Instrument):
    """A Keithley 2400 SourceMeter, which sources a voltage and measures the
    current that flows."""

    name = "Keithley 2400"

    @mark_query
    def identify(self) -> str:
        """The make, model, serial number and firmware."""
        return self.query("*IDN?").strip()

    @mark_query
    def get_current(self) -> float:
        """Takes a reading, and answers the current, in amps."""
        # :READ? answers five numbers: volts, amps, ohms, a time and a status
        reading = self.query(":READ?").split(",")
        return float(reading[1])

    @mark_command
    def set_voltage(self, volts: float) -> None:
        """Sets the voltage to source, in volts."""
        self.command(f":SOUR:VOLT {volts}")

    @mark_query
    def get_voltage(self) -> float:
        """The voltage set to source, in volts."""
        return float(self.query(":SOUR:VOLT?"))

    @mark_command
    def set_output(self, on: bool) -> None:
        """Turns the output on, or off."""
        self.command(":OUTP ON" if on else ":OUTP OFF")
