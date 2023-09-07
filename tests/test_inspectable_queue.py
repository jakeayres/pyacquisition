import pytest
import time

from pyacquisition.inspectable_queue import InspectableQueue


pytestmark = pytest.mark.software


@pytest.fixture
def queue():
	return InspectableQueue()



@pytest.mark.asyncio
async def test_put_queue(queue):

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


# def test_putnowait_queue(queue):

# 	queue.put_nowait('item3')
# 	assert queue.inspect() == ['item1', 'item2', 'item3']


# @pytest.mark.asyncio
# async def test_get_queue(queue):
# 	item = await queue.get()
# 	assert item == 'item1'
# 	assert queue.inspect() == ['item2', 'item3']


# def test_insert_queue(queue):
# 	queue.insert('item2.5', 1)
# 	assert queue.inspect() == ['item2', 'item2.5', 'item3']


# def test_remove_queue(queue):
# 	popped = queue.remove(1)
# 	assert popped == 'item2.5'


# def test_remove_queue(queue):
# 	queue.clear()
# 	assert queue.inspect() == []