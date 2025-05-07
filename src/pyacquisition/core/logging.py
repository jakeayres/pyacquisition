from loguru import logger as loguru_logger
from threading import Lock
import sys
import time
from pathlib import Path
from .broadcaster import Broadcaster


class Logger(Broadcaster):
    """
    Singleton class for configuring and managing logging in the application.
    """

    LOG_LEVELS = {
        "DEBUG": 10,
        "INFO": 20,
        "WARNING": 30,
        "ERROR": 40,
        "EXCEPTION": 50,
    }

    _instance = None
    _lock = Lock()  # To make it thread-safe

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(Logger, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        # Avoid reinitializing if the instance already exists
        if hasattr(self, "_initialized") and self._initialized:
            return
        super().__init__()
        self._initialized = True
        self._gui_level = "DEBUG"
        self.log_path: Path = Path()
        loguru_logger.remove()

    def _should_broadcast(self, level: str) -> bool:
        return (
            self.LOG_LEVELS[level.upper()] >= self.LOG_LEVELS[self._gui_level.upper()]
        )

    def configure(
        self,
        root_path: Path,
        console_level: str = "DEBUG",
        file_level: str = "DEBUG",
        gui_level: str = "DEBUG",
        file_name: Path = Path("debug.log"),
    ) -> None:
        """
        Configures the logger for the application.

        Args:
            root_path (str): The root path where the log file will be stored.
            console_level (str, optional): Logging level for console output. Defaults to "DEBUG".
            file_level (str, optional): Logging level for file output. Defaults to "DEBUG".
            file_name (str, optional): Name of the log file. Defaults to "debug.log".
        """
        self._gui_level = gui_level
        loguru_logger.remove()
        loguru_logger.add(
            sink=sys.stdout,
            colorize=True,
            level=console_level,
            # format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}",
        )
        log_file_path = root_path / file_name
        self.debug(f"Log file path: {log_file_path}")
        loguru_logger.add(
            sink=log_file_path,
            level=file_level,
            format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}",
        )
        self.info(
            f"Logging configured: console level={console_level}, file level={file_level}, file name={log_file_path}, gui level={self._gui_level}"
        )

    def info(self, message: str) -> None:
        """
        Logs an info message.

        Args:
            message (str): The message to log.
        """
        loguru_logger.info(message)
        if self._should_broadcast("INFO"):
            self.broadcast_sync(
                {"time": time.time(), "message": message, "level": "info"}
            )

    def debug(self, message: str) -> None:
        """
        Logs a debug message.

        Args:
            message (str): The message to log.
        """
        loguru_logger.debug(message)
        if self._should_broadcast("DEBUG"):
            self.broadcast_sync(
                {"time": time.time(), "message": message, "level": "debug"}
            )

    def warning(self, message: str) -> None:
        """
        Logs a warning message.

        Args:
            message (str): The message to log.
        """
        loguru_logger.warning(message)
        if self._should_broadcast("WARNING"):
            self.broadcast_sync(
                {"time": time.time(), "message": message, "level": "warning"}
            )

    def error(self, message: str) -> None:
        """
        Logs an error message.

        Args:
            message (str): The message to log.
        """
        loguru_logger.error(message)
        if self._should_broadcast("ERROR"):
            self.broadcast_sync(
                {"time": time.time(), "message": message, "level": "error"}
            )

    def exception(self, message: str) -> None:
        """
        Logs an exception message.

        Args:
            message (str): The message to log.
        """
        loguru_logger.exception(message)
        if self._should_broadcast("EXCEPTION"):
            self.broadcast(
                {"time": time.time(), "message": message, "level": "exception"}
            )


# Singleton instance
logger = Logger()
