from furnace import Furnace
from pyacquisition import Experiment, Measurement
from pyacquisition.instruments import Clock


class Hold(Experiment):
    """A furnace, held at a temperature by a PID."""

    def setup(self):
        clock = Clock("clock")
        furnace = Furnace("furnace")
        self.add_instrument(clock)
        self.add_instrument(furnace)

        self.add_measurement(Measurement("time", clock.time, unit="s"))
        self.add_measurement(
            Measurement("temperature", furnace.temperature, unit="°C")
        )


if __name__ == "__main__":
    Hold().run()
