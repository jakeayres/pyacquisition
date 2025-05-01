import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from pyacquisition.core.relay import Relay

@pytest.fixture
def relay():
    return Relay()


@pytest.mark.asyncio
async def test_relay_initialization(relay):
    assert relay.queue is not None
    assert isinstance(relay.queue, asyncio.Queue)
    assert relay._subscribers == []