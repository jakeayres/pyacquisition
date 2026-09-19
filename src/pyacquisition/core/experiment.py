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
from .calculations import Calculations
from .task_manager.task_manager import TaskManager
from .task_manager.task import Task
from .scribe import Scribe
from ..gui import Gui
from ..instruments import instrument_map
from ..tasks import standard_tasks
from .measurement import Measurement
from .instrument import Instrument, SoftwareInstrument
from .adapters import get_adapter
from .config_parser import ConfigParser


class Experiment:
    """
    Class representing an experiment.

    This class provides the structure for setting up, running, and tearing down an experiment.
    It includes functionality for configuring logging, starting an API server, and managing
    tasks in an asynchronous task group.

    Attributes:
        root_path (Path): The root directory for the experiment.
        data_path (Path): The directory where experiment data will be stored.
        log_path (Path): The directory where logs will be stored.
        log_file_name (Path): The name of the log file.
        console_log_level (str): The logging level for console output.
        file_log_level (str): The logging level for file output.
        gui_log_level (str): The logging level for GUI output.
        api_server_host (str): The host address for the API server.
        api_server_port (int): The port number for the API server.
        measurement_period (float): The time interval between measurements in seconds.
    """

    def __init__(
        self,
        root_path: str = ".",
        data_path: str = ".",
        data_file_extension: str = "data",
        data_delimiter: str = ",",
        log_path: str = ".",
        console_log_level: str = "DEBUG",
        file_log_level: str = "DEBUG",
        gui_log_level: str = "DEBUG",
        log_file_name: str = "debug.log",
        api_server_host: str = "localhost",
        api_server_port: int = 8000,
        measurement_period: float = 0.25,
        gui: bool = True,
    ) -> None:
        """
        Initializes the Experiment instance.
        Args:
            root_path (str): The root directory for the experiment. Defaults to ".".
            data_path (str): The directory where experiment data will be stored. Defaults to ".".
            data_file_extension (str): The file extension for data files. Defaults to ".data".
            log_path (str): The directory where logs will be stored. Defaults to ".".
            console_log_level (str): The logging level for console output. Defaults to "DEBUG".
            file_log_level (str): The logging level for file output. Defaults to "DEBUG".
            gui_log_level (str): The logging level for GUI output. Defaults to "DEBUG".
            log_file_name (str): The name of the log file. Defaults to "debug.log".
            api_server_host (str): The host address for the API server. Defaults to "localhost".
            api_server_port (int): The port number for the API server. Defaults to 8000.
            measurement_period (float): The time interval between measurements in seconds. Defaults to 0.25.
            ui (bool): Whether to run the GUI. Defaults to True.
        """
        self._root_path: Path = Path(root_path)
        self._data_path: Path = self._root_path / Path(data_path)
        self._log_path: Path = self._root_path / Path(log_path)
        self._log_file_name: Path = Path(log_file_name)

        # configure logging
        logger.configure(
            root_path=self._log_path,
            console_level=console_log_level,
            file_level=file_log_level,
            gui_level=gui_log_level,
            file_name=self._log_file_name,
        )

        self._api_server = APIServer(
            host=api_server_host,
            port=api_server_port,
        )

        self._rack = Rack(
            period=measurement_period,
        )

        self._calculations = Calculations()

        # The main task manager keeps the original endpoints. More can be added
        # with `add_task_manager()`, and they all run at the same time.
        self._task_manager = TaskManager()
        self._task_managers = {self._task_manager.name: self._task_manager}
        # Tasks registered on every task manager, kept so that a task manager added
        # later gets them too.
        self._shared_tasks = []

        self._run_gui = gui
        self._gui = Gui(host=api_server_host, port=api_server_port)

        self._scribe = Scribe(
            root_path=self._data_path,
            delimiter=data_delimiter,
            extension=data_file_extension,
        )

        self._calculations.subscribe_to(self._rack)
        self._scribe.subscribe_to(self._calculations)

        self._api_server.add_websocket_endpoint("/data")
        self._api_server.websocket_endpoints["/data"].subscribe_to(self._rack)

        self._api_server.add_websocket_endpoint("/logs")
        self._api_server.websocket_endpoints["/logs"].subscribe_to(logger)

        for task in standard_tasks:
            self.register_task(task)

        self._shutdown_event = asyncio.Event()
        self._started = False

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

    @staticmethod
    def _get_adapter_class(adapter_name: str):
        """
        Get the adapter class by name.

        Args:
            adapter_name (str): The name of the adapter.

        Returns:
            Adapter: The adapter class.

        Raises:
            ValueError: If the adapter is not found in the adapter map.
        """
        try:
            return get_adapter(adapter_name)
        except KeyError:
            raise ValueError(f"Adapter '{adapter_name}' not found in adapter map.")

    @staticmethod
    def _open_resource(adapter, resource: str, timeout: int = 5000, **kwargs):
        """
        Open a resource using the appropriate adapter.

        Args:
            resource (str): The resource to open.

        Returns:
            Resource: The opened resource.

        Raises:
            ValueError: If the resource cannot be opened.
        """
        try:
            available_resources = adapter.list_resources()
            logger.debug(f"Available resources: {adapter.list_resources()}")
            if resource not in available_resources:
                logger.warning(f"Resource '{resource}' not found.")
                return None
            else:
                logger.debug(f"Opening resource '{resource}'")
                return adapter.open_resource(resource, timeout=timeout, **kwargs)
        except Exception as e:
            logger.warning(f"Failed to open resource '{resource}': {e}")
            return None

    @classmethod
    def from_config(cls, toml_file: str) -> "Experiment":
        """
        Creates an Experiment instance from a TOML configuration file.

        Args:
            toml_file (str): Path to the TOML configuration file.

        Returns:
            Experiment: An instance of the Experiment class.

        Raises:
            ValueError: If the TOML file cannot be loaded or parsed.
        """
        config = ConfigParser.parse(toml_file)

        try:
            experiment = cls._initialize_experiment(config)
            cls._configure_instruments(experiment, config)
            cls._configure_measurements(experiment, config)
            return experiment
        except Exception as e:
            raise ValueError(f"Failed to configure instruments or measurements: {e}")

    @classmethod
    def _initialize_experiment(cls, config: dict) -> "Experiment":
        """
        Initializes the Experiment instance from the configuration.

        Args:
            config (dict): The parsed TOML configuration.

        Returns:
            Experiment: An initialized Experiment instance.
        """
        try:
            return cls(
                root_path=config.get("experiment", {}).get("root_path", "."),
                data_path=config.get("data", {}).get("path", "."),
                data_file_extension=config.get("data", {}).get(
                    "file_extension", "data"
                ),
                data_delimiter=config.get("data", {}).get("delimiter", ","),
                log_path=config.get("logging", {}).get("path", "."),
                console_log_level=config.get("logging", {}).get(
                    "console_level", "DEBUG"
                ),
                file_log_level=config.get("logging", {}).get("file_level", "DEBUG"),
                gui_log_level=config.get("logging", {}).get("gui_level", "DEBUG"),
                log_file_name=config.get("logging", {}).get("file_name", "debug.log"),
                api_server_host=config.get("api_server", {}).get("host", "localhost"),
                api_server_port=config.get("api_server", {}).get("port", 8000),
                measurement_period=config.get("rack", {}).get("period", 0.25),
                gui=config.get("gui", {}).get("run", True),
            )
        except KeyError as e:
            raise ValueError(f"Missing required configuration key: {e}")
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
                    adapter_class = cls._get_adapter_class(instrument["adapter"])
                    kwargs = instrument.get("args", {})
                    resource = cls._open_resource(
                        adapter_class,
                        instrument.get("resource", None),
                        timeout=5000,
                        **kwargs,
                    )

                    if resource:
                        inst = instrument_class(name, resource)
                        experiment.add_instrument(inst)
                    else:
                        logger.warning(
                            f"Failed to open resource '{instrument.get('resource', None)}' for instrument '{name}'"
                        )
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

                experiment.add_measurement(Measurement(name, method))
            except Exception as e:
                logger.warning(f"Failed to configure measurement '{name}': {e}")

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
        resolved_args = {}
        for arg_name, arg_type in method_hints.items():
            if arg_name in args:
                arg_value = args[arg_name]
                if inspect.isclass(arg_type.annotation) and issubclass(
                    arg_type.annotation, Enum
                ):
                    logger.debug(
                        f"Resolving Enum type for argument '{arg_name}': {arg_value}"
                    )
                    resolved_args[arg_name] = arg_type.annotation[arg_value]
                else:
                    logger.debug(f"Resolving argument '{arg_name}': {arg_value}")
                    resolved_args[arg_name] = arg_value
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

        Args:
            instrument (Instrument | SoftwareInstrument): The instrument to add.

        Raises:
            RuntimeError: If the experiment has already started running.

        Example:
            clock = Clock("clock")
            experiment.add_instrument(clock)
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

    def add_calculation(self, calculation) -> None:
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

        Raises:
            RuntimeError: If the experiment has already started running.
            TypeError: If the calculation is not callable.

        Example:
            experiment.add_calculation(lambda row: {"power": row["v"] * row["i"]})
            experiment.add_calculation(RollingMean("power", window=10))
        """
        self._check_not_started("add a calculation")
        self._calculations.add_calculation(calculation)

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
        try:
            self._register_endpoints(self._api_server)
            self.setup()
            self._started = True
            try:
                if self._run_gui:
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
                for task_manager in self._task_managers.values():
                    tg.create_task(self._run_component(task_manager))
                logger.debug("All experiment tasks started")

                await self._shutdown_event.wait()

                logger.info("Shutdown event set, terminating tasks")

                await self._api_server.shutdown()
                await self._rack.shutdown()
                await self._calculations.shutdown()
                await self._scribe.shutdown()
                for task_manager in self._task_managers.values():
                    await task_manager.shutdown()

        except Exception as e:
            logger.error(f"Task group terminated due to an error: {e}")
            if isinstance(e, ExceptionGroup):
                for subexception in e.exceptions:
                    logger.exception(f"Subexception details: {e}")
        finally:
            try:
                if self._run_gui:
                    logger.debug("Waiting for GUI process to finish")
                    self._ui_process.terminate()
                    self._ui_process.join()
                    logger.debug("GUI process terminated")
            except Exception as e:
                logger.error(f"Error during experiment teardown: {e}")
                raise
            self.teardown()

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
        except KeyboardInterrupt:
            logger.info("Experiment interrupted by user")
        except Exception as e:
            logger.error(f"An error occurred while running the experiment: {e}")

        logger.info("Experiment ended")

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

    def _register_endpoints(self, api_server):
        """
        Register the endpoints for the experiment.
        """

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
