from pyacquisition.core.instrument import Instrument, mark_query


class Keithley_2400(Instrument):
    """A Keithley 2400 SourceMeter, which sources a voltage and measures the
    current that flows."""

    name = "Keithley 2400"

    @mark_query
    def identify(self) -> str:
        """The make, model, serial number and firmware."""
        return self.query("*IDN?").strip()
