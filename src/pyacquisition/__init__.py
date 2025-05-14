from .core.experiment import Experiment as Experiment
from .core.measurement import Measurement as Measurement
from .core.task_manager.task import Task as Task
import sys


def main(*args) -> None:
    """
    Main function to run the experiment.

    Args:
        toml_file (str): Path to the TOML configuration file.
    """

    toml_file = " ".join(sys.argv[1:])
    experiment = Experiment.from_config(toml_file=toml_file)
    experiment.run()
