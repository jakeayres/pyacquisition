from ..instruments.lakeshore.lakeshore_340 import Lakeshore_340
from ..instruments.lakeshore.lakeshore_340 import OutputChannel as OC340
from ..instruments.lakeshore.lakeshore_350 import Lakeshore_350
from ..instruments.lakeshore.lakeshore_350 import OutputChannel as OC350
from ..instruments.lakeshore.lakeshore_350 import State
from ..core import Task
from ..core.instrument import resolve_enum_kwargs
from dataclasses import dataclass
from enum import Enum


@dataclass
class RampTemperature(Task):
    """Ramp temperature setpoint

    Registered by itself when there is a Lakeshore 340 or 350.

    Attributes:
        lakeshore (str): The id of the temperature controller.
        output_channel (str): The output to ramp, such as `"OUTPUT_1"`. An
            `OutputChannel` member is accepted too.
        setpoint (float): The temperature to ramp to.
        ramp_rate (float): The ramp rate, in kelvin per minute.
    """

    applies_to = {"lakeshore": (Lakeshore_340, Lakeshore_350)}

    lakeshore: str
    output_channel: OC340 | OC350
    setpoint: float
    ramp_rate: float

    @property
    def description(self) -> str:
        channel = self.output_channel
        channel = channel.name if isinstance(channel, Enum) else channel
        return (
            f"Ramping temperature {channel} to {self.setpoint} at {self.ramp_rate}K/min"
        )

    async def run(self, experiment):
        lakeshore = experiment.instruments[self.lakeshore]
        # The channel is the one of this controller, whichever way it was given.
        channel = self.output_channel
        channel = resolve_enum_kwargs(
            lakeshore.set_setpoint,
            {"output_channel": channel.name if isinstance(channel, Enum) else channel},
        )["output_channel"]
        tolerance = 0.003

        await self.sleep(1)

        lakeshore.set_ramp(channel, State.ON, self.ramp_rate)
        self.log(f"Ramp Rate set: {self.ramp_rate}")
        await self.sleep(1)

        lakeshore.set_setpoint(channel, self.setpoint)
        self.log(f"Setpoint set: {self.setpoint}")
        await self.sleep(1)

        await self.wait_until(
            lambda: abs(lakeshore.get_setpoint(channel) - self.setpoint) <= tolerance,
            what="the setpoint to finish ramping",
        )
        self.log("Temperature ramp finished")
