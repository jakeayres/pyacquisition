import tomllib
import asyncio
import re
from pathlib import Path
from types import MappingProxyType
from functools import partial
import inspect
from enum import Enum
from .logging import logger
from .api_server import APIServer
from .rack import Rack
from . import calculations
from .calculations import Calculations
from .task_manager.task_manager import TaskManager
from .task_manager.task import Task
from .scribe import Scribe
from .history import History
from .log_history import LogHistory
from .sequences import Sequences
from .layout import Layout
# The module's names, since `gui` is also an option here.
from ..gui import Gui
from ..gui import mount as serve_gui
from ..instruments import instrument_map
from ..tasks import instrument_tasks, standard_tasks
from .measurement import Measurement
from .instrument import Instrument, SoftwareInstrument, resolve_enum_kwargs
from .config_parser import ConfigParser
from . import settings

# Seconds that the GUI's window is given to close by itself, once the
# experiment has stopped, before its process is terminated.
GUI_CLOSE_TIMEOUT = 5.0


class Experiment:
    """
    Class representing an experiment.

    This class provides the structure for setting up, running, and tearing down an experiment.
    It includes functionality for configuring logging, starting an API server, and managing
    tasks in an asynchronous task group.

    The options below are class attributes, so a subclass sets one by naming it,
    with no `__init__` needed:

        class MyExperiment(Experiment):
            data_path = "my_data"
            measurement_period = 0.5

    A value is taken from the first of these that gives one: an argument to
    `Experiment(...)` or `Experiment.from_config(...)`, then the TOML file, then the
    class attribute of the subclass, then the default shown here. A value that is
    not valid, or an attribute whose name is a near miss of an option
    (`data_pth`), raises an error.

    Attributes:
        root_path (str): The base folder for the data and log folders. Defaults to ".".
        data_path (str): The folder for data files, inside `root_path`. Defaults to ".".
        data_file_extension (str): The extension of data files. Defaults to "data".
        data_delimiter (str): The column separator in data files. Defaults to ",".
        history_points (int): The most rows kept in memory for the GUI (the
            current data file and the one before it), from 100 to 100,000,000. Each
            numeric column takes 8 bytes a row. Defaults to 500,000.
        log_path (str): The folder for the log file, inside `root_path`. Defaults to ".".
        log_file_name (str): The name of the log file. Defaults to "debug.log".
        console_log_level (str): The logging level for console output. Defaults to "DEBUG".
        file_log_level (str): The logging level for file output. Defaults to "DEBUG".
        gui_log_level (str): The logging level for GUI output. Defaults to "DEBUG".
        api_server_host (str): The host address for the API server. Defaults to "localhost".
        api_server_port (int): The port number for the API server. Defaults to 8000.
        api_server_fallback_ports (list[int]): Ports to try in turn if
            `api_server_port` is taken by another program, such as another
            experiment. The port it ends up on is logged, and the GUI uses it.
            Defaults to none, so a taken port stops the experiment starting.
        measurement_period (float): The time between measurements in seconds. Defaults to 0.25.
        gui (bool | str): Whether to show the GUI in a window of its own: True
            (or "new", its name) or False. It can also be opened in a browser at the
            API server's address, whether or not it has a window. Defaults to True.
        auto_tasks (bool): Whether the tasks that come with an instrument are
            registered by themselves when it is in the experiment, such as
            `RampTemperature` with a Lakeshore. Defaults to True.
    """

    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        settings.check_subclass(cls)

    def __init__(
        self,
        root_path: str | None = None,
        data_path: str | None = None,
        data_file_extension: str | None = None,
        data_delimiter: str | None = None,
        history_points: int | None = None,
        log_path: str | None = None,
        console_log_level: str | None = None,
        file_log_level: str | None = None,
        gui_log_level: str | None = None,
        log_file_name: str | None = None,
        api_server_host: str | None = None,
        api_server_port: int | None = None,
        api_server_fallback_ports: list[int] | tuple[int, ...] | None = None,
        measurement_period: float | None = None,
        gui: bool | str | None = None,
        auto_tasks: bool | None = None,
    ) -> None:
        """
        Initializes the Experiment instance.

        Every argument is optional, and one that is left out takes the value of the
        class attribute of the same name. See the class docstring for the options.

        Raises:
            ValueError: If a value is not valid.
        """
        options = settings.resolve(
            self,
            {
                "root_path": root_path,
                "data_path": data_path,
                "data_file_extension": data_file_extension,
                "data_delimiter": data_delimiter,
                "history_points": history_points,
                "log_path": log_path,
                "console_log_level": console_log_level,
                "file_log_level": file_log_level,
                "gui_log_level": gui_log_level,
                "log_file_name": log_file_name,
                "api_server_host": api_server_host,
                "api_server_port": api_server_port,
                "api_server_fallback_ports": api_server_fallback_ports,
                "measurement_period": measurement_period,
                "gui": gui,
                "auto_tasks": auto_tasks,
            },
        )

        self._root_path: Path = Path(options["root_path"])
        self._data_path: Path = self._root_path / Path(options["data_path"])
        self._log_path: Path = self._root_path / Path(options["log_path"])
        self._log_file_name: Path = Path(options["log_file_name"])

        # The recent log messages, for the GUI. Made before logging is
        # configured, so the first messages are kept too.
        self._log_history = LogHistory(logger)

        # configure logging
        logger.configure(
            root_path=self._log_path,
            console_level=options["console_log_level"],
            file_level=options["file_log_level"],
            gui_level=options["gui_log_level"],
            file_name=self._log_file_name,
        )

        self._api_server = APIServer(
            host=options["api_server_host"],
            port=options["api_server_port"],
            fallback_ports=options["api_server_fallback_ports"],
        )

        self._rack = Rack(
            period=options["measurement_period"],
        )

        self._calculations = Calculations()

        # The main task manager keeps the original endpoints. More can be added
        # with `add_task_manager()`, and they all run at the same time.
        self._task_manager = TaskManager()
        self._task_managers = {self._task_manager.name: self._task_manager}
        # Queues saved to use again, in `sequences` under the root path.
        self._sequences = Sequences(self._root_path / "sequences", self._task_managers)
        # Tasks registered on every task manager, kept so that a task manager added
        # later gets them too.
        self._shared_tasks = []
        self._registered_tasks = set()  # the classes, so as not to register one twice
        self._auto_tasks = options["auto_tasks"]

        # The GUI's page is served whether or not it has a window, so that it can
        # be opened in a browser too. Its window is made either way, but only
        # started if asked for.
        serve_gui(self._api_server.app)
        self._run_gui = settings.gui_to_run(options["gui"]) is not None
        self._gui = Gui(
            host=options["api_server_host"],
            port=options["api_server_port"],
        )

        self._scribe = Scribe(
            root_path=self._data_path,
            delimiter=options["data_delimiter"],
            extension=options["data_file_extension"],
        )

        # The recent rows, for the GUI: kept since the current file started
        # (and the file before), and streamed with a number for each event.
        self._history = History(max_rows=options["history_points"])

        self._calculations.subscribe_to(self._rack)
        self._scribe.subscribe_to(self._calculations)
        self._history.subscribe_to(self._calculations)
        self._scribe.add_file_listener(self._history.new_file)

        # History's events (and the log's) are made to be JSON, so sent as they are.
        self._api_server.add_websocket_endpoint("/stream/data").subscribe_to(self._history)

        self._api_server.add_websocket_endpoint("/stream/logs").subscribe_to(
            self._log_history
        )

        for task in standard_tasks:
            self.register_task(task)

        self._shutdown_event = asyncio.Event()
        self._started = False
        # The error or interruption that stopped it, if one did (see `_adopt_gui`).
        self._error = None
        # A window already open, which the experiment takes over (see `_adopt_gui`).
        self._adopted_ui_process = None
        # What the interface calls the experiment. `from_config` names a plain
        # Experiment after its TOML file instead.
        self._name = type(self).__name__
        # The GUI's layout, kept by name (from_config renames it afterwards).
        self._layout = Layout(self._root_path, lambda: self._name)

        logger.info("[Experiment] Fully initialized")

    @staticmethod
    def _read_toml(toml_file: str) -> dict:
        """
        Load and parse a TOML file, returning its contents as a dictionary.

        Args:
            toml_file (str): The path to the TOML file to read.

        Returns:
            dict: The parsed contents of the TOML file.

        Raises:
            ValueError: If the file is not found, cannot be decoded, or another error occurs during reading.
        """
        try:
            with open(toml_file, "rb") as file:
                return tomllib.load(file)
        except FileNotFoundError:
            raise ValueError(f"TOML file '{toml_file}' not found.")
        except tomllib.TOMLDecodeError:
            raise ValueError(f"Failed to decode TOML file '{toml_file}'.")
        except Exception as e:
            raise ValueError(
                f"An error occurred while reading the TOML file '{toml_file}': {e}"
            )

    @staticmethod
    def _get_instrument_class(instrument_name: str):
        """
        Get the instrument class by name.

        Args:
            instrument_name (str): The name of the instrument.

        Returns:
            Instrument: The instrument class.

        Raises:
            ValueError: If the instrument is not found in the instrument map.
        """
        try:
            return instrument_map[instrument_name]
        except KeyError:
            raise ValueError(
                f"Instrument '{instrument_name}' not found in instrument map."
            )

    @classmethod
    def from_config(cls, toml_file: str, **overrides) -> "Experiment":
        """
        Creates an Experiment instance from a TOML configuration file.

        Called on a subclass, the options the file leaves out come from the
        subclass's class attributes. Options the file sets win over them, and
        `overrides` win over the file.

        Args:
            toml_file (str): Path to the TOML configuration file.
            **overrides: Options to set whatever the file says, by their class
                attribute names, for example `gui=False`.

        Returns:
            Experiment: An instance of the Experiment class.

        Raises:
            ValueError: If the TOML file cannot be loaded or parsed, or holds an
                option that is not valid.
        """
        config = ConfigParser.parse(toml_file)

        try:
            experiment = cls._initialize_experiment(config, overrides)
            if cls is Experiment:
                experiment._name = Path(toml_file).stem
            cls._configure_instruments(experiment, config)
            cls._configure_measurements(experiment, config)
            cls._configure_calculations(experiment, config)
            return experiment
        except Exception as e:
            raise ValueError(
                f"Failed to configure instruments, measurements or calculations: {e}"
            )

    @classmethod
    def _initialize_experiment(
        cls, config: dict, overrides: dict | None = None
    ) -> "Experiment":
        """
        Initializes the Experiment instance from the configuration.

        Only the options the configuration sets are passed on, so the others keep
        the class attributes of `cls`.

        Args:
            config (dict): The parsed TOML configuration.
            overrides (dict): Options that win over the configuration.

        Returns:
            Experiment: An initialized Experiment instance.
        """
        try:
            return cls(**{**settings.from_config(config), **(overrides or {})})
        except Exception as e:
            raise ValueError(f"Failed to create Experiment instance: {e}")

    @classmethod
    def _configure_instruments(cls, experiment: "Experiment", config: dict) -> None:
        """
        Configures the instruments for the experiment.

        Args:
            experiment (Experiment): The Experiment instance.
            config (dict): The parsed TOML configuration.
        """
        instruments = config.get("instruments", {})
        for name, instrument in instruments.items():
            try:
                instrument_class = cls._get_instrument_class(instrument["instrument"])

                if instrument.get("adapter", None) is None:
                    logger.debug(f"Creating instrument '{name}' without adapter")
                    inst = instrument_class(name)
                    experiment.add_instrument(inst)
                else:
                    logger.debug(
                        f"Creating instrument '{name}' with adapter '{instrument['adapter']}'"
                    )
                    if instrument.get("resource") is None:
                        raise ValueError("it has an adapter but no `resource`")
                    # An instrument that cannot be reached is skipped with a
                    # warning, so the rest of the rig still comes up.
                    inst = instrument_class(
                        name,
                        instrument["resource"],
                        adapter=instrument["adapter"],
                        **instrument.get("args", {}),
                    )
                    experiment.add_instrument(inst)
            except Exception as e:
                logger.warning(f"Failed to configure instrument '{name}': {e}")

    @classmethod
    def _configure_measurements(cls, experiment: "Experiment", config: dict) -> None:
        """
        Configures the measurements for the experiment.

        Args:
            experiment (Experiment): The Experiment instance.
            config (dict): The parsed TOML configuration.
        """
        measurements = config.get("measurements", {})
        for name, measurement in measurements.items():
            logger.debug(f"Configuring measurement '{name}'")
            try:
                instrument_name = measurement.get("instrument")
                method_name = measurement.get("method")
                args = measurement.get("args", None)

                if instrument_name not in experiment.instruments:
                    logger.warning(
                        f"Instrument '{instrument_name}' not found for measurement '{name}'"
                    )
                    continue

                instrument = experiment.instruments[instrument_name]

                if method_name not in instrument.queries:
                    logger.warning(
                        f"Method '{method_name}' not found for instrument '{instrument_name}'"
                    )
                    continue

                method = instrument.queries[method_name]

                if args:
                    method = cls._resolve_method_args(method, args)

                experiment.add_measurement(
                    Measurement(name, method, unit=measurement.get("unit"))
                )
            except Exception as e:
                logger.warning(f"Failed to configure measurement '{name}': {e}")

    @classmethod
    def _configure_calculations(cls, experiment: "Experiment", config: dict) -> None:
        """
        Adds the calculations the configuration describes, in order. One that
        uses a column the experiment doesn't have, because a measurement couldn't
        be configured, is left out with a warning, as the measurement was.

        Args:
            experiment (Experiment): The Experiment instance.
            config (dict): The parsed TOML configuration, already checked.
        """
        table = config.get("calculations", {})
        made = calculations.from_config(table, config.get("measurements", {}))
        columns = set(experiment.measurements)
        for (name, options), calculation in zip(table.items(), made):
            missing = [c for c in calculations.config_inputs(options) if c not in columns]
            if missing:
                logger.warning(
                    f"Calculation '{name}' is left out, as the experiment has no "
                    f"column {', '.join(repr(c) for c in missing)}"
                )
                continue
            logger.debug(f"Configuring calculation '{name}'")
            experiment.add_calculation(calculation)
            columns.add(name)

    @staticmethod
    def _resolve_method_args(method, args: dict):
        """
        Resolves method arguments, including Enum types.

        Args:
            method: The method to resolve arguments for.
            args (dict): The arguments to resolve.

        Returns:
            Callable: The method with resolved arguments.
        """
        method_hints = inspect.signature(method).parameters
        given = {name: args[name] for name in method_hints if name in args}
        # A string for an enum, such as "INPUT_A", becomes the member it names.
        resolved_args = resolve_enum_kwargs(method, given)
        for arg_name, arg_value in resolved_args.items():
            annotation = method_hints[arg_name].annotation
            if (
                inspect.isclass(annotation)
                and issubclass(annotation, Enum)
                and not isinstance(arg_value, annotation)
            ):
                raise ValueError(
                    f"`{arg_name}` must name a member of {annotation.__name__}, "
                    f"got {arg_value!r}"
                )
            logger.debug(f"Resolved argument '{arg_name}': {arg_value}")
        return partial(method, **resolved_args)

    @property
    def instruments(self) -> MappingProxyType:
        """
        Returns the instruments associated with the experiment.

        The mapping is read-only. Use `add_instrument` and `remove_instrument`
        to change it.

        Returns:
            MappingProxyType: A read-only mapping of instrument uid to instrument.
        """
        return MappingProxyType(self._rack.instruments)

    @property
    def measurements(self) -> MappingProxyType:
        """
        Returns the measurements associated with the experiment.

        The mapping is read-only. Use `add_measurement` and `remove_measurement`
        to change it.

        Returns:
            MappingProxyType: A read-only mapping of measurement name to measurement.
        """
        return MappingProxyType(self._rack.measurements)

    @property
    def task_managers(self) -> MappingProxyType:
        """
        Returns the task managers of the experiment.

        There is always one called `"main"`, which is where tasks go by default.
        The mapping is read-only. Use `add_task_manager` to add another.

        Returns:
            MappingProxyType: A read-only mapping of name to task manager.
        """
        return MappingProxyType(self._task_managers)

    def _check_not_started(self, action: str) -> None:
        """
        Raises if the experiment has already started running.

        Instrument endpoints are registered with the API server, and the GUI builds
        its menus from them, when the experiment starts. Changes after that point
        would be measured but not visible to either.
        """
        if self._started:
            raise RuntimeError(
                f"Cannot {action} after the experiment has started running. "
                "Instruments, measurements, calculations and task managers must be "
                "set up beforehand, for example in `setup()`."
            )

    def add_instrument(self, instrument: Instrument | SoftwareInstrument) -> None:
        """
        Adds an instrument to the experiment.

        Must be called before the experiment starts running, for example in `setup()`.

        A hardware instrument opens its own connection from the address it is
        given, and the experiment closes it when the experiment ends.

        Args:
            instrument (Instrument | SoftwareInstrument): The instrument to add.

        Raises:
            RuntimeError: If the experiment has already started running.

        Example:
            clock = Clock("clock")
            experiment.add_instrument(clock)

            lockin = SR_830("lockin", "GPIB0::7::INSTR")
            experiment.add_instrument(lockin)
        """
        self._check_not_started("add an instrument")
        self._rack.add_instrument(instrument)

    def remove_instrument(self, uid: str) -> None:
        """
        Removes an instrument from the experiment.

        Must be called before the experiment starts running, for example in `setup()`.

        Args:
            uid (str): The uid of the instrument to remove.

        Raises:
            RuntimeError: If the experiment has already started running.
        """
        self._check_not_started("remove an instrument")
        self._rack.remove_instrument(uid)

    def add_measurement(self, measurement: Measurement) -> None:
        """
        Adds a measurement to the experiment.

        Must be called before the experiment starts running, for example in `setup()`.

        Args:
            measurement (Measurement): The measurement to add.

        Raises:
            RuntimeError: If the experiment has already started running.

        Example:
            experiment.add_measurement(Measurement("time", clock.timestamp_ms))
        """
        self._check_not_started("add a measurement")
        self._rack.add_measurement(measurement)

    def remove_measurement(self, name: str) -> None:
        """
        Removes a measurement from the experiment.

        Must be called before the experiment starts running, for example in `setup()`.

        Args:
            name (str): The name of the measurement to remove.

        Raises:
            RuntimeError: If the experiment has already started running.
        """
        self._check_not_started("remove a measurement")
        self._rack.remove_measurement(name)

    def add_calculation(self, calculation, units: dict | None = None) -> None:
        """
        Adds a calculation, which makes new columns from the measurements.

        A calculation is a function that takes a row of data (a dict of column
        name to value) and returns a dict of new columns. Calculations run in the
        order they are added, and each one sees the columns added by the ones
        before it. The results are saved to the data file alongside the
        measurements.

        Must be called before the experiment starts running, for example in `setup()`.

        Args:
            calculation (callable): A function, lambda or `Calculation` such as
                `RollingMean`.
            units (dict | None): The unit of each new column that has one, for
                display in the interface, such as `{"power": "W"}`.

        Raises:
            RuntimeError: If the experiment has already started running.
            TypeError: If the calculation is not callable, or a unit is not text.

        Example:
            experiment.add_calculation(
                lambda row: {"power": row["v"] * row["i"]}, units={"power": "W"}
            )
            experiment.add_calculation(RollingMean("power", window=10, unit="W"))
        """
        self._check_not_started("add a calculation")
        self._calculations.add_calculation(calculation, units=units)

    def add_task_manager(self, name: str) -> TaskManager:
        """
        Adds a task manager, which runs its own queue of tasks at the same time as
        the others.

        Each task manager runs the tasks in its queue one after another, and is
        paused, resumed and aborted independently of the others. Use one for work
        that must carry on while the main queue does something else, such as a
        control loop.

        Queue tasks on it in `setup()` with `task_manager.add_task(...)`. Every task
        registered with `register_task`, including the standard ones, can be queued
        on it from the API, unless it was registered for other task managers only.
        Its endpoints are placed under `/managers/<name>/`.

        Must be called before the experiment starts running, for example in `setup()`.

        Args:
            name (str): The name of the task manager. It is used in URLs, so it may
                only contain letters, numbers, `_` and `-`. `"main"` is taken.

        Returns:
            TaskManager: The new task manager.

        Raises:
            RuntimeError: If the experiment has already started running.
            ValueError: If the name is not valid, or is already used.

        Example:
            control = self.add_task_manager("control")
            control.add_task(HoldTemperature(kelvin=4.2))
        """
        self._check_not_started("add a task manager")
        if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", name):
            raise ValueError(
                f"Invalid task manager name {name!r}. Use letters, numbers, "
                "`_` and `-` only."
            )
        if name in self._task_managers:
            raise ValueError(f"There is already a task manager called '{name}'.")

        task_manager = TaskManager(
            name=name,
            path=f"/managers/{name}",
            tasks_path=f"/managers/{name}/tasks",
        )
        self._task_managers[name] = task_manager
        for task, kwargs in self._shared_tasks:
            task_manager.register_task(self, task, **kwargs)
        return task_manager

    def setup(self) -> None:
        """
        Sets up the experiment environment.

        Override this method to implement custom setup logic for the experiment. It
        is called before the main experiment event loop starts
        """
        pass

    def teardown(self) -> None:
        """
        Cleans up the experiment environment.

        Override this method to implement custom teardown logic for the experiment.
        It is called after the main experiment event loop ends.
        """
        pass

    async def _run_component(self, component) -> None:
        """
        A coroutine that runs a component of the experiment.

        Args:
            component: The component to run (e.g., API server, rack, task manager, GUI).
            experiment: The Experiment instance (optional).
        """
        component._register_endpoints(self._api_server)
        await component.setup()
        logger.debug(f"Running {component.__class__.__name__}")
        await component.run(experiment=self)
        await component.teardown()

    async def _run(self) -> None:
        """
        A coroutine that runs the experiment.

        The main logic of the experiment is executed within this coroutine.
        """
        # The port first, before anything is set up: if none can be had, the
        # experiment stops here with nothing to undo. And the GUI must be told the
        # port the server ends up on. (`run` logs the PortsUnavailable error,
        # which says which ports were tried.)
        port = self._api_server.bind()
        self._gui.host = self._api_server.host
        self._gui.port = port
        logger.info(f"[Experiment] API server on port {port}")

        try:
            self._register_endpoints(self._api_server)
            self.setup()
            self._register_instrument_tasks()
            self._started = True
            try:
                if self._adopted_ui_process is not None:
                    self._ui_process = self._adopted_ui_process
                    self._gui.end_handover()  # the window follows this server now
                elif self._run_gui:
                    self._ui_process = self._gui.run_in_new_process()
                    self._ui_process.start()
            except Exception as e:
                logger.error(f"Error during experiment setup: {e}")
                raise

            # async def monitor_shutdown_event(workers):
            #     """
            #     Monitor the shutdown event and terminate the workers if set.
            #     """
            #     await self._shutdown_event.wait()
            #     logger.info("Shutdown event set, terminating workers")

            #     self._api_server.server.should_exit = True
            #     self._rack._shutdown_event.set()

            async with asyncio.TaskGroup() as tg:
                # tg.create_task(monitor_shutdown_event(tg))
                tg.create_task(self._run_component(self._api_server))
                tg.create_task(self._run_component(self._rack))
                tg.create_task(self._run_component(self._calculations))
                tg.create_task(self._run_component(self._scribe))
                tg.create_task(self._run_component(self._history))
                tg.create_task(self._run_component(self._log_history))
                for task_manager in self._task_managers.values():
                    tg.create_task(self._run_component(task_manager))
                if self._run_gui:
                    tg.create_task(self._watch_gui(self._ui_process))
                logger.debug("All experiment tasks started")

                await self._shutdown_event.wait()

                logger.info("Shutdown event set, terminating tasks")

                await self._api_server.shutdown()
                await self._rack.shutdown()
                await self._calculations.shutdown()
                await self._scribe.shutdown()
                await self._history.shutdown()
                await self._log_history.shutdown()
                for task_manager in self._task_managers.values():
                    await task_manager.shutdown()

        except Exception as e:
            self._error = e
            logger.error(f"Task group terminated due to an error: {e}")
            if isinstance(e, ExceptionGroup):
                for subexception in e.exceptions:
                    logger.exception(f"Subexception details: {e}")
        finally:
            self._api_server.release()  # if it never got as far as serving
            try:
                self._stop_gui()
            except Exception as e:
                logger.error(f"Error during experiment teardown: {e}")
                raise
            try:
                self.teardown()
            finally:
                self._close_instruments()

    def _adopt_gui(self, gui: Gui, process) -> None:
        """
        Takes over a window that is already open, instead of opening one: the
        setup page's (see `core/setup.py`), whose Run button starts this
        experiment. The window is being handed over (`gui.start_handover()` has
        been called), and is moved to this experiment's server once `setup()`
        has run, where a new window would be started. If the experiment stops
        before that, the window is left as it is, for the setup page to take
        back, and `_error` says why it stopped.

        Args:
            gui (Gui): The window's `Gui`, whose process is running.
            process: The window's process.
        """
        self._gui = gui
        self._adopted_ui_process = process
        self._run_gui = True

    async def _watch_gui(self, process, period: float = 0.25) -> None:
        """
        Shuts the experiment down if the GUI's process ends, so that it never runs
        on with no GUI to see it by. The GUI normally asks for the shutdown itself
        before it closes, and then this does nothing more.

        Args:
            process: The GUI's process.
            period (float): The time between checks, in seconds.
        """
        while not self._shutdown_event.is_set():
            if not process.is_alive():
                logger.warning(
                    "[Experiment] The GUI has closed, so the experiment is shutting down"
                )
                self._shutdown_event.set()
                return
            try:
                await asyncio.wait_for(self._shutdown_event.wait(), timeout=period)
            except TimeoutError:
                pass

    def _stop_gui(self) -> None:
        """
        Ends the GUI's process, if it was started, and waits for it.

        The window is told to close, and given a moment to, and only terminated
        if it has not.
        """
        process = getattr(self, "_ui_process", None)
        if process is None:
            return
        logger.debug("Waiting for GUI process to finish")
        self._gui.close()
        process.join(timeout=GUI_CLOSE_TIMEOUT)
        if process.is_alive():
            process.terminate()
        process.join()
        logger.debug("GUI process finished")

    def _close_instruments(self) -> None:
        """
        Closes the connections that the instruments opened themselves.

        Runs after `teardown()`, so that it can still talk to the instruments.
        A failure to close one does not stop the others from closing.
        """
        for uid, instrument in self._rack.instruments.items():
            try:
                instrument.close()
            except Exception as e:
                logger.warning(f"Failed to close instrument '{uid}': {e}")

    def run(self) -> None:
        """
        Run the experiment. The main entry point for executing the experiment.

        Example:
            experiment = Experiment.from_config("experiment_config.toml")
            experiment.run()
        """
        logger.info("Experiment started")

        try:
            asyncio.run(self._run())
        except KeyboardInterrupt as e:
            self._error = e
            logger.info("Experiment interrupted by user")
        except Exception as e:
            self._error = e
            logger.error(f"An error occurred while running the experiment: {e}")

        logger.info("Experiment ended")

    def _register_instrument_tasks(self) -> None:
        """
        Registers the tasks that come with an instrument, for the instruments that
        the experiment has. It runs when `setup()` has added them.

        A task is registered when every instrument it is for is present. The input
        that holds the instrument's id is fixed to it, so the form does not ask, if
        there is exactly one such instrument. With several, the form asks which. A
        task that has already been registered is left as it is, and nothing is done
        if `auto_tasks` is off.
        """
        if not self._auto_tasks:
            return
        for task in instrument_tasks:
            if task in self._registered_tasks:
                continue
            found = {}
            for field, types in (task.applies_to or {}).items():
                ids = [
                    uid
                    for uid, instrument in self.instruments.items()
                    if isinstance(instrument, types)
                ]
                if not ids:
                    break
                found[field] = ids
            else:
                fixed = {field: ids[0] for field, ids in found.items() if len(ids) == 1}
                label = re.sub(r"(?<!^)(?=[A-Z])", " ", task.__name__)
                logger.debug(f"Registering '{label}' for {sorted(found.values())}")
                self.register_task(task, label=label, **fixed)

    def register_task(self, task: Task, manager=None, **kwargs) -> None:
        """
        Registers a task with the experiment.

        This method allows you to register a task with the experiment. Once
        registered, the task can be added to a task queue within the GUI.

        By default a task can be queued on every task manager, including any you
        add afterwards. Give `manager` to limit it to one, or to several.

        Args:
            task (Task): The task to register.
            manager (str | list[str] | None): The name of the task manager, or a
                list of names, that the task can be queued on. Defaults to all of
                them. See `add_task_manager`.
            **kwargs: Additional keyword arguments to pass to the task manager.

        Raises:
            ValueError: If there is no task manager with one of the names.

        Example:
            experiment.register_task(MyCustomTask())
            experiment.register_task(HoldTemperature, manager="control")

        """
        self._registered_tasks.add(task)
        if manager is None:
            self._shared_tasks.append((task, kwargs))
            for task_manager in self._task_managers.values():
                task_manager.register_task(self, task, **kwargs)
            return

        names = [manager] if isinstance(manager, str) else list(manager)
        for name in names:
            if name not in self._task_managers:
                raise ValueError(
                    f"There is no task manager called '{name}'. Add it first with "
                    f"`add_task_manager()`. The task managers are: "
                    f"{', '.join(self._task_managers)}."
                )
        for name in names:
            self._task_managers[name].register_task(self, task, **kwargs)

    def _column_info(self) -> list[dict]:
        """What is known about each column of the data (see /experiment/columns)."""
        columns = [
            {
                "name": name,
                "kind": "measurement",
                "source": measurement.source,
                "unit": measurement.unit,
            }
            for name, measurement in self._rack.measurements.items()
        ]
        measured = {column["name"] for column in columns}
        columns += [
            {
                "name": name,
                "kind": "calculation",
                "source": "",
                "unit": self._calculations.units.get(name),
            }
            for name in self._calculations.known_columns
            if name not in measured
        ]
        return columns

    def _register_endpoints(self, api_server):
        """
        Register the endpoints for the experiment.
        """
        self._sequences._register_endpoints(api_server)
        self._layout._register_endpoints(api_server)

        @api_server.app.get("/experiment/info", tags=["experiment"])
        async def experiment_info():
            """
            Endpoint for what the interface shows about the experiment: its name,
            which is the name of its class, or of its TOML file for a plain
            `Experiment.from_config`.
            """
            return {"status": 200, "data": {"name": self._name}}

        @api_server.app.get("/experiment/columns", tags=["experiment"])
        async def experiment_columns():
            """
            Endpoint describing the columns of the data: each measurement, then each
            calculated column that is known, in order, with its `kind`
            ("measurement" or "calculation"), its `source` (`instrument.method`,
            or empty) and its `unit` (or null). A calculated column from a plain
            function is only listed if it was given a unit.
            """
            return {"status": 200, "data": self._column_info()}

        @api_server.app.get("/managers", tags=["experiment"])
        async def list_task_managers():
            """
            Endpoint to list the task managers. The main one is controlled at
            `/task_manager/...`, and the others at `/managers/<name>/...`.
            """
            return {"status": 200, "data": list(self._task_managers)}

        @api_server.app.get("/managers/state", tags=["experiment"])
        async def task_manager_states():
            """
            Endpoint for the status, current task and queue of every task manager,
            in one call.
            """
            return {
                "status": 200,
                "data": {
                    name: task_manager.state()
                    for name, task_manager in self._task_managers.items()
                },
            }

        @api_server.app.get("/experiment/shutdown", tags=["experiment"])
        async def shutdown():
            """
            Endpoint to shut down the experiment.
            """
            logger.info("Shutting down the experiment")
            self._shutdown_event.set()
            return {"status": "success", "message": "Experiment shutdown initiated."}


# The options are class attributes, so that a subclass can set them by name. Their
# defaults are kept with the rest of their description in `settings`.
for _setting in settings.SETTINGS.values():
    setattr(Experiment, _setting.name, _setting.default)
del _setting
