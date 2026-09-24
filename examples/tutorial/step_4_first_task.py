import math
from dataclasses import dataclass

from pyacquisition import Experiment, Measurement, Task
from pyacquisition.instruments import Clock
from pyacquisition.instruments.lakeshore.lakeshore_350 import (
    InputChannel,
    OutputChannel,
    State,
)
from simulated import SimulatedCryostat, SimulatedLockin


# --8<-- [start:task]
@dataclass
class SetTemperature(Task):
    """Ramp the cryostat to a temperature, and wait until it gets there."""

    kelvin: float
    ramp_rate: float = 30.0  # kelvin per minute

    @property
    def description(self):
        return f"Go to {self.kelvin} K"

    async def run(self, experiment):
        cryostat = experiment.instruments["lakeshore"]
        cryostat.set_ramp(OutputChannel.OUTPUT_1, State.ON, self.ramp_rate)
        cryostat.set_setpoint(OutputChannel.OUTPUT_1, self.kelvin)
        self.log(f"Ramping to {self.kelvin} K")

        sensor = InputChannel.INPUT_A
        await self.wait_until(
            lambda: abs(cryostat.get_temperature(sensor) - self.kelvin) <= 0.05
        )
        self.log(f"Arrived at {self.kelvin} K")

    async def teardown(self, experiment):
        # However the task ends, stop the ramp where the sample is now.
        cryostat = experiment.instruments["lakeshore"]
        here = cryostat.get_temperature(InputChannel.INPUT_A)
        cryostat.set_setpoint(OutputChannel.OUTPUT_1, here)
        # --8<-- [end:task]


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

        self.register_task(SetTemperature, label="Set Temperature")


if __name__ == "__main__":
    MyExperiment().run()
