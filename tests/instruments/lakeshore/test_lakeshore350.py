import pytest, time, asyncio
import numpy as np
from pyacquisition.instruments import Lakeshore_350
from pyacquisition.visa import resource_manager

from pyacquisition.instruments.lakeshore.lakeshore_350 import (
	OutputChannel,
	InputChannel,
	State,
	CurveFormat,
	CurveCoefficient,
)



"""
Mark tests
"""
pytestmark = [
	pytest.mark.hardware,
	pytest.mark.lakeshore_350,
]



@pytest.fixture
def inst():
	visa_res = resource_manager('prologix', com_port=3).open_resource('GPIB0::3::INSTR')
	return Lakeshore_350('lake', visa_res)


def test_identify(inst):
	assert '350' in inst._query('*IDN?')



def test_set_setpoint(inst):
	response = inst.set_setpoint(OutputChannel.OUTPUT_1, 25)
	assert response == 0


def test_get_setpoint(inst):
	response = inst.get_setpoint(OutputChannel.OUTPUT_1)
	assert isinstance(response, float)


def test_set_ramp(inst):
	response = inst.set_ramp(OutputChannel.OUTPUT_1, State.ON, 2.5)
	assert response == 0


def test_get_ramp(inst):
	response = inst.get_ramp(OutputChannel.OUTPUT_1)
	assert isinstance(response, list)
	assert isinstance(response[0], State)
	assert isinstance(response[1], float)


def test_get_ramp_status(inst):
	response = inst.get_ramp_status(OutputChannel.OUTPUT_1)
	assert isinstance(response, State)


def test_get_temperature(inst):
	response = inst.get_temperature(InputChannel.INPUT_A)
	assert isinstance(response, float)


def test_get_resistance(inst):
	response = inst.get_resistance(InputChannel.INPUT_A)
	assert isinstance(response, float)


def test_get_curve_header(inst):
	response = inst.get_curve_header(1)
	assert 'DT-470' in response


def test_set_curve_header(inst):
	response = inst.set_curve_header(22, 'JAKE', 'TEST', CurveFormat.LOGOHM_K, 305, CurveCoefficient.NEGATIVE)
	assert response == 0

	response = inst.get_curve_header(22)
	assert 'JAKE' in response


def test_get_curve_point(inst):
	response = inst.get_curve_point(1, 1)
	assert '+0.07933,+480.000' in response


def test_set_curve_point(inst):
	for i, (x, t) in enumerate(zip(np.linspace(1.0, 4, 100), np.linspace(300, 4, 100))):
		response = inst.set_curve_point(22, i+1, x, t)
		assert response == 0

	response = inst.get_curve_point(22, 1)
	assert '1.0' in response
	assert '300.0' in response