from ..instruments.lakeshore.lakeshore_340 import OutputChannel as OC340
from ..instruments.lakeshore.lakeshore_350 import OutputChannel as OC350
from ..instruments.lakeshore.lakeshore_350 import State
from ..core.task import Task
from dataclasses import dataclass
import asyncio


@dataclass
class RampTemperature(Task):
    """Ramp temperature setpoint"""

    lakeshore: str
    output_channel: OC340 | OC350
    setpoint: float
    ramp_rate: float

    def description(self):
        return f"Ramping temperature {self.output_channel} to {self.setpoint} at {self.ramp_rate}K/min"

    async def run(self, experiment):
        lakeshore = experiment.rack.instruments[self.lakeshore]
        tolerance = 0.003

        await asyncio.sleep(1)
        yield ""

        lakeshore.set_ramp(self.output_channel, State.ON, self.ramp_rate)
        yield f"Ramp Rate set: {self.ramp_rate}"
        await asyncio.sleep(1)
        yield ""

        lakeshore.set_setpoint(self.output_channel, self.setpoint)
        yield f"Setpoint set: {self.setpoint}"
        await asyncio.sleep(1)

        while (
            abs(lakeshore.get_setpoint(self.output_channel) - self.setpoint) > tolerance
        ):
            await asyncio.sleep(1)
            yield ""

        yield "Temperature ramp finished"
