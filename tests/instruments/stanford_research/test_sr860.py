import pytest, time, asyncio
from pyacquisition.instruments import SR_860
from pyacquisition.visa import resource_manager

from pyacquisition.instruments.stanford_research.sr_860 import (
	ReferenceSource,
	InputMode,
	InputConfiguration,
	InputCoupling,
	InputGrounding,
	InputVoltageRange,
	Sensitivity,
	TimeConstant,
	FilterSlope,
	SyncFilter,
	AdvancedFilter,
)


"""
Mark tests
"""
pytestmark = [
	pytest.mark.hardware,
	pytest.mark.SR_860,
]



@pytest.fixture
def inst():
	visa_res = resource_manager('prologix', com_port=3).open_resource('GPIB0::1::INSTR')
	return SR_860('my_lia', visa_res)



def test_identify(inst):
	assert 'SR860' in inst._query('*IDN?')


@pytest.mark.parametrize("value", [0.00, -10.123, 123.43, 6, 54])
def test_phase(inst, value):
	response = inst.set_phase(value)
	result = inst.get_phase()

	assert response == 0
	assert result == pytest.approx(value, rel=1e-3)


@pytest.mark.parametrize("value", [
	ReferenceSource.INTERNAL, 
	ReferenceSource.EXTERNAL,
	ReferenceSource.DUAL,
	ReferenceSource.CHOP,
	])
def test_reference_source(inst, value):
	response = inst.set_reference_source(value)
	source = inst.get_reference_source()

	assert response == 0
	assert source == source


@pytest.mark.parametrize("value", [0.98, 12, 15.542, 100, 15e3, 15000, 100e3, 1e3])
def test_frequency(inst, value):
	response = inst.set_frequency(value)
	frequency = inst.get_frequency()

	assert response == 0
	assert frequency == pytest.approx(value, rel=1e-3)


@pytest.mark.parametrize("value", [0.98, 12, 15.542, 100, 15e3, 15000, 100e3, 1e3])
def test_internal_frequency(inst, value):
	response = inst.set_internal_frequency(value)
	frequency = inst.get_internal_frequency()

	assert response == 0
	assert frequency == pytest.approx(value, rel=1e-3)	


@pytest.mark.parametrize("value", [1, 2, 3, 1])
def test_harmonic(inst, value):
	response = inst.set_harmonic(value)
	harmonic = inst.get_harmonic()

	assert response == 0
	assert harmonic == value


@pytest.mark.parametrize("value", [-2, 0, -2, 0.002, -5e-3, 0])
def test_reference_amplitude(inst, value):
	response = inst.set_reference_offset(value)
	offset = inst.get_reference_offset()

	assert response == 0
	assert offset == pytest.approx(value, rel=1e-3)


@pytest.mark.parametrize("value", list(InputMode))
def test_input_mode(inst, value):
	response = inst.set_input_mode(value)
	result = inst.get_input_mode()

	assert response == 0
	assert result == value


@pytest.mark.parametrize("value", list(InputConfiguration))
def test_input_configuration(inst, value):
	response = inst.set_input_configuration(value)
	result = inst.get_input_configuration()

	assert response == 0
	assert result == value


@pytest.mark.parametrize("value", list(InputCoupling))
def test_input_coupling(inst, value):
	response = inst.set_input_coupling(value)
	result = inst.get_input_coupling()

	assert response == 0
	assert result == value


@pytest.mark.parametrize("value", list(InputGrounding))
def test_input_grounding(inst, value):
	response = inst.set_input_grounding(value)
	result = inst.get_input_grounding()

	assert response == 0
	assert result == value


@pytest.mark.parametrize("value", list(InputVoltageRange))
def test_input_voltage_range(inst, value):
	response = inst.set_input_voltage_range(value)
	result = inst.get_input_voltage_range()

	assert response == 0
	assert result == value


@pytest.mark.parametrize("value", list(Sensitivity))
def test_sensitivity(inst, value):
	response = inst.set_sensitivity(value)
	result = inst.get_sensitivity()

	assert response == 0
	assert result == value


@pytest.mark.parametrize("value", list(TimeConstant))
def test_time_constant(inst, value):
	response = inst.set_time_constant(value)
	result = inst.get_time_constant()

	assert response == 0
	assert result == value


@pytest.mark.parametrize("value", list(FilterSlope))
def test_filter_slope(inst, value):
	response = inst.set_filter_slope(value)
	result = inst.get_filter_slope()

	assert response == 0
	assert result == value


@pytest.mark.parametrize("value", list(SyncFilter))
def test_sync_filter(inst, value):
	response = inst.set_sync_filter(value)
	result = inst.get_sync_filter()

	assert response == 0
	assert result == value


@pytest.mark.parametrize("value", list(AdvancedFilter))
def test_advanced_filter(inst, value):
	response = inst.set_advanced_filter(value)
	result = inst.get_advanced_filter()

	assert response == 0
	assert result == value


def test_output_x(inst):
	result = inst.get_x()
	assert isinstance(result, float)


def test_output_y(inst):
	result = inst.get_y()
	assert isinstance(result, float)


def test_output_xy(inst):
	result = inst.get_xy()
	assert all(isinstance(item, float) for item in result)
	assert len(result) == 2







