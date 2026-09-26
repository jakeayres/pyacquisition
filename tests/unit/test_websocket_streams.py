"""Websocket streams: every client receives every message (milestone 2)."""

import asyncio
import socket
from enum import Enum

import pytest
import pytest_asyncio
from aiohttp import ClientSession

from pyacquisition.core.api_server import APIServer, enum_choices
from pyacquisition.core.broadcaster import Broadcaster


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("localhost", 0))
        return s.getsockname()[1]


async def eventually(condition, timeout=3.0):
    for _ in range(int(timeout / 0.02)):
        if condition():
            return
        await asyncio.sleep(0.02)
    raise AssertionError("the condition never held")


@pytest_asyncio.fixture
async def stream():
    """A running server with a websocket at /stream, fed by a broadcaster."""
    port = free_port()
    server = APIServer(port=port)
    endpoint = server.add_websocket_endpoint("/stream", encode=lambda message: message)
    source = Broadcaster()
    endpoint.subscribe_to(source)
    serving = asyncio.create_task(server.run())
    while not getattr(server, "server", None) or not server.server.started:
        await asyncio.sleep(0.02)

    yield f"ws://localhost:{port}/stream", endpoint, source

    await server.shutdown()
    await asyncio.wait_for(serving, timeout=10)


@pytest.mark.asyncio
async def test_every_client_receives_every_message(stream):
    url, endpoint, source = stream
    async with (
        ClientSession() as session,
        session.ws_connect(url) as first,
        session.ws_connect(url) as second,
    ):
        await eventually(lambda: endpoint.connections == 2)

        for n in range(20):
            await source.broadcast({"n": n})

        for client in (first, second):
            received = [
                (await asyncio.wait_for(client.receive_json(), timeout=3))["n"]
                for _ in range(20)
            ]
            assert received == list(range(20))


@pytest.mark.asyncio
async def test_a_client_that_leaves_stops_being_sent_to(stream):
    url, endpoint, source = stream
    async with ClientSession() as session:
        client = await session.ws_connect(url)
        await eventually(lambda: endpoint.connections == 1)
        assert len(source._subscribers) == 1

        await client.close()  # while nothing is being sent

        await eventually(lambda: endpoint.connections == 0)
        assert source._subscribers == []


@pytest.mark.asyncio
async def test_nothing_is_queued_while_no_client_is_connected(stream):
    _, _, source = stream

    for n in range(100):
        await source.broadcast({"n": n})

    assert source._subscribers == []


@pytest.mark.asyncio
async def test_a_client_that_joins_late_gets_what_is_sent_from_then_on(stream):
    url, endpoint, source = stream
    await source.broadcast({"n": "before"})
    async with ClientSession() as session, session.ws_connect(url) as client:
        await eventually(lambda: endpoint.connections == 1)
        await source.broadcast({"n": "after"})

        received = await asyncio.wait_for(client.receive_json(), timeout=3)
        assert received == {"n": "after"}


class Colour(Enum):
    RED = 1
    BLUE = 2


def test_the_classic_encoding_lists_the_choices_of_an_enum():
    message = {"colour": Colour.BLUE, "x": 1.0}

    assert enum_choices(message) == {
        "colour": {
            "RED": {"value": 1, "selected": False},
            "BLUE": {"value": 2, "selected": True},
        },
        "x": 1.0,
    }
    assert message["colour"] is Colour.BLUE  # the message itself is left alone


def test_the_classic_encoding_passes_other_messages_through():
    assert enum_choices("text") == "text"
