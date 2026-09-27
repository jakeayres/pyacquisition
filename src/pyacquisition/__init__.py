import argparse
import importlib.util
import inspect
import multiprocessing
import sys
from pathlib import Path

from .core.calculations import Calculation as Calculation
from .core.calculations import RollingMean as RollingMean
from .core.calculations import Sum as Sum
from .core.experiment import Experiment as Experiment
from .core.measurement import Measurement as Measurement
from .core.task_manager.task import Task as Task

# The GUI runs in its own process (see `gui.Gui.run_in_new_process`). On Windows,
# a frozen application (see `freeze.py`) that spawns a process re-executes the
# whole frozen bootstrap to create it, and without this, that re-execution runs
# this script over again from the top instead of becoming the child process. It
# has to run before anything creates a `Process`, and importing `pyacquisition`
# always happens before that, so it is here rather than left for a user's own
# script to remember. It is a no-op unless this really is that re-execution, on
# any platform, so it costs nothing the rest of the time.
multiprocessing.freeze_support()


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


def _add_source_arguments(parser) -> None:
    """`--toml` or `--py`, describing the experiment: exactly one is required."""
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--toml", type=str, help="Path to the TOML configuration file.")
    source.add_argument(
        "--py", type=str, help="Path to the Python script with the experiment."
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pyacquisition", description="Set up, run or freeze an experiment."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run an experiment.")
    _add_source_arguments(run_parser)

    build_parser = subparsers.add_parser(
        "build", help="Freeze an experiment into a standalone application."
    )
    _add_source_arguments(build_parser)
    build_parser.add_argument(
        "--name",
        type=str,
        default=None,
        help="The name of the built application. Defaults to the file's own name.",
    )
    build_parser.add_argument(
        "--onedir",
        action="store_true",
        help=(
            "Build a folder instead of a single executable. Starts faster, at the "
            "cost of being a folder rather than one file to hand over."
        ),
    )
    build_parser.add_argument(
        "--console",
        action="store_true",
        help="Keep the console window, to see errors from a build that misbehaves.",
    )
    build_parser.add_argument(
        "--icon",
        type=str,
        default=None,
        help="An .ico file for the application's icon.",
    )

    new_parser = subparsers.add_parser(
        "new",
        help="Build or change an experiment's config in a window.",
        description=(
            "Build or change an experiment's TOML config in a window, and run "
            "it from there. A file that doesn't exist yet is made when it is "
            "first saved."
        ),
    )
    new_parser.add_argument("config", type=str, help="Path to the TOML config file.")
    new_parser.add_argument(
        "--port",
        type=int,
        default=None,
        help=(
            "The port for the setup page, and for the experiment it runs. "
            "Defaults to the file's own, or 8000."
        ),
    )

    return parser


def _run(toml_file: str | None, py_file: str | None) -> None:
    if toml_file:
        print(f"Running experiment from TOML file: {toml_file}")
        Experiment.from_config(toml_file=toml_file).run()
    else:
        print(f"Running experiment from Python script: {py_file}")
        module = _import_from_file(py_file)
        UserExperiment = _find_experiment_class(module)
        UserExperiment().run()


def _build(args: argparse.Namespace) -> None:
    from .freeze import build_app

    kind = "TOML file" if args.toml else "Python script"
    print(f"Building a standalone application from {kind}: {args.toml or args.py}")
    try:
        app_dir = build_app(
            toml_file=args.toml,
            py_file=args.py,
            name=args.name,
            onefile=not args.onedir,
            windowed=not args.console,
            icon=args.icon,
        )
    except (ValueError, FileNotFoundError, RuntimeError) as error:
        raise SystemExit(f"pyacquisition build: {error}")
    print(f"Built {app_dir}")


def _new(config: str, port: int | None) -> None:
    path = Path(config)
    # A file that doesn't exist yet is made when it is first saved.
    if path.suffix.lower() != ".toml":
        raise SystemExit(f"pyacquisition new: {config} must be a .toml file.")
    if not path.parent.resolve().is_dir():
        raise SystemExit(f"pyacquisition new: the folder {path.parent} doesn't exist.")
    # Imported here, so that running an experiment doesn't load it.
    from .core.setup import open_setup

    open_setup(path, port=port)


def main(*args) -> None:
    """
    The `pyacquisition` command: `run` an experiment, `build` a standalone
    application from one, or set one up with `new`.

    Args:
        run --toml <path> | --py <path>: Run the experiment the file describes.
        new <path> [--port]: Build or change a TOML config in a window, and run
            it from there. See `pyacquisition.core.setup.open_setup`.
        build --toml <path> | --py <path> [--name] [--onedir] [--console] [--icon]:
            Freeze it into a standalone application with PyInstaller: a single
            executable by default. See `pyacquisition.freeze.build_app`.

    For backward compatibility, `pyacquisition --toml <path>` (with no
    subcommand) still works, as `pyacquisition run --toml <path>`.
    """
    argv = list(args) if args else sys.argv[1:]
    # `--help` alone lists the subcommands; anything else unknown is `run`'s.
    if not argv or argv[0] not in ("run", "build", "new", "-h", "--help"):
        argv = ["run", *argv]

    parsed = _build_parser().parse_args(argv)

    if parsed.command == "run":
        _run(parsed.toml, parsed.py)
    elif parsed.command == "new":
        _new(parsed.config, parsed.port)
    else:
        _build(parsed)
