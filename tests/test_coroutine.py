import pytest
import asyncio
from dataclasses import dataclass
from pyacquisition import Experiment
from pyacquisition.coroutines.coroutine import Coroutine

pytestmark = pytest.mark.software


@dataclass
class CoroutineOne(Coroutine):

	var: float = 1

	def string(self):
		return f"This is a CoroutineOne"


	async def run(self):
		yield {'data': self.var}



@dataclass
class CoroutineTwo(Coroutine):

	var: float = 2

	def string(self):
		return f"This is a CoroutineTwo"


	async def run(self):
		yield None
		yield {'data': self.var}


@dataclass
class NestedCoroutine(Coroutine):

	var: float = 3

	def string(self):
		return f"This is a CoroutineTwo"


	async def run(self):
		yield None
		x = await self.execute_another_coroutine(
			CoroutineTwo()
		)
		yield {
			'own_data': self.var,
			'nested_data': x['data'],
		}



@dataclass
class ConcurrentNestedCoroutine(Coroutine):

	var: float = 4

	def string(self):
		return f"This is a CoroutineTwo"


	async def run(self):
		yield None
		x = await self.execute_concurrent_coroutines([
			CoroutineOne(),
			CoroutineTwo(),
		])
		yield {
			'own_data': self.var,
			'nested_data': x,
		}





@pytest.fixture
def coroutine_one():
	return CoroutineOne()


@pytest.fixture
def coroutine_two():
	return CoroutineTwo()


@pytest.fixture
def nested_coroutine():
	return NestedCoroutine()


@pytest.fixture
def concurrent_nested_coroutine():
	return ConcurrentNestedCoroutine()


@pytest.mark.asyncio
async def test_execution(coroutine_one):
	"""
	Ensure coroutines execute
	"""
	x = await coroutine_one.execute()
	assert x == {'data': 1}


@pytest.mark.asyncio
async def test_nested_execution(nested_coroutine):
	"""
	Ensure nested coroutines execute
	"""
	x = await nested_coroutine.execute()
	assert 'own_data' in x
	assert 'nested_data' in x



@pytest.mark.asyncio
async def test_concurrent_nested_execution(concurrent_nested_coroutine):
	"""
	Ensure concurrent nested coroutines execute
	"""
	x = await concurrent_nested_coroutine.execute()
	assert x['nested_data'] == [{'data': 1}, {'data': 2}]

