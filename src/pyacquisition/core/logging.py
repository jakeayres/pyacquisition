from loguru import logger as loguru_logger
from threading import Lock
import sys
import os


class Logger:
    """
    Singleton class for configuring and managing logging in the application.
    """
    
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
        self._initialized = True
        
        
    def configure(
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
        loguru_logger.remove()
        loguru_logger.add(
            sink=sys.stdout,
            level=console_level,
            format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}",
        )
        log_file_path = os.path.join(root_path, file_name)
        loguru_logger.add(
            sink=log_file_path,
            level=file_level,
            format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}",
        )
        self.info(f"Logging configured: console level={console_level}, file level={file_level}, file name={file_name}") 
        
        
    def info(self, message: str) -> None:
        """
        Logs an info message.

        Args:
            message (str): The message to log.
        """
        loguru_logger.info(message)
        
        
    def debug(self, message: str) -> None:
        """
        Logs a debug message.

        Args:
            message (str): The message to log.
        """
        loguru_logger.debug(message)
        
    
    def warning(self, message: str) -> None:
        """
        Logs a warning message.

        Args:
            message (str): The message to log.
        """
        loguru_logger.warning(message)
        
        
    def error(self, message: str) -> None:
        """
        Logs an error message.

        Args:
            message (str): The message to log.
        """
        loguru_logger.error(message)
        
        
    def exception(self, message: str) -> None:
        """
        Logs an exception message.

        Args:
            message (str): The message to log.
        """
        loguru_logger.exception(message)


# Singleton instance
logger = Logger()