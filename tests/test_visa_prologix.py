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


def test_connection():

	rm = PrologixResourceManager(com_port=3)
	res = rm.open_resource('GPIB0::1::INSTR')

	assert res.query('*IDN?') == 'response'