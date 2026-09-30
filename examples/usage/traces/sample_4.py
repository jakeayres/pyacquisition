from pyacquisition import Experiment, Measurement, Trace
from pyacquisition.instruments import Clock
from pyacquisition.instruments.lakeshore.lakeshore_350 import InputChannel
from simulated import (
    SimulatedCryostat,
    SimulatedLockin,
    SimulatedSpectrometer,
)


class Sample(Experiment):
    """A sample in a cryostat, measured with a lock-in."""

    def setup(self):
        clock = Clock("clock")
        cryostat = SimulatedCryostat("cryostat")
        lockin = SimulatedLockin("lockin", cryostat)
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
                input_channel=InputChannel.INPUT_A,
                unit="K",
            )
        )

        spectrometer = SimulatedSpectrometer("spectrometer", cryostat)
        self.add_instrument(spectrometer)
        self.add_trace(
            Trace(
                "spectrum",
                spectrometer.get_spectrum,
                reduce=["peak_x"],
                every_rows=1,
            )
        )


if __name__ == "__main__":
    Sample().run()
