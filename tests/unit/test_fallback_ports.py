"""Fallback ports: the API server moves to another port when its own is taken
by some other program."""

import asyncio
import socket
from contextlib import contextmanager

import pytest
from aiohttp import ClientSession

from pyacquisition import Experiment
from pyacquisition.core import settings
from pyacquisition.core.api_server import APIServer, PortsUnavailable, bind_sockets


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("localhost", 0))
        return s.getsockname()[1]


@contextmanager
def taken(port):
    """Another program listening on the port."""
    other = socket.create_server(("127.0.0.1", port))
    try:
        yield
    finally:
        other.close()


def free_ports(count):
    """Different free ports (held open while they're found, so none repeats)."""
    holders = [socket.create_server(("127.0.0.1", 0)) for _ in range(count)]
    ports = [s.getsockname()[1] for s in holders]
    for s in holders:
        s.close()
    return ports


# -------------------------------------------------------------- the setting
def test_there_are_no_fallback_ports_unless_given(tmp_path):
    assert Experiment(root_path=str(tmp_path), gui=False)._api_server.fallback_ports == ()


def test_fallback_ports_are_a_list_of_ports():
    check = settings.SETTINGS["api_server_fallback_ports"].check
    assert check("p", [8001, 8002]) == (8001, 8002)
    assert check("p", (8001,)) == (8001,)
    assert check("p", []) == ()


@pytest.mark.parametrize("value", [8001, "8001", [0], [70000], ["8001"], [True], None])
def test_anything_else_is_refused(value):
    with pytest.raises(ValueError, match="api_server_fallback_ports"):
        settings.SETTINGS["api_server_fallback_ports"].check(
            "api_server_fallback_ports", value
        )


def test_fallback_ports_are_read_from_toml(tmp_path):
    config = tmp_path / "rig.toml"
    config.write_text(
        f'[experiment]\nroot_path = "{tmp_path.as_posix()}"\n'
        "[api_server]\nport = 8000\nfallback_ports = [8001, 8002]\n[gui]\nrun = false\n"
    )

    assert Experiment.from_config(str(config))._api_server.fallback_ports == (8001, 8002)


def test_fallback_ports_can_be_a_class_attribute(tmp_path):
    class Rig(Experiment):
        api_server_fallback_ports = [8101, 8102]

    assert Rig(root_path=str(tmp_path), gui=False)._api_server.fallback_ports == (8101, 8102)


# -------------------------------------------------------------- binding
def test_a_free_port_is_bound_on_every_address_of_localhost():
    port = free_port()
    sockets = bind_sockets("localhost", port)
    try:
        addresses = {s.getsockname()[0] for s in sockets}
        assert "127.0.0.1" in addresses
        assert {s.getsockname()[1] for s in sockets} == {port}
    finally:
        for s in sockets:
            s.close()


def test_a_port_another_program_has_can_not_be_bound():
    port = free_port()
    with taken(port), pytest.raises(OSError):
        bind_sockets("localhost", port)


def test_nothing_is_left_bound_when_one_address_fails():
    port = free_port()
    with taken(port):
        with pytest.raises(OSError):
            bind_sockets("localhost", port)
    # Every address can be had again, so nothing was left holding one.
    for s in bind_sockets("localhost", port):
        s.close()


def test_the_server_keeps_its_own_port_when_it_is_free():
    port, fallback = free_ports(2)
    server = APIServer(port=port, fallback_ports=(fallback,))
    try:
        assert server.bind() == port
        assert server.port == port
    finally:
        server.release()


def test_the_server_moves_to_the_first_free_fallback():
    port, busy_fallback, fallback = free_ports(3)
    server = APIServer(port=port, fallback_ports=(busy_fallback, fallback))
    with taken(port), taken(busy_fallback):
        try:
            assert server.bind() == fallback
            assert server.port == fallback
        finally:
            server.release()


def test_binding_again_keeps_the_port_it_has():
    port = free_port()
    server = APIServer(port=port)
    try:
        server.bind()
        assert server.bind() == port
    finally:
        server.release()


def test_releasing_lets_the_port_go():
    port = free_port()
    server = APIServer(port=port)
    server.bind()
    server.release()

    for s in bind_sockets("localhost", port):
        s.close()


def test_when_every_port_is_taken_the_error_says_which():
    port, fallback = free_ports(2)
    server = APIServer(port=port, fallback_ports=(fallback,))
    with taken(port), taken(fallback):
        with pytest.raises(PortsUnavailable) as caught:
            server.bind()
    message = str(caught.value)
    assert f"{port} (" in message and f"{fallback} (" in message
    assert "api_server_fallback_ports" in message


def test_with_no_fallbacks_a_taken_port_is_an_error():
    port = free_port()
    with taken(port), pytest.raises(PortsUnavailable):
        APIServer(port=port).bind()


@pytest.mark.asyncio
async def test_the_server_answers_on_the_fallback_port():
    port, fallback = free_ports(2)
    with taken(port):
        server = APIServer(port=port, fallback_ports=(fallback,))
        server._register_endpoints(server)
        serving = asyncio.create_task(server.run())
        try:
            while not getattr(server, "server", None) or not server.server.started:
                await asyncio.sleep(0.02)
            async with ClientSession() as session:
                async with session.get(f"http://localhost:{fallback}/ping") as response:
                    assert await response.json() == "pong"
        finally:
            await server.shutdown()
            await asyncio.wait_for(serving, timeout=10)


# -------------------------------------------------------------- in an experiment
@pytest.mark.asyncio
async def test_an_experiment_runs_on_the_fallback_and_tells_its_gui(tmp_path):
    port, fallback = free_ports(2)
    experiment = Experiment(
        root_path=str(tmp_path),
        gui=False,
        api_server_port=port,
        api_server_fallback_ports=[fallback],
    )
    with taken(port):
        running = asyncio.create_task(experiment._run())
        try:
            async with ClientSession() as session:
                for _ in range(100):
                    try:
                        async with session.get(f"http://localhost:{fallback}/ping") as r:
                            assert await r.json() == "pong"
                            break
                    except OSError:
                        await asyncio.sleep(0.05)
                else:
                    pytest.fail("the experiment never answered on the fallback port")
            assert experiment._api_server.port == fallback
            assert experiment._gui.port == fallback  # the GUI goes where the server is
        finally:
            experiment._shutdown_event.set()
            await asyncio.wait_for(running, timeout=20)


@pytest.mark.asyncio
async def test_an_experiment_with_no_port_to_have_stops_before_setting_up(tmp_path):
    port = free_port()
    set_up = []

    class Rig(Experiment):
        def setup(self):
            set_up.append(True)

    experiment = Rig(root_path=str(tmp_path), gui=False, api_server_port=port)
    with taken(port):
        with pytest.raises(PortsUnavailable):
            await asyncio.wait_for(experiment._run(), timeout=10)

    assert set_up == []  # no instruments were opened


def test_the_gui_follows_the_port():
    from pyacquisition.gui import Gui

    gui = Gui(port=8000)
    gui.port = 8003

    assert gui.server == "http://localhost:8003"


def test_making_the_coroutine_does_not_claim_the_port():
    port = free_port()
    server = APIServer(port=port)

    server.run().close()  # made, never run

    for s in bind_sockets("localhost", port):
        s.close()
