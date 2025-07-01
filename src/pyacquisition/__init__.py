from .core.experiment import Experiment as Experiment
from .core.measurement import Measurement as Measurement
from .core.task_manager.task import Task as Task
import sys
import argparse
import importlib.util
import inspect
from pathlib import Path


def _import_from_file(file_path):
    file_path = Path(file_path).resolve()
    if not file_path.exists() or file_path.suffix != ".py":
        raise FileNotFoundError(f"{file_path} is not a valid .py file")

    module_name = file_path.stem
    spec = importlib.util.spec_from_file_location(module_name, str(file_path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _find_experiment_class(module):
    for name, obj in inspect.getmembers(module, inspect.isclass):
        if issubclass(obj, Experiment) and obj is not Experiment:
            return obj
    raise ValueError("No class inheriting from ExperimentBaseClass found.")


def main(*args) -> None:
    """
    Main function to run the experiment.

    Args:
        toml (str): Path to the TOML configuration file.
    """

    parser = argparse.ArgumentParser(description="Run an experiment.")
    parser.add_argument(
        "--toml",
        type=str,
        required=False,
        help="Path to the TOML configuration file.",
    )
    parser.add_argument(
        "--py",
        type=str,
        required=False,
        help="Path to the Python script with experiment.",
    )
    
    parsed_args = parser.parse_args(args if args else sys.argv[1:])
    
    toml_file = parsed_args.toml if parsed_args.toml else None
    py_file = parsed_args.py if parsed_args.py else None
    
    if toml_file:
        print(f"Running experiment from TOML file: {toml_file}")
        experiment = Experiment.from_config(toml_file=toml_file)
        experiment.run()
    else:
        print("No TOML file provided. Please specify a TOML file with --toml.")
    
    if py_file:
        print(f"Running experiment from Python script: {py_file}")
        
        mod = _import_from_file(py_file)
        
        UserExperiment = _find_experiment_class(mod)
        experiment = UserExperiment()
        experiment.run()
    else:
        print("No Python script provided. Please specify a Python script with --py.")

