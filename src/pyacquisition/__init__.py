from .core.logging import logger as logger
from .core.experiment import Experiment as Experiment
from .core.measurement import Measurement as Measurement
from .core.task import Task as Task
import sys
import asyncio
from dataclasses import dataclass

from .tasks import WaitFor, WaitUntil, NewFile
from .tasks import RampTemperature, SweepMagneticField

from .instruments.lakeshore.lakeshore_340 import OutputChannel as OC350


@dataclass
class MyTask(Task):
    age: int
    sex: str
    location: str

    @property
    def description(self):
        return f"Task {self.name} is {self.age} years old"

    async def run(self, experiment):
        yield self.name
        await asyncio.sleep(1)
        yield f"{self.age}"
        await asyncio.sleep(1)
        yield self.sex
        await asyncio.sleep(1)
        yield self.location
        await asyncio.sleep(1)
        yield "Done!"


class MyExperiment(Experiment):
    def setup(self) -> None:
        self.register_task(WaitFor)
        self.register_task(WaitUntil)
        self.register_task(MyTask, sex="male")
        self.register_task(NewFile, label="New")
        self.register_task(
            RampTemperature,
            label="Ramp 1",
            lakeshore="lake",
            output_channel=OC350.OUTPUT_1,
        )
        self.register_task(
            RampTemperature,
            label="Ramp 2",
            lakeshore="lake",
            output_channel=OC350.OUTPUT_2,
        )
        self.register_task(SweepMagneticField, magnet_psu="magnet")


def main(*args) -> None:
    """
    Main function to run the experiment.

    Args:
        toml_file (str): Path to the TOML configuration file.
    """

    toml_file = " ".join(sys.argv[1:])
    experiment = MyExperiment.from_config(toml_file=toml_file)
    experiment.run()
