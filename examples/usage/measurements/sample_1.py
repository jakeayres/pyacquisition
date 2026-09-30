from pyacquisition import Experiment, Measurement
from pyacquisition.instruments import Clock
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

        self.add_measurement(Measurement("time", clock.time))
        self.add_measurement(Measurement("x", lockin.get_x))
        self.add_measurement(Measurement("y", lockin.get_y))


if __name__ == "__main__":
    Sample().run()
