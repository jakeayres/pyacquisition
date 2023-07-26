import pytest
import asyncio

from pyacquisition import Broadcaster
from pyacquisition import Consumer


pytestmark = [
	pytest.mark.software,
]



@pytest.fixture
def broadcaster():
	return Broadcaster()


@pytest.fixture
def consumer():
	return Consumer()


def test_broadcaster_subscribing_and_unsubscribing(broadcaster, consumer):
	assert len(broadcaster._consumer_queues) == 0

	broadcaster.subscribe(consumer)
	assert len(broadcaster._consumer_queues) == 1

	broadcaster.unsubscribe(consumer)
	assert len(broadcaster._consumer_queues) == 0


def test_consumer_subscribing_and_unsubscribing(broadcaster, consumer):
	assert len(broadcaster._consumer_queues) == 0

	consumer.subscribe_to(broadcaster)
	assert len(broadcaster._consumer_queues) == 1

	consumer.unsubscribe_to(broadcaster)
	assert len(broadcaster._consumer_queues) == 0


@pytest.mark.asyncio
async def test_emit(broadcaster, consumer):
    test_item = "test item"
    consumer.subscribe_to(broadcaster)

    broadcaster.emit(test_item)

    # Get the item from consumer's queue with a timeout to avoid blocking indefinitely if the test fails
    received_item = await asyncio.wait_for(consumer._queue.get(), timeout=1.0)

    assert received_item == test_item