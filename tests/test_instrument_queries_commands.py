import pytest
import time

from pyacquisition.instruments import Gizmotron


pytestmark = [
	pytest.mark.software,
]


@pytest.fixture
def gizmo():
	return Gizmotron('my_gizmo')


def test_commands(gizmo):
	commands = gizmo.commands
	assert isinstance(commands, dict)
	assert 'set_setpoint' in commands


def test_queries(gizmo):
	queries = gizmo.queries
	assert isinstance(queries, dict)
	assert 'get_setpoint' in queries

