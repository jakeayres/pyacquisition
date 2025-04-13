import tomllib
import asyncio
from .logging import logger
from .api_server import APIServer


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
        
        api_server_host: str = "localhost",
        api_server_port: int = 8000,
        allowed_cors_origins: list = ["http://localhost:3000"],
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
        
        self.api_server = APIServer(
            host=api_server_host,
            port=api_server_port,
            allowed_cors_origins=allowed_cors_origins,
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
            
                api_server_host=config.get("api_server", {}).get("host", "localhost"),
                api_server_port=config.get("api_server", {}).get("port", 8000),
                allowed_cors_origins=config.get("api_server", {}).get("allowed_cors_origins", ["http://localhost:3000"]),
            )
        except Exception as e:
            raise ValueError(f"Failed to load configuration from {toml_file}: {e}")


    def run(self) -> None:
        """
        Runs the experiment.
        """
        
        logger.debug("Experiment started")

        async def _run():
            try:
                # Run tasks in an async task group
                async with asyncio.TaskGroup() as tg:
                    tg.create_task(self.api_server.coroutine())
                    logger.debug("API server started")
                    # tg.create_task(task2())
                    # tg.create_task(task3())
                    logger.debug("All experiment tasks started")
            except Exception as e:
                logger.error(f"Task group terminated due to an error: {e}")
                

        asyncio.run(_run()) 