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


def mount(app) -> None:
    """Serves the page at `/ui/`, and sends `/` there.

    It is served whichever GUI the experiment runs, or none, so that the page can
    always be opened in a browser as well.
    """
    app.mount(UI_PATH, _FreshStaticFiles(directory=STATIC_DIR, html=True), name="ui")

    @app.get("/", include_in_schema=False)
    async def root():
        return RedirectResponse(f"{UI_PATH}/")


class Gui:
    """Starts the window that shows the page, in a process of its own."""

    def __init__(self, host: str = "localhost", port: int = 8000):
        """
        Args:
            host (str): The host of the API server.
            port (int): The port of the API server.
        """
        # Pickled when it is sent to the new process, so it holds only plain data.
        self.host = host
        self.port = port
        self._closing = None  # made with the process, as it cannot be pickled

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
        return Process(
            target=window.main,
            args=(self.server, self._closing),
            name="pyacquisition-gui",
        )

    def close(self) -> None:
        """Tells the window to close now, as the experiment is shutting down.

        It never waits, even if the window has already gone. Without it, the
        window only notices the experiment has gone when it stops answering,
        which on Windows can take several seconds.
        """
        if self._closing is not None:
            self._closing.value = True
