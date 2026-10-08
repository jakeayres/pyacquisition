"""The process that shows the GUI in a native window.

The window and the experiment live and die together:

- Closing the window asks first, in the page, and stops the experiment if you
  confirm. Cancelling leaves both running.
- If the experiment stops, it tells the window to close. If its process ends
  without saying (a crash), the window closes by itself once it notices, so that
  it is never left open with nothing behind it.
- An experiment that is running but not answering keeps its window. One waiting
  on an instrument that doesn't reply (a GPIB read that times out blocks it for
  seconds) carries on afterwards, and closing the window would stop it. The page
  says that it isn't answering, and catches up when it does.
- If this process ends any other way, the experiment notices and shuts down (see
  `Experiment._watch_gui`).

The window can also be handed from one server to another without closing: the
setup page (`pyacquisition new`) hands it to the experiment its Run button
starts. While a handover is under way the window waits, as long as the process
that started it is alive, and then follows the new address (see `gui.Gui`).
"""

import json
import multiprocessing
import os
import signal
import subprocess
import sys
import threading
import urllib.request

TITLE = "PyAcquisition"
PING_PERIOD = 0.5  # seconds between checks that the experiment is still there
TOLD_CHECK_PERIOD = 0.1  # seconds between checks that the experiment said to close

# Set to show the browser's developer tools in the window.
DEBUG_VARIABLE = "PYACQUISITION_GUI_DEBUG"

# What the page is asked to do when the window's close button is pressed. It gives
# `true` if it has shown its warning, and anything else if it cannot.
_REQUEST_CLOSE = (
    "window.pyacquisition && window.pyacquisition.requestClose"
    " ? window.pyacquisition.requestClose() : false"
)


# The window's colour before the page paints, so it does not flash white in the
# dark theme. The same as `--bg` in static/css/tokens.css.
BACKGROUND = {"light": "#f4f5f7", "dark": "#0e1014"}


# Where the WebView2 Runtime can be installed from (Microsoft's "Evergreen
# Bootstrapper").
WEBVIEW2_DOWNLOAD = "https://go.microsoft.com/fwlink/p/?LinkId=2124703"


def needs_webview2() -> bool:
    """Whether the window would be shown by Internet Explorer's engine, which
    can't run the page: pywebview falls back to it on Windows without the
    Microsoft Edge WebView2 Runtime (Windows 11 has it, and so does Windows 10
    with a current Edge). Elsewhere, False."""
    if sys.platform != "win32":
        return False
    # An engine chosen through pywebview's own setting is the one used. (Its
    # Windows module reads the setting only if imported after `webview.start`.)
    forced = os.environ.get("PYWEBVIEW_GUI", "").lower()
    if forced:
        return forced == "mshtml"
    try:
        from webview.platforms import winforms
    except Exception:  # noqa: BLE001 - it can't tell, and pywebview says why itself
        return False
    return winforms.renderer == "mshtml"


def webview2_notice(server: str, theme: str) -> str:
    """The page shown instead, saying what to install, and that the experiment
    runs regardless and can be seen in a browser."""
    background = BACKGROUND[theme]
    text = "#e6e8eb" if theme == "dark" else "#1d2127"
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>{TITLE}</title></head>
<body style="margin:0;padding:48px;background:{background};color:{text};
  font-family:'Segoe UI',sans-serif;font-size:14px;line-height:1.5">
  <h1 style="font-size:18px;font-weight:600;margin:0 0 12px">
    This window needs the Microsoft Edge WebView2 Runtime</h1>
  <p>The experiment is running, but this PC can't show its window without the
    runtime. Install it from Microsoft, then start the experiment again:</p>
  <p style="font-family:Consolas,monospace;user-select:all">{WEBVIEW2_DOWNLOAD}</p>
  <p>Until then, open this address in Edge, Chrome or Firefox to see it:</p>
  <p style="font-family:Consolas,monospace;user-select:all">{server}</p>
  <p>Closing this window stops the experiment.</p>
</body></html>"""


def system_theme() -> str:
    """The theme Windows is set to for apps, "dark" or "light". Elsewhere, "light"."""
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        ) as key:
            light, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        return "light" if light else "dark"
    except (ImportError, OSError):  # not Windows, or never set
        return "light"


def ping(server: str, timeout: float = 1.0) -> bool:
    """Whether the experiment's API server answers."""
    try:
        with urllib.request.urlopen(f"{server}/ping", timeout=timeout) as response:
            return response.status == 200
    except OSError:  # refused, timed out, or an HTTP error: it does not answer
        return False


def shutdown(server: str) -> None:
    """Asks the experiment to shut down. A failure means it has gone already."""
    try:
        urllib.request.urlopen(f"{server}/experiment/shutdown", timeout=5).close()
    except OSError:
        pass  # it has gone already, which is what was asked for


class _Api:
    """What the page can call, as `window.pywebview.api`."""

    def __init__(self, owner):
        self._owner = owner  # private, so pywebview does not expose it to the page

    def close(self):
        """Closes the window without asking. The page calls it once it has asked,
        and has stopped the experiment."""
        self._owner.close()

    def open_data_folder(self) -> bool:
        """Opens the experiment's data folder in the file manager. Returns whether
        it could."""
        return open_folder(data_folder(self._owner.server))

    def save_file(self, name: str, text: str | None = None, base64: str | None = None):
        """Asks where to save a file (starting in the data folder, as `name`),
        and saves it: `text`, or the bytes that `base64` holds (an image). The
        page calls it to export a plot, since the window doesn't download.
        Returns where it was saved, or None if the dialog was cancelled."""
        import base64 as b64

        suffix = os.path.splitext(name)[1].lower()
        kinds = {
            ".png": "PNG image (*.png)",
            ".csv": "CSV file (*.csv)",
            ".py": "Python script (*.py)",
        }
        chosen = ask_where_to_save(
            self._owner.window,
            directory=data_folder(self._owner.server) or "",
            save_filename=name,
            file_types=(kinds[suffix],) if suffix in kinds else (),
        )
        if not chosen:
            return None
        path = chosen if isinstance(chosen, str) else chosen[0]
        return save_to(path, text=text, data=None if base64 is None else b64.b64decode(base64))


def ask_where_to_save(window, **options):
    """Shows the Save dialog, on the window's own thread, and gives what it
    answers (a path, a tuple of one, or None if cancelled).

    The page's calls come on a thread of pywebview's own, and on Windows
    pywebview shows the dialog on the calling thread. That thread can't show
    Windows Forms dialogs, so the dialog never appeared and the call never
    returned. It is shown on the window's thread instead, when the window is
    one of pywebview's Windows Forms ones (its module is loaded then).
    """
    import webview

    def show():
        return window.create_file_dialog(webview.FileDialog.SAVE, **options)

    winforms = sys.modules.get("webview.platforms.winforms")
    view = winforms and winforms.BrowserView.instances.get(getattr(window, "uid", None))
    if view is None or not view.InvokeRequired:
        return show()
    answer = []
    view.Invoke(winforms.Func[winforms.Type](lambda: answer.append(show())))
    return answer[0] if answer else None


def save_to(path: str, text: str | None = None, data: bytes | None = None) -> str:
    """Writes text (UTF-8, as it is) or bytes to a file. Returns its path."""
    if data is not None:
        with open(path, "wb") as file:
            file.write(data)
    else:
        with open(path, "w", encoding="utf-8", newline="") as file:
            file.write(text or "")
    return path


def data_folder(server: str) -> str | None:
    """The experiment's data folder, as it says, so the page can't ask for any
    other folder to be opened."""
    try:
        with urllib.request.urlopen(f"{server}/scribe/current_directory", timeout=2) as r:
            return json.load(r)["data"]
    except Exception:  # noqa: BLE001 - gone, or not answering: nothing to open
        return None


def open_folder(path: str | None) -> bool:
    """Opens a folder in the system's file manager."""
    if not path or not os.path.isdir(path):
        return False
    try:
        if sys.platform == "win32":
            os.startfile(path)  # noqa: S606 - a folder the experiment writes to
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
        return True
    except OSError:
        return False


def parent_alive() -> bool:
    """Whether the process that started this one is still running."""
    parent = multiprocessing.parent_process()
    return parent is None or parent.is_alive()


class _Window:
    def __init__(self, server: str, address=None):
        """
        Args:
            server (str): The address of the server the window shows.
            address: A shared address (see `gui.Gui`) that replaces `server`, so
                that the window can be moved to another server.
        """
        self._server = server
        self._address = address
        self.window = None
        self._closing = threading.Event()  # set once the window may really close
        self._lock = threading.Lock()

    @property
    def server(self) -> str:
        """The address of the server the window shows now."""
        if self._address is None:
            return self._server
        return self._address.value.decode()

    def close(self) -> None:
        """Closes the window, once, whichever thread asks first."""
        with self._lock:
            if self._closing.is_set():
                return
            self._closing.set()
        self.window.destroy()

    def on_closing(self):
        """The window's close button. Returning False keeps the window open."""
        if self._closing.is_set():
            return True
        # This runs on the window's own thread, which must not wait on the page.
        threading.Thread(target=self._ask_to_close, daemon=True).start()
        return False

    def _ask_to_close(self) -> None:
        try:
            asked = self.window.evaluate_js(_REQUEST_CLOSE)
        except Exception:  # noqa: BLE001 - whatever failed, the page cannot ask
            asked = False
        if asked is True:
            return  # the page asks, and calls `close` if the answer is yes
        # The page cannot ask, because it has not loaded or has broken.
        if not ping(self.server):
            self.close()  # nothing is running, so there is nothing to warn about
        elif self.window.create_confirmation_dialog(
            "Stop the experiment?", "Closing this window stops the experiment."
        ):
            shutdown(self.server)
            self.close()

    def watch(self, told_to_close=None, handing_over=None) -> None:
        """Closes the window when the experiment says it is shutting down, or,
        if it goes without saying (a crash), once the process that started the
        window has ended. The experiment always runs in that process, whether
        it opened the window or took it over from the setup page.

        The window stays open while the experiment doesn't answer. It used to
        close after a few seconds of that, and so stopped experiments that were
        only waiting on an instrument that hadn't replied.

        Being told is watched for on a thread of its own, since a check that a
        new address answers can take a second to fail. `told_to_close` is a
        shared flag with a `value`, checked every so often rather than waited
        on (see Gui.run_in_new_process).

        While `handing_over` (a shared flag too) is set, the server is going
        away on purpose and another will take over. When the address changes,
        the window waits for the new one to answer, and then shows its page.
        (When the port stays the same, the address doesn't change, and the
        setup page moves to the experiment's page itself.)
        """
        if told_to_close is not None:

            def close_when_told():
                while not self._closing.is_set():
                    if told_to_close.value:
                        self.close()
                        return
                    self._closing.wait(TOLD_CHECK_PERIOD)

            threading.Thread(target=close_when_told, daemon=True).start()
        watched = self.server
        moved = False  # to show the new address's page once it answers
        while not self._closing.is_set():
            if not parent_alive():
                self.close()
                return
            if handing_over is None or not handing_over.value:
                if self.server != watched:
                    watched = self.server
                    moved = True
                if moved and ping(watched):
                    moved = False
                    self.window.load_url(f"{watched}/")  # sent on to its own page
            self._closing.wait(PING_PERIOD)


def main(
    server: str,
    told_to_close=None,
    address=None,
    handing_over=None,
    page: str = "/ui/",
) -> None:
    """Shows the page served at `server` until the window closes.

    Args:
        server (str): The address of the experiment's API server, such as
            `http://localhost:8000`.
        told_to_close (multiprocessing.RawValue | None): A shared flag that the
            experiment sets when it shuts down, so the window closes at once.
        address (multiprocessing.RawArray | None): The shared address the window
            follows, which starts as `server`.
        handing_over (multiprocessing.RawValue | None): A shared flag set while
            the window is being handed to another server.
        page (str): The path of the page to open.
    """
    import webview  # imported here, so that importing pyacquisition does not load it

    # Ctrl+C in the console reaches this process too. It is for the experiment,
    # which shuts down, and then this window closes because the experiment has gone.
    signal.signal(signal.SIGINT, signal.SIG_IGN)

    app = _Window(server, address)
    theme = system_theme()
    # Without the WebView2 Runtime the page can't run here: the window says so
    # instead of staying blank.
    shown = (
        {"html": webview2_notice(server, theme)}
        if needs_webview2()
        else {"url": f"{server}{page}"}
    )
    app.window = webview.create_window(
        TITLE,
        **shown,
        js_api=_Api(app),
        width=1600,
        height=900,
        min_size=(900, 600),
        background_color=BACKGROUND[theme],
    )
    app.window.events.closing += app.on_closing
    webview.start(
        app.watch,
        (told_to_close, handing_over),
        debug=bool(os.environ.get(DEBUG_VARIABLE)),
    )
