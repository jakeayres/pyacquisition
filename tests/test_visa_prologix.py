import pytest
from pyacquisition.visa import PrologixResourceManager
from pyacquisition.visa.prologix import PrologixResource


pytestmark = [
	pytest.mark.software,
]


def test_resource_manager_init(mocker):
	mock_serial = mocker.patch('serial.Serial', autospec=True)
	rm = PrologixResourceManager(1)
	mock_serial.assert_called_once_with('COM1', PrologixResourceManager.BUAD_RATE, timeout=PrologixResourceManager.TIMEOUT)