"""The fix for asyncio on Windows, for connections that the other end resets."""

import sys
from types import SimpleNamespace

import pytest

from pyacquisition.core import windows_asyncio


class ResetSocket:
    """A socket whose other end has reset the connection."""

    def __init__(self):
        self.closed = False

    def shutdown(self, how):
        if self.closed:
            raise OSError("closed")
        raise ConnectionResetError(10054, "forcibly closed by the remote host")

    def fileno(self):
        return -1 if self.closed else 7

    def close(self):
        self.closed = True


def transport():
    """What asyncio's clean-up reads from a transport, with a reset socket."""
    return SimpleNamespace(
        _called_connection_lost=False,
        _protocol=SimpleNamespace(lost=[], connection_lost=lambda exc: None),
        _sock=ResetSocket(),
        _server=SimpleNamespace(detached=[], _detach=lambda *a: None),
    )


def asyncio_clean_up():
    """asyncio's own `_call_connection_lost`, without the fix."""
    from asyncio import proactor_events

    method = proactor_events._ProactorBasePipeTransport._call_connection_lost
    return getattr(method, "__wrapped__", method)


def watch(t):
    lost, detached = [], []
    t._protocol.connection_lost = lost.append
    t._server._detach = lambda *args: detached.append(True)
    return lost, detached


def test_without_the_fix_a_reset_skips_the_rest_of_the_clean_up():
    t = transport()
    lost, detached = watch(t)

    with pytest.raises(ConnectionResetError):
        asyncio_clean_up()(t, None)

    assert lost == [None]  # the protocol heard...
    assert detached == []  # ...but the server still counts the connection
    assert t._called_connection_lost is False


def test_with_the_fix_a_reset_is_cleaned_up_fully():
    t = transport()
    lost, detached = watch(t)

    windows_asyncio._tolerant(asyncio_clean_up())(t, None)

    assert lost == [None]
    assert detached == [True]
    assert t._called_connection_lost is True
    assert t._sock is None


def test_with_the_fix_an_ordinary_close_is_unchanged():
    t = transport()
    t._sock.shutdown = lambda how: None  # no reset
    lost, detached = watch(t)

    windows_asyncio._tolerant(asyncio_clean_up())(t, None)

    assert (lost, detached, t._called_connection_lost) == ([None], [True], True)


class Pipe:
    """A pipe, as a subprocess's input or output is: no shutdown to call."""

    def __init__(self):
        self.closed = False

    def fileno(self):
        return -1 if self.closed else 9

    def close(self):
        self.closed = True


def test_a_pipe_is_left_to_asyncio():
    # Playwright talks to its driver over pipes; breaking their clean-up hung it.
    t = transport()
    t._sock = Pipe()
    t._server = None
    lost, _ = watch(SimpleNamespace(_protocol=t._protocol, _server=SimpleNamespace()))

    windows_asyncio._tolerant(asyncio_clean_up())(t, None)

    assert lost == [None]
    assert t._called_connection_lost is True


def test_a_second_call_does_nothing():
    t = transport()
    t._called_connection_lost = True
    sock = t._sock

    windows_asyncio._tolerant(asyncio_clean_up())(t, None)

    assert not sock.closed


@pytest.mark.skipif(sys.platform != "win32", reason="the fix is only for Windows")
def test_it_is_installed_with_the_api_server():
    from asyncio import proactor_events

    import pyacquisition.core.api_server  # noqa: F401

    method = proactor_events._ProactorBasePipeTransport._call_connection_lost
    assert hasattr(method, "__wrapped__")
