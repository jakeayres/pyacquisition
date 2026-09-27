"""The setup page: `pyacquisition new CONFIG`.

A small server, with no experiment behind it, serves a page on which an
experiment's TOML config is built, and the usual window shows it. The page's
Run button starts the experiment from the file in the same process, and the
window is handed over to it without closing:

1. `/setup/run` tells the window a handover has started (`Gui.start_handover`),
   and the setup server stops, which lets go of its port.
2. `Experiment.from_config(CONFIG)` is built and run with the window already
   open (`Experiment._adopt_gui`). It listens on the same port, and moves the
   window to its own address once `setup()` has run (`Gui.end_handover`).
3. The page, told the port by `/setup/run`, goes to the experiment's page once
   the experiment answers.

If the experiment stops before it starts, such as for a mistake in the file, the
setup server starts again, on the same port and file, and the page shows why.
"""

import asyncio
import tomllib
from pathlib import Path

from fastapi import BackgroundTasks

from ..gui import UI_PATH, Gui
from ..gui import mount as serve_gui
from . import settings
from .api_server import APIServer
from .logging import logger

# The setup page's path. `/` is sent here.
SETUP_PAGE = f"{UI_PATH}/setup/"


def _read(path: Path) -> dict:
    """The config in `path`, as `tomllib` reads it, or {} if it can't be read."""
    try:
        with open(path, "rb") as file:
            return tomllib.load(file)
    except (OSError, tomllib.TOMLDecodeError):
        return {}


def _ports(config: dict) -> tuple[int, tuple[int, ...]]:
    """The port the config's experiment listens on, and its fallback ports: as
    the file sets them, or the defaults if it sets none or can't be read."""
    port = settings.SETTINGS["api_server_port"]
    fallbacks = settings.SETTINGS["api_server_fallback_ports"]
    try:
        options = settings.from_config(config)
        wanted = port.check(port.name, options.get(port.name, port.default))
        others = fallbacks.check(
            fallbacks.name, options.get(fallbacks.name, fallbacks.default)
        )
    except ValueError:
        return port.default, fallbacks.default
    return wanted, others


class SetupServer:
    """Serves the setup page for one config file, with no experiment.

    Endpoints:
        GET /setup/config: the file's path, whether it exists, its config, and
            why the last Run stopped before the experiment started (or null).
        POST /setup/run: starts handing over to the experiment, and stops the
            server. Answers with the port the experiment will listen on.
        GET /setup/shutdown: stops the server, when the window closes.
    """

    def __init__(
        self,
        path: str | Path,
        host: str = "localhost",
        port: int | None = None,
        gui: Gui | None = None,
        error: str | None = None,
    ):
        """
        Args:
            path: The config file.
            host (str): The address to listen on.
            port (int | None): The port to listen on. By default, the one the file
                gives its experiment, or 8000. The file's fallback ports are tried
                if it is taken, as the experiment tries them.
            gui (Gui | None): The window, which Run hands over.
            error (str | None): Why the last Run stopped before the experiment
                started, to show on the page.
        """
        self.path = Path(path)
        wanted, fallbacks = _ports(_read(self.path))
        self._api_server = APIServer(
            host=host, port=port or wanted, fallback_ports=fallbacks
        )
        self._gui = gui
        self.error = error
        self.run_asked = False  # whether Run was pressed, once the server stops

        serve_gui(self.app, start=SETUP_PAGE)
        self._api_server._register_endpoints(self._api_server)  # /ping
        self._register_endpoints()

    @property
    def app(self):
        """The FastAPI app."""
        return self._api_server.app

    @property
    def host(self) -> str:
        return self._api_server.host

    @property
    def port(self) -> int:
        """The port, which is the one it listens on once `bind` has run."""
        return self._api_server.port

    def bind(self) -> int:
        """Claims the port, as `APIServer.bind` does, and returns it."""
        return self._api_server.bind()

    def run(self, window=None) -> bool:
        """Serves until the server is stopped, or `window` (a process) ends.

        Returns:
            bool: Whether it stopped for Run, rather than to close.
        """
        asyncio.run(self.serve(window))
        return self.run_asked

    async def serve(self, window=None) -> None:
        """A coroutine that serves until the server is stopped, or `window` (a
        process) ends."""
        async with asyncio.TaskGroup() as group:
            server = group.create_task(self._api_server.run())
            if window is not None:
                group.create_task(self._watch(window, server))

    async def stop(self) -> None:
        """Stops the server, after a moment for the answer in hand to go out."""
        await self._api_server.shutdown()

    async def _watch(self, window, server: asyncio.Task, period: float = 0.25) -> None:
        """Stops the server if the window's process ends."""
        while not server.done():
            if not window.is_alive():
                logger.info("[Setup] The window has closed")
                await self.stop()
                return
            await asyncio.wait({server}, timeout=period)

    def _config(self) -> dict:
        return {
            "path": str(self.path.resolve()),
            "exists": self.path.exists(),
            "config": _read(self.path),
            "error": self.error,
        }

    def _register_endpoints(self) -> None:
        app = self.app

        @app.get("/setup/config", tags=["setup"])
        async def setup_config():
            """
            Endpoint for the config file: its `path`, whether it `exists`, its
            `config` as JSON (`{}` for a file that doesn't exist, or can't be
            read), and the `error` that stopped the last Run, or null.
            """
            return {"status": 200, "data": self._config()}

        @app.post("/setup/run", tags=["setup"])
        async def setup_run(background: BackgroundTasks):
            """
            Endpoint that starts the experiment from the file. The window is
            handed over to it, and this server stops. Answers with the `port`
            the experiment will listen on, whose page the setup page then opens.
            """
            logger.info(f"[Setup] Starting the experiment from {self.path}")
            self.run_asked = True
            self.error = None  # so the page can tell a new one from the last
            if self._gui is not None:
                self._gui.start_handover()
            background.add_task(self.stop)
            return {"status": 200, "data": {"port": self.port}}

        @app.get("/setup/shutdown", tags=["setup"])
        async def setup_shutdown(background: BackgroundTasks):
            """
            Endpoint that stops the setup server, when its window closes.
            """
            background.add_task(self.stop)
            return {"status": 200, "data": None}


def _run_experiment(path: Path, port: int, gui: Gui, window) -> str | None:
    """Builds the experiment from the file and runs it in the window, until it
    stops.

    Returns:
        str | None: Why it stopped before it started, or None if it started.
    """
    from .experiment import Experiment

    try:
        experiment = Experiment.from_config(str(path), api_server_port=port)
    except Exception as e:  # noqa: BLE001 - any failure is shown on the page
        return str(e)
    experiment._adopt_gui(gui, window)
    experiment.run()
    if experiment._started or isinstance(experiment._error, KeyboardInterrupt):
        return None
    return str(experiment._error or "The experiment stopped before it started.")


def open_setup(path: str | Path, port: int | None = None) -> None:
    """Shows the setup page for a config file in a window, until it closes, and
    runs the experiment in the same window when the page's Run button is
    pressed. `pyacquisition new CONFIG` calls it.

    Args:
        path: The config file.
        port (int | None): The port for the setup server, and for the
            experiment Run starts. By default, the one the file gives, or 8000.
    """
    logger.configure(console_level="INFO", file_level=None, gui_level="NONE")
    path = Path(path)
    gui = Gui(page=SETUP_PAGE)
    window = None
    error = None
    try:
        while True:
            server = SetupServer(path, port=port, gui=gui, error=error)
            port = server.bind()  # the same port each time round, once had
            gui.host, gui.port = server.host, port
            if window is None:
                window = gui.run_in_new_process()
                window.start()
            else:
                gui.end_handover()  # back from an experiment that didn't start
            logger.info(f"[Setup] The setup page is at {gui.server}{SETUP_PAGE}")
            if not server.run(window):
                return  # the window closed
            error = _run_experiment(path, port, gui, window)
            if error is None:
                return  # it ran, and has stopped, and its window with it
            logger.error(f"[Setup] The experiment didn't start: {error}")
    except KeyboardInterrupt:
        logger.info("[Setup] Interrupted by user")
    finally:
        if window is not None:
            gui.close()
            window.join(timeout=5)
            if window.is_alive():
                window.terminate()
