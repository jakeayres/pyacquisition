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
import inspect
import tomllib
import typing
from enum import Enum
from pathlib import Path

from fastapi import BackgroundTasks, Body, Query, Request
from fastapi.responses import JSONResponse

from ..gui import UI_PATH, Gui
from ..gui import mount as serve_gui
from ..instruments import instrument_map
from . import calculations, config_check, config_writer, settings
from .adapters import ADAPTERS, open_resource
from .api_server import APIServer
from .instrument import SoftwareInstrument, _allows_text, enum_classes, resolve_enum_kwargs
from .task_manager.inputs import _enum_choices
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
        GET /setup/describe: what a config can hold: the options, the drivers
            and their queries, the calculations, and the adapters.
        GET /setup/config: the file's path, whether it exists, its config, and
            why the last Run stopped before the experiment started (or null).
        POST /setup/check: a config's problems, and the file it would write.
        POST /setup/save: writes a config with no problems to the file.
        POST /setup/test: asks an instrument at an address for `*IDN?`, and
            whether its reply is its driver's.
        POST /setup/run: starts handing over to the experiment, and stops the
            server. Answers with the port the experiment will listen on.
        GET /setup/shutdown: stops the server, when the window closes.
        GET /setup/drivers/<driver>/<query>: a query's arguments, checked and
            as a config holds them. Its schema gives the page its form.
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

    def _text(self) -> str | None:
        """The file's text, if it exists."""
        return config_writer.read_text(self.path) if self.path.exists() else None

    def check(self, config) -> dict:
        """A config's `problems` (as JSON), and the `toml` that saving it would
        write, or None if it can't be written."""
        found = config_check.problems(config)
        toml = None
        if isinstance(config, dict):
            try:
                toml = config_writer.render(config, self._text())
            except (config_writer.ConfigWriteError, TypeError, ValueError) as e:
                found.append(config_check.Problem((), f"The file can't be written: {e}"))
        return {"problems": [p.to_json() for p in found], "toml": toml}

    def _register_endpoints(self) -> None:
        app = self.app

        @app.get("/setup/describe", tags=["setup"])
        async def setup_describe():
            """
            Endpoint for what a config can hold: the `options` (each with its
            section, key, default, help and kind), the `drivers` (each with
            whether it is `hardware` and its `queries`, which are what can be
            measured, with the first line of each one's docstring), the
            `calculations` (each with the keys it takes and their kinds), and
            the `adapters`.
            """
            return {"status": 200, "data": describe()}

        @app.post("/setup/check", tags=["setup"])
        async def setup_check(config: dict = Body(...)):
            """
            Endpoint that checks a config, given as JSON in the shape a TOML
            file reads as, without opening an instrument. Answers with its
            `problems` (each with `where`, the keys that lead to it, and a
            `message`), and the `toml` that saving it would write, keeping the
            file's comments.
            """
            return {"status": 200, "data": self.check(config)}

        @app.post("/setup/save", tags=["setup"])
        async def setup_save(config: dict = Body(...)):
            """
            Endpoint that writes a config, given as JSON, to the file, keeping
            its comments. A config with problems is refused (422), with them.
            """
            checked = self.check(config)
            if checked["problems"]:
                return JSONResponse(status_code=422, content={"status": 422, "data": checked})
            config_writer.write(self.path, config)
            logger.info(f"[Setup] Saved {self.path}")
            return {"status": 200, "data": checked}

        @app.post("/setup/test", tags=["setup"])
        def setup_test(instrument: dict = Body(...)):
            """
            Endpoint that opens an instrument's address, asks `*IDN?`, and
            closes it, without making the driver (which would send its setup
            commands). Given `instrument` (the driver's name), `adapter`,
            `resource` and `args`, as a config holds them. Answers with the
            `reply` (or null), whether it `matches` the driver's identity (null
            when it has none), the `expected` words, the words `missing` from the
            reply, and the `error` if it couldn't be asked.
            """
            return {
                "status": 200,
                "data": test_instrument(
                    instrument.get("instrument"),
                    instrument.get("adapter"),
                    instrument.get("resource"),
                    instrument.get("args") or {},
                ),
            }

        for driver, cls in instrument_map.items():
            for name, query in config_check.queries(cls).items():
                app.add_api_route(
                    f"/setup/drivers/{driver}/{name}",
                    _driver_route(query),
                    methods=["GET"],
                    tags=["setup drivers"],
                )

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


def test_instrument(driver, adapter, resource, args: dict) -> dict:
    """Asks the instrument at an address for `*IDN?` (see `/setup/test`)."""
    from .discovery import identities
    from ..verify.spec import missing_words

    expected = identities().get(driver)
    answer = {
        "reply": None,
        "matches": None,
        "expected": list(expected) if expected else None,
        "missing": [],
        "error": None,
    }
    if not isinstance(resource, str) or not resource or not isinstance(adapter, str):
        answer["error"] = "It needs an adapter and an address to test."
        return answer
    try:
        opened = open_resource(resource, adapter, **args)
    except Exception as e:  # noqa: BLE001 - whatever it was, it is shown
        answer["error"] = str(e)
        return answer
    try:
        answer["reply"] = str(opened.query("*IDN?")).strip()
    except Exception as e:  # noqa: BLE001
        answer["error"] = f"It didn't answer *IDN?: {e}"
    finally:
        try:
            opened.close()
        except Exception:  # noqa: BLE001 - closing is best effort
            pass
    if expected and answer["reply"] is not None:
        answer["missing"] = missing_words(expected, answer["reply"])
        answer["matches"] = not answer["missing"]
    return answer


def describe() -> dict:
    """What a config can hold (see `/setup/describe`)."""

    def first_line(function) -> str:
        return (inspect.getdoc(function) or "").split("\n")[0]

    return {
        "options": settings.describe(),
        "drivers": [
            {
                "name": name,
                "hardware": not issubclass(cls, SoftwareInstrument),
                "queries": [
                    {"name": query, "doc": first_line(function)}
                    for query, function in sorted(config_check.queries(cls).items())
                ],
            }
            for name, cls in instrument_map.items()
        ],
        "calculations": [
            {"name": name, "keys": dict(cls.config_keys)}
            for name, cls in calculations.calculation_map.items()
        ],
        "adapters": list(ADAPTERS),
    }


def _driver_route(function):
    """A route with a query's arguments (without `self`) as its parameters,
    which answers with them as a config holds them: those given, checked, with
    an enum member by its name.

    As a task's inputs are (`task_manager/inputs.py`), an enum is asked for as
    text, with its members' names as the choices (`enum` in the schema) and
    their labels (`x-labels`), so the page's form holds names, as the file does.
    Other spellings are accepted too (`resolve_enum_kwargs`). A value that names
    no member is refused (422), by the argument, as FastAPI refuses the others.
    """
    signature = inspect.signature(function)
    try:
        hints = typing.get_type_hints(function)
    except Exception:  # noqa: BLE001 - left as they are, unresolved
        hints = {}
    parameters = []
    for parameter in list(signature.parameters.values())[1:]:
        hint = hints.get(parameter.name, parameter.annotation)
        enums = enum_classes(hint)
        default = parameter.default
        if enums and not _allows_text(hint):
            names, labels = _enum_choices(enums)
            hint = typing.Annotated[
                str, Query(json_schema_extra={"enum": names, "x-labels": labels})
            ]
            if isinstance(default, Enum):
                default = default.name
        parameters.append(
            parameter.replace(
                annotation=hint, default=default, kind=inspect.Parameter.KEYWORD_ONLY
            )
        )

    async def route(request: Request, **kwargs):
        given = {name: kwargs[name] for name in kwargs if name in request.query_params}
        refused = []
        for name, value in given.items():
            try:
                given[name] = resolve_enum_kwargs(function, {name: value})[name]
            except ValueError as e:
                refused.append({"loc": ["query", name], "msg": str(e), "type": "value_error"})
        if refused:
            return JSONResponse(status_code=422, content={"detail": refused})
        answer = {name: v.name if isinstance(v, Enum) else v for name, v in given.items()}
        return {"status": 200, "data": answer}

    route.__name__ = function.__name__
    route.__doc__ = function.__doc__
    request = inspect.Parameter(
        "request", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=Request
    )
    route.__signature__ = signature.replace(
        parameters=[request, *parameters], return_annotation=dict
    )
    return route


def _run_experiment(path: Path, port: int, gui: Gui | None, window) -> str | None:
    """Builds the experiment from the file and runs it in the window, until it
    stops. With no window (`gui` None), it runs with none of its own either.

    Returns:
        str | None: Why it stopped before it started, or None if it started.
    """
    from .experiment import Experiment

    overrides = {"api_server_port": port}
    if gui is None:
        overrides["gui"] = False
    try:
        experiment = Experiment.from_config(str(path), **overrides)
    except Exception as e:  # noqa: BLE001 - any failure is shown on the page
        return str(e)
    if gui is not None:
        experiment._adopt_gui(gui, window)
    experiment.run()
    if experiment._started or isinstance(experiment._error, KeyboardInterrupt):
        return None
    return str(experiment._error or "The experiment stopped before it started.")


def open_setup(path: str | Path, port: int | None = None, window: bool = True) -> None:
    """Shows the setup page for a config file in a window, until it closes, and
    runs the experiment in the same window when the page's Run button is
    pressed. `pyacquisition new CONFIG` calls it.

    Args:
        path: The config file.
        port (int | None): The port for the setup server, and for the
            experiment Run starts. By default, the one the file gives, or 8000.
        window (bool): Whether to show it in a window. Without one (for the
            browser tests), it runs until `/setup/shutdown`, or until the
            experiment that Run starts stops, which has no window either.
    """
    logger.configure(console_level="INFO", file_level=None, gui_level="NONE")
    path = Path(path)
    gui = Gui(page=SETUP_PAGE) if window else None
    process = None
    error = None
    try:
        while True:
            server = SetupServer(path, port=port, gui=gui, error=error)
            port = server.bind()  # the same port each time round, once had
            if gui is not None:
                gui.host, gui.port = server.host, port
                if process is None:
                    process = gui.run_in_new_process()
                    process.start()
                else:
                    gui.end_handover()  # back from an experiment that didn't start
            logger.info(
                f"[Setup] The setup page is at http://localhost:{port}{SETUP_PAGE}"
            )
            if not server.run(process):
                return  # the window closed
            error = _run_experiment(path, port, gui, process)
            if error is None:
                return  # it ran, and has stopped, and its window with it
            logger.error(f"[Setup] The experiment didn't start: {error}")
    except KeyboardInterrupt:
        logger.info("[Setup] Interrupted by user")
    finally:
        if process is not None:
            gui.close()
            process.join(timeout=5)
            if process.is_alive():
                process.terminate()
