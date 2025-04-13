import tomllib
from loguru import logger
import sys
import os


class Experiment:
    """
    Class representing an experiment.
    """

    def __init__(self, config: dict = None) -> None:
        """
        Initializes the Experiment instance with an optional configuration.

        Args:
            config (dict, optional): A dictionary containing experiment configuration.
        """
        self.config = config or {}
        
        # Main config
        main_config = self.config.get("main", {})
        root_path = main_config.get("root_path", os.getcwd())

        # Configure the logger
        logging_config = self.config.get("logging", {})
        console_level = logging_config.get("console_level", "DEBUG")
        file_level = logging_config.get("file_level", "DEBUG")
        log_file = logging_config.get("log_file", "debug.log")

        self.configure_logger(
            root_path=os.getcwd(),
            console_level=console_level,
            file_level=file_level,
            file_name=log_file,
        )

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
            return cls(config=config)
        except Exception as e:
            raise ValueError(f"Failed to load configuration from {toml_file}: {e}")

    def configure_logger(
        self,
        root_path: str,
        console_level: str = "DEBUG",
        file_level: str = "DEBUG",
        file_name: str = "debug.log",
    ) -> None:
        """
        Configures the logger for the application.

        Args:
            root_path (str): The root path where the log file will be stored.
            console_level (str, optional): Logging level for console output. Defaults to "DEBUG".
            file_level (str, optional): Logging level for file output. Defaults to "DEBUG".
            file_name (str, optional): Name of the log file. Defaults to "debug.log".
        """
        logger.remove()
        logger.add(
            sink=sys.stdout,
            level=console_level,
            format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}",
        )
        log_file_path = os.path.join(root_path, file_name)
        logger.add(
            sink=log_file_path,
            level=file_level,
            format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}",
        )

    def run(self) -> None:
        """
        Runs the experiment.
        """
        pass