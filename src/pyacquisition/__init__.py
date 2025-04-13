from .core import Experiment
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