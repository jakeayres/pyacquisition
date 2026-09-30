from pyacquisition import Experiment, Measurement
from pyacquisition.instruments import Clock
from pyacquisition.instruments.lakeshore.lakeshore_350 import InputChannel
from simulated import SimulatedCryostat, SimulatedLockin


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


if __name__ == "__main__":
    Sample().run()
