from enum import Enum
from pydantic import BaseModel

from ...core.instrument import Instrument, mark_query, mark_command


class ReferenceSource(Enum):
    INTERNAL = 0
    EXTERNAL = 1
    DUAL = 2
    CHOP = 3


class ReferenceSourceModel(Enum):
    INTERNAL = 'Internal'
    EXTERNAL = 'External'
    DUAL = 'Dual'
    CHOP = 'Chopped'


class ReferenceSlope(Enum):
    SINE = 0
    TTL_RISING = 1
    TTL_FALLING = 2


class ReferenceSlopeModel(Enum):
    SINE = 'Sine'
    TTL_RISING = 'TTL Rising'
    TTL_FALLING = 'TLL Falling'


class InputMode(Enum):
    VOLTAGE = 0
    CURRENT = 1


class InputModeModel(Enum):
    VOLTAGE = 'Voltage'
    CURRENT = 'Current'


class InputConfiguration(Enum):
    A = 0
    A_B = 1


class InputConfigurationModel(Enum):
    A = 'A'
    A_B = 'A-B'


class InputGrounding(Enum):
    FLOAT = 0
    GROUND = 1


class InputGroundingModel(Enum):
    FLOAT = 'Floating'
    GROUND = 'Grounded'


class InputCoupling(Enum):
    AC = 0
    DC = 1


class InputCouplingModel(Enum):
    AC = 'AC'
    DC = 'DC'


class InputVoltageRange(Enum):
    V_1 = 0
    mV_300 = 1
    mV_100 = 2
    mV_30 = 3
    mV_10 = 4


class InputVoltageRangeModel(Enum):
    V_1 = '1 V'
    mV_300 = '300 mV'
    mV_100 = '100 mV'
    mV_30 = '30 mV'
    mV_10 = '10 mV'


class SyncFilter(Enum):
    OFF = 0
    ON = 1


class SyncFilterModel(Enum):
    OFF = 'Off'
    ON = 'On'


class AdvancedFilter(Enum):
    OFF = 0
    ON = 1


class AdvancedFilterModel(Enum):
    OFF = 'Off'
    ON = 'On'


class Sensitivity(Enum):
    nV_1 = 27
    nV_2 = 26
    nV_5 = 25
    nV_10 = 24
    nV_20 = 23
    nV_50 = 22
    nV_100 = 21
    nV_200 = 20
    nV_500 = 19
    uV_1 = 18
    uV_2 = 17
    uV_5 = 16
    uV_10 = 15
    uV_20 = 14
    uV_50 = 13
    uV_100 = 12
    uV_200 = 11
    uV_500 = 10
    mV_1 = 9
    mV_2 = 8
    mV_5 = 7
    mV_10 = 6
    mV_20 = 5
    mV_50 = 4
    mV_100 = 3
    mV_200 = 2
    mV_500 = 1
    V_1 = 0


class SensitivityModel(Enum):
    nV_1 = '1 nV'
    nV_2 = '2 nV'
    nV_5 = '5 nV'
    nV_10 = '10 nV'
    nV_20 = '20 nV'
    nV_50 = '50 nV'
    nV_100 = '100 nV'
    nV_200 = '200 nV'
    nV_500 = '500 nV'
    uV_1 = '1 µV'
    uV_2 = '2 µV'
    uV_5 = '5 µV'
    uV_10 = '10 µV'
    uV_20 = '20 µV'
    uV_50 = '50 µV'
    uV_100 = '100 µV'
    uV_200 = '200 µV'
    uV_500 = '500 µV'
    mV_1 = '1 mV'
    mV_2 = '2 mV'
    mV_5 = '5 mV'
    mV_10 = '10 mV'
    mV_20 = '20 mV'
    mV_50 = '50 mV'
    mV_100 = '100 mV'
    mV_200 = '200 mV'
    mV_500 = '500 mV'
    V_1 = '1 V'


class TimeConstant(Enum):
    us_1 = 0
    us_3 = 1
    us_10 = 2
    us_30 = 3
    us_100 = 4
    us_300 = 5
    ms_1 = 6
    ms_3 = 7
    ms_10 = 8
    ms_30 = 9
    ms_100 = 10
    ms_300 = 11
    s_1 = 12
    s_3 = 13
    s_10 = 14
    s_30 = 15
    s_100 = 16
    s_300 = 17
    ks_1 = 18
    ks_3 = 19
    ks_10 = 20
    ks_30 = 21


class TimeConstantModel(Enum):
    us_1 = '1 us'
    us_3 = '3 us'
    us_10 = '10 us'
    us_30 = '30 us'
    us_100 = '100 us'
    us_300 = '300 us'
    ms_1 = '1 ms'
    ms_3 = '3 ms'
    ms_10 = '10 ms'
    ms_30 = '30 ms'
    ms_100 = '100 ms'
    ms_300 = '300 ms'
    s_1 = '1 s'
    s_3 = '3 s'
    s_10 = '10 s'
    s_30 = '30 s'
    s_100 = '100 s'
    s_300 = '300 s'
    ks_1 = '1 ks'
    ks_3 = '3 ks'
    ks_10 = '10 ks'
    ks_30 = '30 ks'


class FilterSlope(Enum):
    db6 = 0
    db12 = 1
    db18 = 2
    db24 = 3


class FilterSlopeModel(Enum):
    db6 = '6 db'
    db12 = '12 db'
    db18 = '18 db'
    db24 = '24 db'



class SR_860(Instrument):
    """ 
    Class for the Stanford Research SR-860 Lock-In Amplifier.
    """

    name = 'SR_860'

    @mark_query
    def identify(self) -> str:
        """Queries the instrument identification string.

        Returns:
            str: The identification string of the instrument.
        """
        return self.query('*IDN?')

    @mark_command
    def reset(self) -> int:
        """Resets the instrument to its default state.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command('*RST')

    @mark_command
    def clear(self) -> int:
        """Clears the status and error registers of the instrument.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command('*CLS')

    @mark_query
    def get_phase(self) -> float:
        """Queries the current excitation phase in degrees.

        Returns:
            float: The current phase angle in degrees.
        """
        return float(self.query("PHAS?"))

    @mark_command
    def set_phase(self, phase: float) -> int:
        """Sets the excitation phase in degrees.

        Args:
            phase (float): The phase angle in degrees to set.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f'PHAS {phase:.2f}')

    @mark_query
    def get_reference_source(self) -> ReferenceSource:
        """Queries the current reference source.

        Returns:
            ReferenceSource: The current reference source (e.g., INTERNAL, EXTERNAL, DUAL, CHOP).
        """
        return ReferenceSource(int(self.query(f'RSRC?')))

    @mark_command
    def set_reference_source(self, source: ReferenceSource) -> int:
        """Sets the reference source.

        Args:
            source (ReferenceSource): The reference source to set (e.g., INTERNAL, EXTERNAL, DUAL, CHOP).

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f'RSRC {source.value}')

    @mark_query
    def get_frequency(self) -> float:
        """Queries the current reference frequency.

        Returns:
            float: The current reference frequency in Hz.
        """
        return float(self.query("FREQ?"))

    @mark_command
    def set_frequency(self, frequency: float) -> int:
        """Sets the reference frequency.

        Args:
            frequency (float): The frequency in Hz to set.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f'FREQ {frequency:.3f}')

    @mark_query
    def get_internal_frequency(self) -> float:
        """Queries the internal reference frequency.

        Returns:
            float: The internal reference frequency in Hz.
        """
        return float(self.query("FREQINT?"))

    @mark_command
    def set_internal_frequency(self, frequency: float) -> int:
        """Sets the internal reference frequency.

        Args:
            frequency (float): The internal frequency in Hz to set.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f'FREQINT {frequency:.3f}')

    @mark_query
    def get_external_reference_slope(self) -> ReferenceSlope:
        """Queries the slope of the external reference signal.

        Returns:
            ReferenceSlope: The slope of the external reference signal (e.g., SINE, TTL_RISING, TTL_FALLING).
        """
        return ReferenceSlope(int(self.query(f'RSLP?')))

    @mark_command
    def set_external_reference_slope(self, slope: ReferenceSlope) -> int:
        """Sets the slope of the external reference signal.

        Args:
            slope (ReferenceSlope): The slope to set (e.g., SINE, TTL_RISING, TTL_FALLING).

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f'RSLP {slope.value}')

    @mark_query
    def get_harmonic(self) -> int:
        """Queries the current harmonic setting.

        Returns:
            int: The current harmonic setting.
        """
        return int(self.query(f'HARM?'))

    @mark_command
    def set_harmonic(self, harmonic: int) -> int:
        """Sets the harmonic.

        Args:
            harmonic (int): The harmonic to set.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f'HARM {harmonic}')

    @mark_query
    def get_reference_amplitude(self) -> float:
        """Queries the reference amplitude.

        Returns:
            float: The reference amplitude in volts.
        """
        return float(self.query(f'SLVL?'))

    @mark_command
    def set_reference_amplitude(self, amplitude: float) -> int:
        """Sets the reference amplitude.

        Args:
            amplitude (float): The amplitude in volts to set.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f'SLVL {amplitude:.3f}')

    @mark_query
    def get_reference_offset(self) -> float:
        """Queries the reference offset.

        Returns:
            float: The reference offset in volts.
        """
        return float(self.query(f'SOFF?'))

    @mark_command
    def set_reference_offset(self, amplitude: float) -> int:
        """Sets the reference offset.

        Args:
            amplitude (float): The offset in volts to set.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f'SOFF {amplitude:.3f}')

    """ INPUT AND FILTER
    """

    @mark_query
    def get_input_mode(self) -> InputMode:
        """Queries the input mode.

        Returns:
            InputMode: The current input mode (e.g., VOLTAGE, CURRENT).
        """
        return InputMode(int(self.query(f'IVMD?')))

    @mark_command
    def set_input_mode(self, mode: InputMode) -> int:
        """Sets the input mode.

        Args:
            mode (InputMode): The input mode to set (e.g., VOLTAGE, CURRENT).

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f'IVMD {mode.value}')

    @mark_query
    def get_input_configuration(self) -> InputConfiguration:
        """Queries the input configuration.

        Returns:
            InputConfiguration: The current input configuration (e.g., A, A-B).
        """
        return InputConfiguration(int(self.query(f'ISRC?')))

    @mark_command
    def set_input_configuration(self, configuration: InputConfiguration) -> int:
        """Sets the input configuration.

        Args:
            configuration (InputConfiguration): The input configuration to set (e.g., A, A-B).

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f'ISRC {configuration.value}')

    @mark_query
    def get_input_coupling(self) -> InputCoupling:
        """Queries the input coupling configuration.

        Returns:
            InputCoupling: The current input coupling configuration (e.g., AC, DC).
        """
        return InputCoupling(int(self.query(f'ICPL?')))

    @mark_command
    def set_input_coupling(self, coupling: InputCoupling) -> int:
        """Sets the input coupling configuration.

        Args:
            coupling (InputCoupling): The input coupling configuration to set (e.g., AC, DC).

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f'ICPL {coupling.value}')

    @mark_query
    def get_input_grounding(self) -> InputGrounding:
        """Queries the input grounding configuration.

        Returns:
            InputGrounding: The current input grounding configuration (e.g., FLOAT, GROUND).
        """
        return InputGrounding(int(self.query(f'IGND?')))

    @mark_command
    def set_input_grounding(self, grounding: InputGrounding) -> int:
        """Sets the input grounding configuration.

        Args:
            grounding (InputGrounding): The input grounding configuration to set (e.g., FLOAT, GROUND).

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f'IGND {grounding.value}')

    @mark_query
    def get_input_voltage_range(self) -> InputVoltageRange:
        """Queries the input voltage range.

        Returns:
            InputVoltageRange: The current input voltage range (e.g., 1 V, 300 mV).
        """
        return InputVoltageRange(int(self.query(f'IRNG?')))

    @mark_command
    def set_input_voltage_range(self, input_range: InputVoltageRange) -> int:
        """Sets the input voltage range.

        Args:
            input_range (InputVoltageRange): The input voltage range to set (e.g., 1 V, 300 mV).

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f'IRNG {input_range.value}')

    @mark_query
    def get_sync_filter(self) -> SyncFilter:
        """Queries the synchronization filter state.

        Returns:
            SyncFilter: The current synchronization filter state (e.g., OFF, ON).
        """
        return SyncFilter(int(self.query(f'SYNC?')))

    @mark_command
    def set_sync_filter(self, configuration: SyncFilter) -> int:
        """Sets the synchronization filter state.

        Args:
            configuration (SyncFilter): The synchronization filter state to set (e.g., OFF, ON).

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f'SYNC {configuration.value}')

    @mark_query
    def get_advanced_filter(self) -> AdvancedFilter:
        """Queries the advanced filter state.

        Returns:
            AdvancedFilter: The current advanced filter state (e.g., OFF, ON).
        """
        return AdvancedFilter(int(self.query(f'ADVFILT?')))

    @mark_command
    def set_advanced_filter(self, configuration: AdvancedFilter) -> int:
        """Sets the advanced filter state.

        Args:
            configuration (AdvancedFilter): The advanced filter state to set (e.g., OFF, ON).

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f'ADVFILT {configuration.value}')

    """ GAIN AND TIME CONSTANT
    """

    @mark_query
    def get_sensitivity(self) -> Sensitivity:
        """Queries the sensitivity setting.

        Returns:
            Sensitivity: The current sensitivity setting.
        """
        return Sensitivity(int(self.query(f'SCAL?')))

    @mark_command
    def set_sensitivity(self, sensitivity: Sensitivity) -> int:
        """Sets the sensitivity.

        Args:
            sensitivity (Sensitivity): The sensitivity setting to apply.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f'SCAL {sensitivity.value}')

    @mark_query 
    def get_time_constant(self) -> TimeConstant:
        """Queries the time constant setting.

        Returns:
            TimeConstant: The current time constant setting.
        """
        return TimeConstant(int(self.query(f'OFLT?')))

    @mark_command
    def set_time_constant(self, time_constant: TimeConstant) -> int:
        """Sets the time constant.

        Args:
            time_constant (TimeConstant): The time constant setting to apply.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f'OFLT {time_constant.value}')

    @mark_query
    def get_filter_slope(self) -> FilterSlope:
        """Queries the filter slope setting.

        Returns:
            FilterSlope: The current filter slope setting (e.g., 6 dB, 12 dB).
        """
        return FilterSlope(int(self.query(f'OFSL?')))

    @mark_command
    def set_filter_slope(self, filter_slope: FilterSlope) -> int:
        """Sets the filter slope.

        Args:
            filter_slope (FilterSlope): The filter slope setting to apply (e.g., 6 dB, 12 dB).

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f'OFSL {filter_slope.value}')


    @mark_query
    def get_output(self, parameter: int) -> float:
        return float(self.query(f'OUTP? {parameter}'))


    @mark_query
    def get_display_output(self, parameter: int) -> float:
        return float(self.query(f'OUTR? {parameter}'))


    @mark_query
    def get_x(self) -> float:
        return float(self.query(f'OUTP? 0'))


    @mark_query
    def get_y(self) -> float:
        return float(self.query(f'OUTP? 1'))


    @mark_query
    def get_r(self) -> float:
        return float(self.query(f'OUTP? 2'))


    @mark_query
    def get_theta(self) -> float:
        return float(self.query(f'OUTP? 3'))



    @mark_query
    def get_xy(self) -> list[float]:
        return [float(s) for s in self.query(f'SNAP? 0,1').split(',')]



    """ INTERFACE
    """

    """ STATUS
    """