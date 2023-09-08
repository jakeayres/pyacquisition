import pytest
import asyncio
from dataclasses import dataclass

from pyacquisition import Experiment
from pyacquisition.coroutines.coroutine import Coroutine

pytestmark = pytest.mark.software


@dataclass
class CoroutineOne(Coroutine):

	def string(self):
		return 'Test coroutine one'

	async def run(self):
		yield ''
		await asyncio.sleep(0.2)
		yield ''


@dataclass
class CoroutineTwo(Coroutine):

	def string(self):
		return 'Test coroutine two'

	async def run(self):
		yield ''
		await asyncio.sleep(0.2)
		yield ''


@pytest.fixture
def temporary_directory(tmpdir):
	p = tmpdir.mkdir("root")
	return p


@pytest.fixture
def experiment(temporary_directory):
	return Experiment(temporary_directory)


@pytest.mark.asyncio
async def test_add_task(experiment):
	"""
	Ensure tasks can be added

	:param      experiment:      The experiment
	:type       experiment:      { type_description }

	:raises     AssertionError:  { exception_description }
	"""

	await experiment.add_task(CoroutineOne())
	task = await experiment.get_task()
	assert isinstance(task, CoroutineOne)


@pytest.mark.asyncio
async def test_remove_task(experiment):
	"""
	Ensure tasks can be removed

	:param      experiment:      The experiment
	:type       experiment:      { type_description }

	:raises     AssertionError:  { exception_description }
	"""

	await experiment.add_task(CoroutineOne())
	assert len(experiment.list_tasks()) == 1

	experiment.remove_task(-1)
	assert len(experiment.list_tasks()) == 0


@pytest.mark.asyncio
async def test_insert_task(experiment):
	"""
	Ensure tasks can be inserted

	:param      experiment:      The experiment
	:type       experiment:      { type_description }

	:raises     AssertionError:  { exception_description }
	"""

	await experiment.add_task(CoroutineOne())
	await experiment.add_task(CoroutineOne())
	experiment.insert_task(CoroutineTwo(), 1)
	assert len(experiment.list_tasks()) == 3

	task = await experiment.get_task()
	assert isinstance(task, CoroutineOne)
	task = await experiment.get_task()
	assert isinstance(task, CoroutineTwo)
	task = await experiment.get_task()
	assert isinstance(task, CoroutineOne)
	

@pytest.mark.asyncio
async def test_clear_tasks(experiment):
	"""
	Ensure tasks can be cleared

	:param      experiment:      The experiment
	:type       experiment:      { type_description }

	:raises     AssertionError:  { exception_description }
	"""
	await experiment.add_task(CoroutineOne())
	await experiment.add_task(CoroutineOne())
	experiment.clear_tasks()

	assert len(experiment.list_tasks()) == 0


@pytest.mark.asyncio
async def test_execute_tasks(experiment):
	"""
	Ensure tasks are executed

	:param      experiment:      The experiment
	:type       experiment:      { type_description }

	:raises     AssertionError:  { exception_description }
	"""

	await experiment.add_task(CoroutineOne())
	await experiment.add_task(CoroutineOne())
	assert len(experiment.list_tasks()) == 2

	execution_task = asyncio.create_task(experiment.execute())

	done, pending = await asyncio.wait([execution_task], timeout=1)

	assert len(experiment.list_tasks()) == 0
	assert execution_task in pending

	if execution_task in pending:
		execution_task.cancel()



@pytest.mark.asyncio
async def test_pause_resume_tasks(experiment):
	"""
	Ensure that tasks can be paused and resumed

	:param      experiment:      The experiment
	:type       experiment:      { type_description }

	:raises     AssertionError:  { exception_description }
	"""

	await experiment.add_task(CoroutineOne())
	await experiment.add_task(CoroutineOne())
	assert len(experiment.list_tasks()) == 2

	execution_task = asyncio.create_task(experiment.execute())
	done, pending = await asyncio.wait([execution_task], timeout=0.05)

	experiment.pause_task()

	assert len(experiment.list_tasks()) == 1
	await asyncio.sleep(0.5)
	assert len(experiment.list_tasks()) == 1
	assert experiment.current_task.is_paused() == True

	experiment.resume_task()
	await asyncio.sleep(0.001)
	assert experiment.current_task.is_paused() == False
	await asyncio.sleep(0.5)
	assert len(experiment.list_tasks()) == 0

	if execution_task in pending:
		execution_task.cancel()
