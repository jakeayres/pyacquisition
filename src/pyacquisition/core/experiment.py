import tomllib
import asyncio
from pathlib import Path
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

        self._task_manager = TaskManager()

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
                    "file_extension", ".data"
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
                    experiment._rack.add_instrument(inst)
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
                        experiment._rack.add_instrument(inst)
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

                if instrument_name not in experiment._rack.instruments:
                    logger.warning(
                        f"Instrument '{instrument_name}' not found for measurement '{name}'"
                    )
                    continue

                instrument = experiment._rack.instruments[instrument_name]

                if method_name not in instrument.queries:
                    logger.warning(
                        f"Method '{method_name}' not found for instrument '{instrument_name}'"
                    )
                    continue

                method = instrument.queries[method_name]

                if args:
                    method = cls._resolve_method_args(method, args)

                experiment._rack.add_measurement(Measurement(name, method))
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
    def instruments(self) -> dict:
        """
        Returns the instruments associated with the experiment.

        Returns:
            dict: A dictionary of instrument instances.
        """
        return self._rack.instruments

    def setup(self) -> None:
        """
        Sets up the experiment environment.

        This method is responsible for preparing the experiment environment, such as
        initializing resources or configuring dependencies.
        """
        pass

    def teardown(self) -> None:
        """
        Cleans up the experiment environment.

        This method is responsible for releasing resources or performing any necessary cleanup
        after the experiment has run.
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
                tg.create_task(self._run_component(self._task_manager))
                logger.debug("All experiment tasks started")

                await self._shutdown_event.wait()

                logger.info("Shutdown event set, terminating tasks")

                await self._api_server.shutdown()
                await self._rack.shutdown()
                await self._calculations.shutdown()
                await self._scribe.shutdown()
                await self._task_manager.shutdown()

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
        Runs the experiment.
        """
        logger.info("Experiment started")

        try:
            asyncio.run(self._run())
        except KeyboardInterrupt:
            logger.info("Experiment interrupted by user")
        except Exception as e:
            logger.error(f"An error occurred while running the experiment: {e}")

        logger.info("Experiment ended")

    def register_task(self, task: Task, **kwargs) -> None:
        """
        Registers a task with the experiment.

        Args:
            task (Task): The task to register.
        """
        self._task_manager.register_task(self, task, **kwargs)

    def _register_endpoints(self, api_server):
        """
        Register the endpoints for the experiment.
        """

        @api_server.app.get("/experiment/shutdown", tags=["experiment"])
        async def shutdown():
            """
            Endpoint to shut down the experiment.
            """
            logger.info("Shutting down the experiment")
            self._shutdown_event.set()
            return {"status": "success", "message": "Experiment shutdown initiated."}
