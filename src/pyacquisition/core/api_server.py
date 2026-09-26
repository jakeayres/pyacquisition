from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from websockets.exceptions import ConnectionClosed
import uvicorn
import inspect
import asyncio
import errno
import socket
import sys
from .logging import logger
from .consumer import Consumer
from . import windows_asyncio
from enum import Enum

# Clients that reset their connections (a browser window closing) must not leave
# tracebacks behind, or hold up the server's shutdown. See windows_asyncio.
windows_asyncio.install()


def enum_choices(message):
    """What the classic GUI expects: each enum in a dict of values becomes all of
    its enum's members, with the one it is marked as selected."""
    if not isinstance(message, dict):
        return message
    return {
        key: APIServer._enum_to_selected_dict(value) if isinstance(value, Enum) else value
        for key, value in message.items()
    }


class WebsocketEndpoint:
    """
    Streams what its sources broadcast to every client connected to it.

    Each connection has its own queue, subscribed to the sources when the client
    connects and unsubscribed when it leaves, so every client receives every
    message, and nothing piles up while no client is connected.
    """

    def __init__(self, encode=enum_choices):
        """
        Args:
            encode (callable): Turns a message into what is sent as JSON.
        """
        self._sources = []
        self._encode = encode
        self._shutdown_event = asyncio.Event()
        self.connections = 0  # clients connected now

    def subscribe_to(self, broadcaster) -> None:
        """Streams what `broadcaster` broadcasts, from now on, to each client."""
        self._sources.append(broadcaster)

    async def run(self, websocket: WebSocket):
        """
        Sends messages to one client until it leaves or the server shuts down.
        """
        await websocket.accept()
        consumer = Consumer(callbacks=[], async_callbacks=[])
        for source in self._sources:
            source.subscribe(consumer)
        self.connections += 1
        logger.debug("[FastApi] Client connected")

        # The client leaving is only seen by receiving, so that is watched as well,
        # in case nothing is being sent when it goes.
        left = asyncio.ensure_future(self._until_disconnected(websocket))
        try:
            while not left.done() and not self._shutdown_event.is_set():
                message = await consumer.consume(timeout=0.1)
                if message is not None:
                    await websocket.send_json(self._encode(message))
            if self._shutdown_event.is_set():
                logger.debug("[FastApi] Shutdown event set, closing WebSocket.")
                await websocket.close()
        except (WebSocketDisconnect, ConnectionClosed):
            logger.debug("[FastApi] Client disconnected")
        except Exception as e:
            if left.done():  # sending raced the client leaving
                logger.debug("[FastApi] Client disconnected")
            else:
                logger.error(f"[FastApi] An error occurred: {e}")
        finally:
            left.cancel()
            for source in self._sources:
                source.unsubscribe(consumer)
            self.connections -= 1

    @staticmethod
    async def _until_disconnected(websocket: WebSocket) -> None:
        while (await websocket.receive())["type"] != "websocket.disconnect":
            pass


class PortsUnavailable(OSError):
    """None of the ports the API server may use could be had."""


def bind_sockets(host: str, port: int) -> list[socket.socket]:
    """Sockets bound to `port` on every address `host` names, as asyncio's own
    `create_server` would bind them: "localhost" is both 127.0.0.1 and ::1, so
    another program on either one means the port can't be used. All of them are
    bound, or none: an address that can't be had closes those already bound, and
    raises.

    An address whose family the machine doesn't have (IPv6 turned off) is left
    out, as asyncio does.
    """
    infos = socket.getaddrinfo(
        host or None, port, type=socket.SOCK_STREAM, flags=socket.AI_PASSIVE
    )
    sockets = []
    try:
        seen = set()
        for family, kind, proto, _, address in infos:
            if (family, address) in seen:
                continue
            seen.add((family, address))
            try:
                sock = socket.socket(family, kind, proto)
            except OSError:
                continue  # a family this machine doesn't have
            sockets.append(sock)
            if sys.platform != "win32":
                # As asyncio does: a port left in TIME_WAIT by the last run can
                # be used again at once. (On Windows it would let another program
                # take a port in use, and a restart works there without it.)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if family == socket.AF_INET6:
                sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
            try:
                sock.bind(address)
            except OSError as e:
                if e.errno == errno.EADDRNOTAVAIL:
                    sockets.pop().close()  # the family isn't turned on
                    continue
                raise
            sock.setblocking(False)
        if not sockets:
            raise OSError(errno.EADDRNOTAVAIL, f"no address to listen on for {host!r}")
    except BaseException:
        for sock in sockets:
            sock.close()
        raise
    return sockets


# Seconds that the server waits, once asked to stop, for its connections to close,
# before it stops anyway. Without a limit, uvicorn waits for ever, and on Windows
# a client that drops its connection at the wrong moment (such as a GUI window
# closing) can leave asyncio counting a connection that no longer exists, so the
# experiment never finishes shutting down.
SHUTDOWN_TIMEOUT = 3


class APIServer:
    def __init__(
        self,
        host: str = "localhost",
        port: int = 8000,
        fallback_ports: tuple[int, ...] = (),
        # allowed_cors_origins: list = ["http://localhost:3000"],
    ):
        """
        Args:
            host (str): The address to listen on.
            port (int): The port to listen on. Once `bind` has run, the port it
                actually listens on.
            fallback_ports (tuple[int, ...]): Ports to try in turn if `port` is
                taken by another program.
        """
        self.host = host
        self.port = port
        self.fallback_ports = tuple(fallback_ports)
        self._sockets = None  # bound by `bind`, then served by uvicorn

        self.app = FastAPI(
            title="PyAcquisition API",
            description="API for PyAcquisition",
        )

        self.websocket_endpoints = {}

        # self.app.add_middleware(
        #     CORSMiddleware,
        #     allow_origins=allowed_cors_origins,
        #     allow_credentials=True,
        #     allow_methods=["*"],
        #     allow_headers=["*"],
        # )

        logger.debug("[FastApi] APIServer initialized")

        self._shutdown_event = asyncio.Event()

    @staticmethod
    def _enum_to_selected_dict(enum_instance):
        """
        Converts an enum instance to a dictionary with enum names as keys and their values as values.
        """
        return {
            item.name: {
                "value": item.value,
                "selected": item == enum_instance,
            }
            for item in enum_instance.__class__
        }

    def add_websocket_endpoint(self, url: str, encode=enum_choices):
        """
        Adds a WebSocket endpoint to the FastAPI app.

        Args:
            url (str): The URL path for the WebSocket endpoint.
            encode (callable): Turns a message into what is sent as JSON. The
                default replaces enums with their choices, as the classic GUI
                expects.

        Returns:
            WebsocketEndpoint: The endpoint, to subscribe to what it streams.
        """

        self.websocket_endpoints[url] = WebsocketEndpoint(encode=encode)

        @self.app.websocket(url)
        async def websocket_endpoint(websocket: WebSocket):
            """
            WebSocket endpoint that polls the provided async function and sends data to connected clients.

            Args:
                    websocket (WebSocket): WebSocket connection object.
            """
            await self.websocket_endpoints[url].run(websocket)

        logger.debug(f"[FastApi] WebSocket endpoint added at '{url}'")
        return self.websocket_endpoints[url]

    async def setup(self):
        """
        Sets up the API server. This method is called before running the server.
        """
        logger.debug(f"[FastApi] Server setup started at {self.host}:{self.port}")
        logger.debug("[FastApi] Server setup completed")

    def bind(self) -> int:
        """
        Claims the port to listen on: `port` if it is free, otherwise the first
        free one of `fallback_ports`. Done before anything else starts (the GUI
        needs to know the port), and by binding, not by checking, so nothing can
        take the port in between. Calling it again changes nothing.

        Returns:
            int: The port, which `port` is now.

        Raises:
            PortsUnavailable: If none of the ports can be had.
        """
        if self._sockets is not None:
            return self.port
        wanted = self.port
        refused = []
        for port in dict.fromkeys((wanted, *self.fallback_ports)):
            try:
                self._sockets = bind_sockets(self.host, port)
            except OSError as e:
                refused.append(f"{port} ({e.strerror or e})")
                logger.warning(f"[FastApi] Can't listen on port {port}: {e.strerror or e}")
                continue
            self.port = port
            if port != wanted:
                logger.warning(
                    f"[FastApi] Port {wanted} is in use, so the API server is on "
                    f"port {port} instead"
                )
            return port
        raise PortsUnavailable(
            f"The API server can't listen on {self.host}: every port it may use is "
            f"taken: {', '.join(refused)}. Close whatever is using one, or choose "
            "others with `api_server_port` and `api_server_fallback_ports`.",
        )

    def release(self) -> None:
        """Lets go of the port, if the server claimed it and never ran (the
        server closes it itself when it stops)."""
        for sock in self._sockets or []:
            sock.close()

    def run(self, experiment=None):
        """
        A coroutine that runs the FastAPI server, on the port `bind` claimed
        (claiming it once it starts, if it hasn't been).
        """
        return self._serve()

    async def _serve(self) -> None:
        self.bind()
        config = uvicorn.Config(
            self.app,
            host=self.host,
            port=self.port,
            log_level="warning",
            timeout_graceful_shutdown=SHUTDOWN_TIMEOUT,
        )
        self.server = uvicorn.Server(config)
        try:
            await self.server.serve(sockets=self._sockets)
        except Exception as e:
            logger.error(f"[FastApi] An error occurred while running the server: {e}")

    async def teardown(self):
        """
        Cleans up the API server. This method is called after the server has stopped.
        """
        logger.debug("[FastApi] Server teardown started")
        logger.debug("[FastApi] Server teardown completed")

    async def shutdown(self):
        """
        Shuts down the API server.
        """
        logger.debug("[FastApi] Server shutdown started")
        self._shutdown_event.set()
        for url, endpoint in self.websocket_endpoints.items():
            endpoint._shutdown_event.set()
        await asyncio.sleep(0.1)
        self.server.should_exit = True

    def create_endpoint_function(self, method):
        """
        Endpoint factory
        """

        async def endpoint_func(**kwargs):
            """
            An endpoint function to handle the request.
            """
            return {"status": 200, "data": method(**kwargs)}

        endpoint_func.__name__ = method.__name__
        endpoint_func.__annotations__ = method.__annotations__
        endpoint_func.__annotations__["return"] = dict
        endpoint_func.__signature__ = inspect.signature(method)
        endpoint_func.__doc__ = method.__doc__

        return endpoint_func

    def _register_endpoints(self, api_server):
        """
        Registers endpoints to the FastAPI app.
        """

        @api_server.app.get("/ping")
        async def ping() -> str:
            """
            Endpoint to check if the API server is running.
            """
            return "pong"

        @api_server.app.get("/list_websockets")
        async def list_websockets() -> list:
            """
            Endpoint to list all available WebSocket endpoints.
            """
            return list(api_server.websocket_endpoints.keys())
