import asyncio
import pytest
from pyacquisition.core.broadcaster import Broadcaster
from pyacquisition.core.consumer import Consumer

@pytest.mark.asyncio
async def test_consumer_subscribe_to_broadcaster():
    """
    Test that a Consumer can subscribe to a Broadcaster.
    """
    broadcaster = Broadcaster()
    consumer = Consumer()

    consumer.subscribe(broadcaster)

    assert consumer in broadcaster._subscribers


@pytest.mark.asyncio
async def test_broadcast_message_to_consumer():
    """
    Test that a Broadcaster can send a message to a Consumer.
    """
    broadcaster = Broadcaster()
    consumer = Consumer()

    consumer.subscribe(broadcaster)

    # Broadcast a message
    message = {"key": "value"}
    await broadcaster.broadcast(message)

    # Verify the message is in the Consumer's queue
    received_message = await consumer.consume(timeout=1)
    assert received_message == message


@pytest.mark.asyncio
async def test_consumer_timeout():
    """
    Test that a Consumer returns None if no message is received within the timeout.
    """
    consumer = Consumer()

    # Attempt to consume with no messages in the queue
    received_message = await consumer.consume(timeout=0.2)
    assert received_message is None


@pytest.mark.asyncio
async def test_broadcast_to_multiple_consumers():
    """
    Test that a Broadcaster can broadcast messages to multiple Consumers.
    """
    broadcaster = Broadcaster()
    consumer1 = Consumer()
    consumer2 = Consumer()

    consumer1.subscribe(broadcaster)
    consumer2.subscribe(broadcaster)

    # Broadcast a message
    message = {"key": "value"}
    await broadcaster.broadcast(message)

    # Verify both consumers received the message
    received_message1 = await consumer1.consume(timeout=1)
    received_message2 = await consumer2.consume(timeout=1)

    assert received_message1 == message
    assert received_message2 == message


@pytest.mark.asyncio
async def test_unsubscribe_consumer():
    """
    Test that a Consumer can unsubscribe from a Broadcaster.
    """
    broadcaster = Broadcaster()
    consumer = Consumer()

    consumer.subscribe(broadcaster)
    assert consumer in broadcaster._subscribers

    broadcaster.unsubscribe(consumer)
    assert consumer not in broadcaster._subscribers