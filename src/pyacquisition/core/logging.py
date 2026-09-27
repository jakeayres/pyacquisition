from loguru import logger as loguru_logger
from threading import Lock
from collections import deque
import sys
import time
from pathlib import Path
from .broadcaster import Broadcaster

# How many of the latest broadcast messages the logger keeps, so a listener that
# starts late (the GUI's log history, see core/log_history.py) can catch up.
RECENT_MESSAGES = 5000


class Logger(Broadcaster):
    """
    Singleton class for configuring and managing logging in the application.
    """

    LOG_LEVELS = {
        "TRACE": 5,
        "DEBUG": 10,
        "INFO": 20,
        "WARNING": 30,
        "ERROR": 40,
        "EXCEPTION": 50,
        "NONE": 100,
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
        loguru_logger.remove()
        super().__init__()
        self._initialized = True
        self._gui_level = "NONE"
        self.sent = 0  # the number of messages broadcast so far
        self._recent = deque(maxlen=RECENT_MESSAGES)  # (number, message)
        self._sinks = []  # the loguru handlers added by the last `configure`

    def _should_broadcast(self, level: str) -> bool:
        return (
            self.LOG_LEVELS[level.upper()] >= self.LOG_LEVELS[self._gui_level.upper()]
        )

    def _send(self, level: str, message: str) -> None:
        """Keeps the message among the recent ones, and broadcasts it."""
        sent = {"time": time.time(), "message": message, "level": level}
        self.sent += 1
        self._recent.append((self.sent, sent))
        self.broadcast_sync(sent)

    def recent_since(self, number: int) -> list[dict]:
        """The messages broadcast after the one numbered `number` (as `sent` was
        then), as far back as they are still kept."""
        return [message for n, message in self._recent if n > number]

    def configure(
        self,
        root_path: Path | None = None,
        console_level: str | None = "DEBUG",
        file_level: str | None = "DEBUG",
        gui_level: str | None = "DEBUG",
        file_name: Path | None = Path("debug.log"),
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

        # Configuring again replaces the console and file output, rather than
        # adding to them. (Each experiment configures the logger, and each sink
        # has a thread of its own, so a process that made many experiments, as
        # the tests do, wrote every message hundreds of times over.)
        for sink in self._sinks:
            loguru_logger.remove(sink)
        self._sinks = []

        if console_level is not None:
            self._sinks.append(
                loguru_logger.add(
                    sink=sys.stdout,
                    colorize=True,
                    level=console_level,
                    enqueue=True,
                    # format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}",
                )
            )

        if file_level is not None:
            log_file_path = root_path / file_name
            self._sinks.append(
                loguru_logger.add(
                    sink=log_file_path,
                    level=file_level,
                    format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}",
                    enqueue=True,
                )
            )
        else:
            log_file_path = None
        self.debug(f"Log file path: {log_file_path}")

        self.info(
            f"Logging configured: console level={console_level}, file level={file_level}, file name={log_file_path}, gui level={self._gui_level}"
        )

    def flush(self) -> None:
        """Waits until every message so far is written to the console and the
        log file, which happens on a thread of their own."""
        loguru_logger.complete()

    def info(self, message: str) -> None:
        """
        Logs an info message.

        Args:
            message (str): The message to log.
        """
        loguru_logger.info(message)
        if self._should_broadcast("INFO"):
            self._send("info", message)

    def debug(self, message: str) -> None:
        """
        Logs a debug message.

        Args:
            message (str): The message to log.
        """
        loguru_logger.debug(message)
        if self._should_broadcast("DEBUG"):
            self._send("debug", message)

    def trace(self, message: str) -> None:
        """
        Logs a trace message.

        Args:
            message (str): The message to log.
        """
        loguru_logger.trace(message)
        if self._should_broadcast("TRACE"):
            self._send("trace", message)

    def warning(self, message: str) -> None:
        """
        Logs a warning message.

        Args:
            message (str): The message to log.
        """
        loguru_logger.warning(message)
        if self._should_broadcast("WARNING"):
            self._send("warning", message)

    def error(self, message: str) -> None:
        """
        Logs an error message.

        Args:
            message (str): The message to log.
        """
        loguru_logger.error(message)
        if self._should_broadcast("ERROR"):
            self._send("error", message)

    def exception(self, message: str) -> None:
        """
        Logs an exception message.

        Args:
            message (str): The message to log.
        """
        loguru_logger.exception(message)
        if self._should_broadcast("EXCEPTION"):
            self._send("exception", message)


# Singleton instance
logger = Logger()
