import pytest
import time

from pyacquisition.inspectable_queue import InspectableQueue


pytestmark = pytest.mark.software


@pytest.fixture
def queue():
	return InspectableQueue()



@pytest.mark.asyncio
async def test_queue(queue):
	await queue.put('item1')
	await queue.put('item2')
	assert queue.inspect() == ['item1', 'item2']

	queue.put_nowait('item3')
	assert queue.inspect() == ['item1', 'item2', 'item3']


	item = await queue.get()
	assert item == 'item1'
	assert queue.inspect() == ['item2', 'item3']

	queue.insert('item2.5', 1)
	assert queue.inspect() == ['item2', 'item2.5', 'item3']

	popped = queue.remove(1)
	assert popped == 'item2.5'

	queue.clear()
	assert queue.inspect() == []