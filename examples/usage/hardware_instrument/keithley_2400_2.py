from pyacquisition.core.instrument import Instrument, mark_query


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
