import tomllib
import asyncio
from .logging import logger
from .api_server import APIServer
from .rack import Rack
from .task_manager import TaskManager
from ..gui import Gui


class Experiment:
    """
    Class representing an experiment.

    This class provides the structure for setting up, running, and tearing down an experiment.
    It includes functionality for configuring logging, starting an API server, and managing
    tasks in an asynchronous task group.

    Attributes:
        root_path (str): The root directory for the experiment.
        console_log_level (str): The logging level for console output.
        file_log_level (str): The logging level for file output.
        log_file_name (str): The name of the log file.
        api_server_host (str): The host address for the API server.
        api_server_port (int): The port number for the API server.
        allowed_cors_origins (list): A list of allowed CORS origins for the API server.
    """

    def __init__(
        self,
        root_path: str = ".",
        console_log_level: str = "DEBUG",
        file_log_level: str = "DEBUG",
        log_file_name: str = "debug.log",
        api_server_host: str = "localhost",
        api_server_port: int = 8000,
        allowed_cors_origins: list = ["http://localhost:3000"],
        measurement_period: float = 0.25,
    ) -> None:
        """
        Initializes the Experiment instance.

        Args:
            root_path (str): The root directory for the experiment. Defaults to ".".
            console_log_level (str): The logging level for console output. Defaults to "DEBUG".
            file_log_level (str): The logging level for file output. Defaults to "DEBUG".
            log_file_name (str): The name of the log file. Defaults to "debug.log".
            api_server_host (str): The host address for the API server. Defaults to "localhost".
            api_server_port (int): The port number for the API server. Defaults to 8000.
            allowed_cors_origins (list): A list of allowed CORS origins for the API server. Defaults to ["http://localhost:3000"].
        """
        self.root_path = root_path

        # configure logging
        logger.configure(
            root_path=root_path,
            console_level=console_log_level,
            file_level=file_log_level,
            file_name=log_file_name,
        )

        self.api_server = APIServer(
            host=api_server_host,
            port=api_server_port,
            allowed_cors_origins=allowed_cors_origins,
        )
        
        self.rack = Rack(
            period = measurement_period,
        )
        
        self.task_manager = TaskManager()
        
        self.gui = Gui()

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
        try:
            with open(toml_file, "rb") as file:
                config = tomllib.load(file)
                print(config)
            return cls(
                root_path=config.get("root_path", "."),
                console_log_level=config.get("logging", {}).get("console_level", "DEBUG"),
                file_log_level=config.get("logging", {}).get("file_level", "DEBUG"),
                log_file_name=config.get("logging", {}).get("file_name", "debug.log"),
                api_server_host=config.get("api_server", {}).get("host", "localhost"),
                api_server_port=config.get("api_server", {}).get("port", 8000),
                allowed_cors_origins=config.get("api_server", {}).get("allowed_cors_origins", ["http://localhost:3000"]),
                measurement_period=config.get("rack", {}).get("period", 0.25),
            )
        except Exception as e:
            raise ValueError(f"Failed to load configuration from {toml_file}: {e}")


    def setup(self) -> None:
        """
        Sets up the experiment environment.

        This method is responsible for preparing the experiment environment, such as
        initializing resources or configuring dependencies.
        """
        logger.debug("Experiment setup started")
        self._ui_process = self.gui.run_in_new_process()
        logger.debug("Experiment setup completed")


    def teardown(self) -> None:
        """
        Cleans up the experiment environment.
        
        This method is responsible for releasing resources or performing any necessary cleanup
        after the experiment has run.
        """
        logger.debug("Experiment teardown started")
        self._ui_process.join()
        logger.debug("Experiment teardown completed")


    async def _run_component(self, component) -> None:
        """
        A coroutine that runs a component of the experiment.

        Args:
            component: The component to run (e.g., API server, rack, task manager, GUI).
        """
        try:
            component.register_endpoints(self.api_server)
            component.setup()
            logger.debug(f"Running {component.__class__.__name__}")
            await component.run()
        except Exception as e:
            logger.error(f"Error running {component.__class__.__name__}: {e}")
            raise
        finally:
            component.teardown()
            
        
    async def _run(self) -> None:
        """
        A coroutine that runs the experiment.
            
        The main logic of the experiment is executed within this coroutine.
        """
        try:
            #self.register_endpoints()
            self.setup()
            # Run tasks in an async task group
            async with asyncio.TaskGroup() as tg:
                tg.create_task(self._run_component(self.api_server))
                tg.create_task(self._run_component(self.rack))
                tg.create_task(self._run_component(self.task_manager))
                logger.debug("All experiment tasks started")
        except Exception as e:
            logger.error(f"Task group terminated due to an error: {e}")
        finally:
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
        
        
    def register_endpoints(self) -> None:
        
        self.rack.register_endpoints(self.api_server)