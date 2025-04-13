import tomllib
from .logging import logger


class Experiment:
    """
    Class representing an experiment.
    """

    def __init__(
        self,
        root_path: str = ".",
        console_log_level: str = "DEBUG",
        file_log_level: str = "DEBUG",  
        log_file_name: str = "debug.log",
    ) -> None:
        """
        Initializes the Experiment instance with an optional configuration.

        Args:
            config (dict, optional): A dictionary containing experiment configuration.
        """
        
        self.root_path = root_path
        
        # configure logging
        logger.configure(
            root_path=root_path,
            console_level=console_log_level,
            file_level=file_log_level,
            file_name=log_file_name,
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
            return cls(
                root_path=config.get("root_path", "."),
                console_log_level=config.get("logging", {}).get("console_level", "DEBUG"),
                file_log_level=config.get("logging", {}).get("file_level", "DEBUG"),
                log_file_name=config.get("logging", {}).get("file_name", "debug.log"),
            )
        except Exception as e:
            raise ValueError(f"Failed to load configuration from {toml_file}: {e}")


    def run(self) -> None:
        """
        Runs the experiment.
        """
        pass