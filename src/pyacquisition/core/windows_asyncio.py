"""A fix for asyncio on Windows, for connections that the other end resets.

When a connection is lost, asyncio's Windows transport shuts its socket down
before closing it. If the other end has already reset the connection (a browser
window closing does), that shutdown raises `ConnectionResetError`, and the rest
of the clean-up is skipped: a traceback is printed ("Exception in callback
_ProactorBasePipeTransport._call_connection_lost"), and the server never learns
that the connection has gone. uvicorn then waits for that connection until its
graceful shutdown times out ("Cancel 0 running task(s), timeout graceful shutdown
exceeded"), so every experiment shutdown after a window closed took 3 s longer.

`install()` wraps the clean-up so the shutdown is tried first, a reset is
ignored, and the socket is closed. asyncio's own clean-up then skips the shutdown
(the socket is already closed) and does the rest as usual.
"""

import socket
import sys

_installed = False


def install() -> None:
    """Applies the fix, once, on Windows. Elsewhere it does nothing."""
    global _installed
    if _installed or sys.platform != "win32":
        return
    from asyncio import proactor_events

    transport = proactor_events._ProactorBasePipeTransport
    transport._call_connection_lost = _tolerant(transport._call_connection_lost)
    _installed = True


def _tolerant(call_connection_lost):
    def _call_connection_lost(self, exc):
        sock = self._sock
        # Only a socket: the same transport carries pipes (a subprocess's input
        # and output), which cannot be shut down, and are left to asyncio.
        if (
            not self._called_connection_lost
            and hasattr(sock, "shutdown")
            and sock.fileno() != -1
        ):
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass  # reset by the other end already, which is what was wanted
            sock.close()
        call_connection_lost(self, exc)

    _call_connection_lost.__wrapped__ = call_connection_lost
    return _call_connection_lost
