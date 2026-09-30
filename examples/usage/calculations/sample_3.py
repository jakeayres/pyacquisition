import math

from pyacquisition import Experiment, Measurement, RollingMean
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


def magnitude(row):
    """The size of the lock-in's signal, whatever its phase."""
    return {"r": math.hypot(row["x"], row["y"])}


if __name__ == "__main__":
    Sample().run()
