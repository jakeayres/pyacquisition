import math

from pyacquisition import Experiment, Measurement
from pyacquisition.instruments import Clock
from pyacquisition.instruments.lakeshore.lakeshore_350 import InputChannel
from simulated import SimulatedCryostat, SimulatedLockin


class MyExperiment(Experiment):
    data_path = "my_data"
    gui_log_level = "INFO"

    def setup(self):
        clock = Clock("clock")
        self.add_instrument(clock)

        cryostat = SimulatedCryostat("lakeshore")
        self.add_instrument(cryostat)

        lockin = SimulatedLockin("lockin", cryostat)
        self.add_instrument(lockin)

        self.add_measurement(Measurement("time", clock.time))
        self.add_measurement(
            Measurement(
                "T",
                cryostat.get_temperature,
                input_channel=InputChannel.INPUT_A,
            )
        )
        self.add_measurement(Measurement("x", lockin.get_x))
        self.add_measurement(Measurement("y", lockin.get_y))

        self.add_calculation(lambda row: {"R": math.hypot(row["x"], row["y"])})


if __name__ == "__main__":
    MyExperiment().run()
