import pytest
import asyncio
from pyacquisition import Experiment
from pyacquisition.dataframe import DataFrame

pytestmark = pytest.mark.software


@pytest.fixture
def temporary_directory(tmpdir):
	p = tmpdir.mkdir("root")
	return p


@pytest.fixture
def experiment(temporary_directory):
	exp = Experiment(temporary_directory)
	exp.add_measurement('var1', lambda: 10)
	exp.add_measurement('var2', lambda: 20)
	return exp



def test_dataframe_instantiation(experiment):

	dataframe = experiment.create_dataframe()
	assert isinstance(dataframe, DataFrame)
	assert 'var1' in dataframe.data.columns
	assert 'var2' in dataframe.data.columns


@pytest.mark.asyncio
async def test_subscription(experiment):

	dataframe = experiment.create_dataframe()
	experiment.rack.measure()

	await dataframe.update()
	print(dataframe.data)
	assert dataframe.data.columns == ['test']
	


