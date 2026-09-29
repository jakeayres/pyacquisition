"""The rig the browser tests run: a simulated cryostat and lock-in (from
examples/simulated_rig/simulated.py), and tasks that set the temperature, record at one,
and sweep it. It was lesson 5 of the tutorial."""

import math
from dataclasses import dataclass

from pyacquisition import Experiment, Measurement, Task
from pyacquisition.instruments import Clock
from pyacquisition.instruments.lakeshore.lakeshore_350 import (
    InputChannel,
    OutputChannel,
    State,
)
from pyacquisition.tasks import NewFile, WaitFor
from simulated import SimulatedCryostat, SimulatedLockin


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


@dataclass
class RecordAt(Task):
    """Go to a temperature and hold there, with a file for each part."""

    kelvin: float
    dwell: int = 60  # seconds

    @property
    def description(self):
        return f"Record at {self.kelvin} K for {self.dwell} s"

    async def run(self, experiment):
        await self.run_subtask(NewFile(file_name=f"{self.kelvin:g}K ramp"))
        await self.run_subtask(SetTemperature(self.kelvin))
        await self.run_subtask(NewFile(file_name=f"{self.kelvin:g}K hold"))
        await self.run_subtask(WaitFor(seconds=self.dwell))
        self.log(f"Recorded at {self.kelvin} K")


@dataclass
class TemperatureSweep(Task):
    """Record a data file at each temperature from low to high."""

    low: float
    high: float
    step: float
    dwell: int = 60  # seconds at each temperature

    @property
    def description(self):
        return f"Sweep {self.low} to {self.high} K"

    async def run(self, experiment):
        points = round((self.high - self.low) / self.step) + 1
        for i in range(points):
            await self.run_subtask(
                RecordAt(self.low + i * self.step, self.dwell)
            )
            self.log(f"Finished point {i + 1} of {points}")


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
        self.register_task(RecordAt, label="Record At")
        self.register_task(TemperatureSweep, label="Temperature Sweep")


if __name__ == "__main__":
    MyExperiment().run()
