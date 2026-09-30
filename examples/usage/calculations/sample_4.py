import math
from collections import deque

from pyacquisition import Calculation, Experiment, Measurement, RollingMean
from pyacquisition.instruments import SR_830, Clock, Lakeshore_350


class Sample(Experiment):
    """A sample in a cryostat, measured with a lock-in."""

    def setup(self):
        clock = Clock("clock")
        # Your instruments' addresses
        cryostat = Lakeshore_350("cryostat", "GPIB0::12::INSTR")
        lockin = SR_830("lockin", "GPIB0::8::INSTR")
        self.add_instrument(clock)
        self.add_instrument(cryostat)
        self.add_instrument(lockin)

        self.add_measurement(Measurement("time", clock.time, unit="s"))
        self.add_measurement(Measurement("x", lockin.get_x, unit="V"))
        self.add_measurement(Measurement("y", lockin.get_y, unit="V"))
        self.add_measurement(
            Measurement(
                "T",
                cryostat.get_temperature,
                input_channel=Lakeshore_350.InputChannel.INPUT_A,
                unit="K",
            )
        )

        self.add_calculation(RollingMean("x", window=10, unit="V"))
        self.add_calculation(magnitude, units={"r": "V"})
        self.add_calculation(Rate("T", window=20, unit="K/min"))


def magnitude(row):
    """The size of the lock-in's signal, whatever its phase."""
    return {"r": math.hypot(row["x"], row["y"])}


class Rate(Calculation):
    """How fast a column is changing, per minute, over its last few rows."""

    def __init__(self, column, window, unit):
        self.column = column
        self.columns = (f"{column}_rate",)
        self.units = {self.columns[0]: unit}
        self._rows = deque(maxlen=window)

    def __call__(self, row):
        self._rows.append((row["time"], row[self.column]))
        (t0, v0), (t1, v1) = self._rows[0], self._rows[-1]
        rate = (v1 - v0) / (t1 - t0) * 60 if t1 > t0 else math.nan
        return {self.columns[0]: rate}


if __name__ == "__main__":
    Sample().run()
