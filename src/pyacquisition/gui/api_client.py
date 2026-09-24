import json
import queue
import threading
import time
from dataclasses import dataclass
import requests
from websockets.exceptions import ConnectionClosed
from websockets.sync.client import connect
from ..core.logging import logger


@dataclass
class Reply:
    """
    What came back from a request, or why nothing did.

    Attributes:
        ok (bool): Whether the server answered without an error.
        data: The decoded JSON of the answer, if it had any.
        error (str | None): What went wrong, in words, if `ok` is false.
        status_code (int | None): The HTTP status, if the server answered.
        elapsed (float): How long it took, in seconds.
    """

    ok: bool
    data: object = None
    error: str | None = None
    status_code: int | None = None
    elapsed: float = 0.0


def describe_error(status_code: int, body) -> str:
    """
    Say what an error response means. FastAPI reports a bad input as a list of
    problems, each with the name of the input, and other errors as a single message.

    Args:
        status_code (int): The HTTP status.
        body: The decoded JSON of the response, or its text if it was not JSON.
    """
    detail = body.get("detail") if isinstance(body, dict) else None
    if isinstance(detail, list):
        problems = []
        for problem in detail:
            if not isinstance(problem, dict):
                problems.append(str(problem))
                continue
            where = [str(part) for part in problem.get("loc", ())]
            name = where[-1] if where and where[0] in ("query", "path") else ""
            message = problem.get("msg", "invalid")
            problems.append(f"{name}: {message}" if name else message)
        return "\n".join(problems)
    if isinstance(detail, str):
        return detail
    if status_code >= 500:
        return f"The server had an error handling the request (HTTP {status_code})."
    return f"HTTP {status_code}: {str(body)[:200]}"


class _Source:
    """
    Base class for anything that receives data from the FastAPI server.

    A worker thread does the blocking network I/O and puts each decoded message on
    a thread-safe queue. The GUI thread calls `dispatch` once per frame, which
    drains the queue and runs the callbacks. This keeps every DearPyGui call on
    the thread that owns the render loop.
    """

    def __init__(self, name: str, url: str, params: dict = None) -> None:
        self.name = name
        self.url = url
        self.params = params if params else {}
        self._queue = queue.Queue()
        self._callbacks = []
        self._stop_event = threading.Event()
        self._thread = None

    def add_callback(self, callback: callable) -> None:
        """
        Adds a callback to be called (on the GUI thread) with each message.

        Args:
            callback (callable): The callback function to add.
        """
        self._callbacks.append(callback)

    def start(self) -> None:
        """
        Starts the worker thread.
        """
        self._thread = threading.Thread(
            target=self._run, name=f"{type(self).__name__}-{self.name}", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        """
        Asks the worker thread to stop.
        """
        self._stop_event.set()

    def dispatch(self) -> None:
        """
        Runs the callbacks for every message received since the last call.
        Must be called from the GUI thread.
        """
        while True:
            try:
                message = self._queue.get_nowait()
            except queue.Empty:
                return
            for callback in self._callbacks:
                try:
                    callback(message)
                except Exception as e:
                    logger.error(f"Error in {self.name} callback: {e}")

    def _run(self) -> None:
        raise NotImplementedError


class Stream(_Source):
    """
    A class for receiving messages from a websocket endpoint.
    """

    RECONNECT_DELAY = 1.0
    RECV_TIMEOUT = 0.5

    def _run(self) -> None:
        """
        Connects to the websocket and queues messages as they arrive,
        reconnecting if the connection is lost.
        """
        while not self._stop_event.is_set():
            try:
                with connect(self.url) as websocket:
                    while not self._stop_event.is_set():
                        try:
                            message = websocket.recv(timeout=self.RECV_TIMEOUT)
                        except TimeoutError:
                            continue
                        self._queue.put(json.loads(message))
            except ConnectionClosed:
                logger.debug("WebSocket connection closed")
            except Exception as e:
                logger.error(f"Error in WebSocket connection: {e}")
            self._stop_event.wait(self.RECONNECT_DELAY)


class Poller(_Source):
    """
    A class for polling an API endpoint at a fixed period.
    """

    def __init__(
        self, name: str, url: str, params: dict = None, period: float = 1.0
    ) -> None:
        """
        Initializes the Poller with the specified name and URL.

        Args:
            name (str): The name of the poller.
            url (str): The URL to poll.
            params (dict, optional): Query parameters to include in the request.
            period (float, optional): The time interval between requests in seconds.
        """
        super().__init__(name, url, params)
        self.period = period

    def _run(self) -> None:
        """
        Repeatedly polls the endpoint and queues the response.
        """
        with requests.Session() as session:
            while not self._stop_event.is_set():
                try:
                    response = session.get(
                        self.url, params=self.params, timeout=self.period + 5
                    )
                    self._queue.put(response.json())
                except Exception as e:
                    logger.error(f"Error in Poller run: {e}")
                self._stop_event.wait(self.period)


class APIClient:
    """
    A class for facilitating the communication with the FastAPI
    server presented by the main process.
    """

    def __init__(self, host: str = "localhost", port: int = 8000) -> None:
        """
        Initializes the APIClient with the specified host and port.

        Args:
            host (str): The hostname of the FastAPI server.
            port (int): The port number of the FastAPI server.
        """
        self.host = host
        self.port = port
        self.streams = {}
        self.pollers = {}
        # The client is pickled with the Gui, when it is sent to the GUI process, and a
        # queue cannot be pickled. So it is made when the first request is sent.
        self._replies = None

    def start(self) -> None:
        """
        Starts the worker threads of all streams and pollers.
        """
        for source in [*self.streams.values(), *self.pollers.values()]:
            source.start()

    def stop(self) -> None:
        """
        Asks the worker threads of all streams and pollers to stop.
        """
        for source in [*self.streams.values(), *self.pollers.values()]:
            source.stop()

    def dispatch(self) -> None:
        """
        Runs the callbacks for all data received since the last call.
        Call once per frame from the GUI thread.
        """
        for source in [*self.streams.values(), *self.pollers.values()]:
            source.dispatch()

        while self._replies is not None:
            try:
                callback, reply = self._replies.get_nowait()
            except queue.Empty:
                return
            try:
                callback(reply)
            except Exception as e:
                logger.error(f"Error in a request callback: {e}")

    def add_stream(self, name: str, url: str) -> Stream:
        """
        Adds a new stream to the APIClient.

        Args:
            name (str): The name of the stream to add.
            url (str): The websocket endpoint to connect to (e.g., '/ws').
        """
        full_url = f"ws://{self.host}:{self.port}{url}"
        self.streams[name] = Stream(name, full_url)
        return self.streams[name]

    def add_poller(
        self, name: str, url: str, params: dict = None, period: float = 1.0
    ) -> Poller:
        """
        Adds a new poller to the APIClient.

        Args:
            name (str): The name of the poller to add.
            url (str): The URL to poll.
            params (dict, optional): Query parameters to include in the request.
            period (float, optional): The time interval between requests in seconds.
        """
        full_url = f"http://{self.host}:{self.port}{url}"
        self.pollers[name] = Poller(name, full_url, params, period)
        return self.pollers[name]

    def get_async(
        self,
        endpoint: str,
        callback: callable,
        params: dict = None,
        timeout: float = 30.0,
    ) -> None:
        """
        Sends a GET request without waiting for it, so a slow instrument cannot
        freeze the GUI.

        The request is made on a worker thread. `callback` is called with a `Reply`
        on the GUI thread, from `dispatch`, whether the request worked or not.

        Args:
            endpoint (str): The API endpoint to send the request to.
            callback (callable): Called with the `Reply`.
            params (dict, optional): The query parameters to include in the request.
            timeout (float, optional): Give up after this many seconds.
        """
        url = f"http://{self.host}:{self.port}{endpoint}"
        if self._replies is None:
            self._replies = queue.Queue()
        replies = self._replies

        def work() -> None:
            replies.put((callback, self._request(url, params, timeout)))

        threading.Thread(target=work, name=f"GET {endpoint}", daemon=True).start()

    @staticmethod
    def _request(url: str, params: dict | None, timeout: float) -> Reply:
        """Make a request, and report how it went. It never raises."""
        started = time.monotonic()
        try:
            response = requests.get(url, params=params, timeout=timeout)
            try:
                body = response.json()
            except ValueError:
                body = response.text
            elapsed = time.monotonic() - started
            if response.ok:
                return Reply(True, body, None, response.status_code, elapsed)
            error = describe_error(response.status_code, body)
            return Reply(False, body, error, response.status_code, elapsed)
        except requests.Timeout:
            error = f"No answer after {timeout:g} s."
        except requests.ConnectionError:
            error = "Could not reach the experiment. Is it still running?"
        except Exception as e:
            error = str(e)
        return Reply(False, None, error, None, time.monotonic() - started)

    def get(
        self,
        endpoint: str,
        params: dict = None,
        callback: callable = None,
        timeout: float | None = None,
    ) -> dict:
        """
        Sends a GET request to the specified endpoint with optional parameters.

        Args:
            endpoint (str): The API endpoint to send the request to.
            params (dict, optional): The query parameters to include in the request.
            timeout (float, optional): Give up after this many seconds. By default
                it waits for as long as it takes.

        Returns:
            dict: The JSON response from the server.
        """
        logger.debug(f"GET request to {endpoint} with params {params}")
        response = requests.get(
            f"http://{self.host}:{self.port}{endpoint}",
            params=params,
            timeout=timeout,
        )
        logger.debug(f"Response: {response.json()}")
        data = response.json()
        if callback:
            callback(data)
        return data
