from .core import Experiment
from .core.task import Task
import sys, asyncio
from dataclasses import dataclass


@dataclass
class MyTask(Task):

    name = "MyTask"
    description = "My task description"
    help = "My task help"

    async def run(self, experiment):
        yield 'STARTING'
        await asyncio.sleep(1)
        yield 'STARTING'
        await asyncio.sleep(1)
        yield 'STARTING'
        await asyncio.sleep(1)
        yield 'STARTING'
        await asyncio.sleep(1)



class MyExperiment(Experiment):
    

    def setup(self) -> None:


        self.register_task(MyTask)




def main(*args) -> None:
    """
    Main function to run the experiment.

    Args:
        toml_file (str): Path to the TOML configuration file.
    """
    
    toml_file = " ".join(sys.argv[1:])
    experiment = MyExperiment.from_config(toml_file=toml_file)
    experiment.run()