import pytest
import time

from pyacquisition import Experiment
from pyacquisition.scribe import Scribe


pytestmark = pytest.mark.software


@pytest.fixture
def temporary_directory(tmpdir):
	p = tmpdir.mkdir("root")
	return p


@pytest.fixture
def scribe(temporary_directory):
	return Scribe(temporary_directory)



def test_scribe_instantiation(scribe):
	assert isinstance(scribe, Scribe)


def test_scribe_incremeneting_from_zero(scribe):
	assert scribe.current_data_file.startswith('00.00')

	scribe.increment_file('Second')
	assert scribe.current_data_file.startswith('00.01')

	scribe.increment_file('Third')
	assert scribe.current_data_file.startswith('00.02')

	scribe.increment_file('Third', new_chapter=True)
	assert scribe.current_data_file.startswith('01.00')