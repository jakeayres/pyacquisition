"""The GUI: a web page served by the experiment's own API server, shown in a
native window by pywebview.

It runs unless the experiment option `gui` is False, and can be opened in a
browser either way. It replaced the classic Dear PyGui interface, following the
plan in `specs/archive/new-gui.md`, in the repository. (`gui = "new"`, from while
both existed, is accepted as the same as True.)
"""

import ctypes
import mimetypes
import multiprocessing
from multiprocessing import Process
from pathlib import Path

from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from . import window

STATIC_DIR = Path(__file__).parent / "static"
UI_PATH = "/ui"

# The type a file is served as comes from `mimetypes`, which on Windows reads the
# registry, and the registry can say that `.js` is `text/plain`. A browser refuses
# to run a module served as that, so the page would be blank.
mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("text/css", ".css")


class _FreshStaticFiles(StaticFiles):
    """Static files that the browser checks are current each time it uses them.

    Without this, a browser (the window's included) may keep using the page's
    scripts from its cache after pyacquisition is updated, and run old code. A
    check costs little: an unchanged file is answered with "304 Not Modified".
    """

    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-cache"
        return response


def mount(app, start: str = f"{UI_PATH}/") -> None:
    """Serves the pages at `/ui/`, and sends `/` to `start`.

    It is served whichever GUI the experiment runs, or none, so that the page can
    always be opened in a browser as well. The setup server (`core/setup.py`)
    serves the same files, and starts at its own page, `/ui/setup/`.
    """
    app.mount(UI_PATH, _FreshStaticFiles(directory=STATIC_DIR, html=True), name="ui")

    @app.get("/", include_in_schema=False)
    async def root():
        return RedirectResponse(start)


# The longest address the window can be moved to, in bytes.
ADDRESS_SIZE = 256


class Gui:
    """Starts the window that shows the page, in a process of its own.

    The window can be handed from one server to another while it stays open: the
    setup server (`pyacquisition new`) hands it to the experiment that its Run
    button starts. See `start_handover` and `end_handover`.
    """

    def __init__(
        self, host: str = "localhost", port: int = 8000, page: str = f"{UI_PATH}/"
    ):
        """
        Args:
            host (str): The host of the API server.
            port (int): The port of the API server.
            page (str): The path of the page the window opens.
        """
        # Pickled when it is sent to the new process, so it holds only plain data.
        self.host = host
        self.port = port
        self.page = page
        # Made with the process, as they cannot be pickled.
        self._closing = None
        self._address = None
        self._handing_over = None

    @property
    def server(self) -> str:
        """The address of the API server, as the window reaches it."""
        # A server listening on every interface is reached through this machine.
        host = "localhost" if self.host in ("", "0.0.0.0", "::") else self.host
        return f"http://{host}:{self.port}"

    def run_in_new_process(self) -> Process:
        """The process that shows the window. It is not started yet."""
        # A plain shared flag, which the window checks every so often. Not a
        # multiprocessing.Event: setting one waits for each process waiting on it
        # to wake, and a window that has closed and gone never does, so the
        # experiment would hang for ever as it shut down.
        self._closing = multiprocessing.RawValue(ctypes.c_bool, False)
        # The address the window follows, and whether it is being handed over.
        # Plain shared memory too, for the same reason. The address is only
        # written while the flag is set, and the window doesn't read it then, so
        # it is never read half written.
        self._address = multiprocessing.RawArray(ctypes.c_char, ADDRESS_SIZE)
        self._address.value = self.server.encode()
        self._handing_over = multiprocessing.RawValue(ctypes.c_bool, False)
        return Process(
            target=window.main,
            args=(self.server, self._closing, self._address, self._handing_over),
            kwargs={"page": self.page},
            name="pyacquisition-gui",
        )

    def start_handover(self) -> None:
        """Tells the window that its server is going away on purpose, and that
        another will take over at `end_handover`. Until then the window doesn't
        close when the server stops answering, but only if the process that
        started it ends."""
        if self._handing_over is not None:
            self._handing_over.value = True

    def end_handover(self) -> None:
        """Moves the window to the address that `host` and `port` now give, and
        ends the handover. The window then waits for that address to answer, as a
        new window waits for its experiment to start."""
        if self._handing_over is None:
            return
        address = self.server.encode()
        if len(address) >= ADDRESS_SIZE:
            raise ValueError(f"The address {self.server!r} is too long for the window")
        self._handing_over.value = True  # so the window never reads it half written
        self._address.value = address
        self._handing_over.value = False

    def close(self) -> None:
        """Tells the window to close now, as the experiment is shutting down.

        It never waits, even if the window has already gone. Without it, the
        window only notices the experiment has gone when it stops answering,
        which on Windows can take several seconds.
        """
        if self._closing is not None:
            self._closing.value = True
