from dataclasses import dataclass

from pyacquisition import Task
from pyacquisition.instruments.lakeshore.lakeshore_350 import (
    InputChannel,
    OutputChannel,
    State,
)


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
