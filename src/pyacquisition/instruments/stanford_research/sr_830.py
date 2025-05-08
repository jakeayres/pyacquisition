from ...core.instrument import Instrument, BaseEnum, mark_query, mark_command


class SyncFilterState(BaseEnum):
    OFF = (0, "Off")
    ON = (1, "On")


class ReferenceSource(BaseEnum):
    INTERNAL = (0, "Internal")
    EXTERNAL = (1, "External")


class ReferenceSlope(BaseEnum):
    SINE = (0, "Sine")
    TTL_RISING = (1, "TTL Rising")
    TTL_FALLING = (2, "TTL Falling")


class InputConfiguration(BaseEnum):
    A = (0, "A")
    A_B = (1, "A-B")
    I_10e6 = (2, "Current 10uA")
    I_100e6 = (3, "Current 100uA")


class InputGrounding(BaseEnum):
    FLOAT = (0, "Float")
    GROUND = (1, "Ground")


class InputCoupling(BaseEnum):
    AC = (0, "AC")
    DC = (1, "DC")


class NotchFilter(BaseEnum):
    NONE = (0, "None")
    LINE_1 = (1, "Line 1")
    LINE_2 = (2, "Line 2")
    BOTH = (3, "Both")


class Sensitivity(BaseEnum):
    nV_2 = (0, "2 nV")
    nV_5 = (1, "5 nV")
    nV_10 = (2, "10 nV")
    nV_20 = (3, "20 nV")
    nV_50 = (4, "50 nV")
    nV_100 = (5, "100 nV")
    nV_200 = (6, "200 nV")
    nV_500 = (7, "500 nV")
    uV_1 = (8, "1 uV")
    uV_2 = (9, "2 uV")
    uV_5 = (10, "5 uV")
    uV_10 = (11, "10 uV")
    uV_20 = (12, "20 uV")
    uV_50 = (13, "50 uV")
    uV_100 = (14, "100 uV")
    uV_200 = (15, "200 uV")
    uV_500 = (16, "500 uV")
    mV_1 = (17, "1 mV")
    mV_2 = (18, "2 mV")
    mV_5 = (19, "5 mV")
    mV_10 = (20, "10 mV")
    mV_20 = (21, "20 mV")
    mV_50 = (22, "50 mV")
    mV_100 = (23, "100 mV")
    mV_200 = (24, "200 mV")
    mV_500 = (25, "500 mV")
    V_1 = (26, "1 V")


class TimeConstant(BaseEnum):
    us_10 = (0, "10 µs")
    us_30 = (1, "30 µs")
    us_100 = (2, "100 µs")
    us_300 = (3, "300 µs")
    ms_1 = (4, "1 ms")
    ms_3 = (5, "3 ms")
    ms_10 = (6, "10 ms")
    ms_30 = (7, "30 ms")
    ms_100 = (8, "100 ms")
    ms_300 = (9, "300 ms")
    s_1 = (10, "1 s")
    s_3 = (11, "3 s")
    s_10 = (12, "10 s")
    s_30 = (13, "30 s")
    s_100 = (14, "100 s")
    s_300 = (15, "300 s")
    ks_1 = (16, "1 ks")
    ks_3 = (17, "3 ks")
    ks_10 = (18, "10 ks")
    ks_30 = (19, "30 ks")


class FilterSlope(BaseEnum):
    db6 = (0, "6 dB")
    db12 = (1, "12 dB")
    db18 = (2, "18 dB")
    db24 = (3, "24 dB")


class DynamicReserve(BaseEnum):
    HIGH_RESERVE = (0, "High Reserve")
    NORMAL = (1, "Normal")
    LOW_NOISE = (2, "Low Noise")


class SR_830(Instrument):
    """
    Stanford Research SR-830 Lock-In Amplifier class.
    """

    @mark_query
    def identify(self) -> str:
        """Queries the instrument identification string.

        Returns:
            str: The identification string of the instrument.
        """
        return self.query("*IDN?")

    @mark_command
    def reset(self) -> int:
        """Resets the instrument to its default state.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command("*RST")

    @mark_command
    def reset_data_buffer(self) -> int:
        """Resets the data buffer of the instrument.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command("*REST")

    @mark_command
    def clear(self) -> int:
        """Clears the status and error registers of the instrument.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command("*CLS")

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
        return self.command(f"PHAS {phase:.2f}")

    @mark_query
    def get_reference_source(self) -> ReferenceSource:
        """Queries the current reference source.

        Returns:
            ReferenceSource: The current reference source (INTERNAL or EXTERNAL).
        """
        return ReferenceSource.from_raw_value(int(self.query("FMOD?")))

    @mark_command
    def set_reference_source(self, source: ReferenceSource) -> int:
        """Sets the reference source.

        Args:
            source (ReferenceSource): The reference source to set (INTERNAL or EXTERNAL).

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"FMOD {source.raw_value}")

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
        return self.command(f"FREQ {frequency:.3f}")

    @mark_query
    def get_external_reference_slope(self) -> ReferenceSlope:
        """Queries the slope of the external reference signal.

        Returns:
            ReferenceSlope: The slope of the external reference signal.
        """
        return ReferenceSlope.from_raw_value(int(self.query("RSLP?")))

    @mark_command
    def set_external_reference_slope(self, slope: ReferenceSlope) -> int:
        """Sets the slope of the external reference signal.

        Args:
            slope (ReferenceSlope): The slope to set (e.g., SINE, TTL_RISING, TTL_FALLING).

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"RSLP {slope.raw_value}")

    @mark_query
    def get_harmonic(self) -> int:
        """Queries the current harmonic setting.

        Returns:
            int: The current harmonic setting.
        """
        return int(self.query("HARM?"))

    @mark_command
    def set_harmonic(self, harmonic: int) -> int:
        """Sets the harmonic.

        Args:
            harmonic (int): The harmonic to set.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"HARM {harmonic}")

    @mark_query
    def get_reference_amplitude(self) -> float:
        """Queries the reference amplitude.

        Returns:
            float: The reference amplitude in volts.
        """
        return float(self.query("SLVL?"))

    @mark_command
    def set_reference_amplitude(self, amplitude: float) -> int:
        """Sets the reference amplitude.

        Args:
            amplitude (float): The amplitude in volts to set.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SLVL {amplitude:.3f}")

    """ INPUT AND FILTER
    """

    @mark_query
    def get_input_configuration(self) -> InputConfiguration:
        """Queries the input configuration.

        Returns:
            InputConfiguration: The current input configuration.
        """
        return InputConfiguration.from_raw_value(int(self.query("ISRC?")))

    @mark_command
    def set_input_configuration(self, configuration: InputConfiguration) -> int:
        """Sets the input configuration.

        Args:
            configuration (InputConfiguration): The input configuration to set.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"ISRC {configuration.raw_value}")

    @mark_query
    def get_input_grounding(self) -> InputGrounding:
        """Queries the input grounding configuration.

        Returns:
            InputGrounding: The current input grounding configuration.
        """
        return InputGrounding.from_raw_value(int(self.query("IGND?")))

    @mark_command
    def set_input_grounding(self, configuration: InputGrounding) -> int:
        """Sets the input grounding configuration.

        Args:
            configuration (InputGrounding): The input grounding configuration to set.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"IGND {configuration.raw_value}")

    @mark_query
    def get_input_coupling(self) -> InputCoupling:
        """Queries the input coupling configuration.

        Returns:
            InputCoupling: The current input coupling configuration.
        """
        return InputCoupling.from_raw_value(int(self.query("ICPL?")))

    @mark_command
    def set_input_coupling(self, configuration: InputCoupling) -> int:
        """Sets the input coupling configuration.

        Args:
            configuration (InputCoupling): The input coupling configuration to set.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"ICPL {configuration.raw_value}")

    @mark_query
    def get_notch_filters(self) -> NotchFilter:
        """Queries the notch filter configuration.

        Returns:
            NotchFilters: The current notch filter configuration.
        """
        return NotchFilter.from_raw_value(int(self.query("ILIN?")))

    @mark_command
    def set_notch_filters(self, configuration: NotchFilter) -> int:
        """Sets the notch filter configuration.

        Args:
            configuration (NotchFilters): The notch filter configuration to set.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"ILIN {configuration.raw_value}")

    """ GAIN AND TIME CONSTANT
    """

    @mark_query
    def get_sensitivity(self) -> Sensitivity:
        """Queries the sensitivity setting.

        Returns:
            Sensitivity: The current sensitivity setting.
        """
        return Sensitivity.from_raw_value(int(self.query("SENS?")))

    @mark_command
    def set_sensitivity(self, sensitivity: Sensitivity) -> int:
        """Sets the sensitivity.

        Args:
            sensitivity (Sensitivity): The sensitivity setting to apply.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SENS {sensitivity.raw_value}")

    @mark_query
    def get_dynamic_reserve(self) -> DynamicReserve:
        """Queries the dynamic reserve setting.

        Returns:
            DynamicReserve: The current dynamic reserve setting.
        """
        return DynamicReserve.from_raw_value(int(self.query("RMOD?")))

    @mark_command
    def set_dynamic_reserve(self, reserve: DynamicReserve) -> int:
        """Sets the dynamic reserve.

        Args:
            reserve (DynamicReserve): The dynamic reserve setting to apply.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"RMOD {reserve.raw_value}")

    @mark_query
    def get_time_constant(self) -> TimeConstant:
        """Queries the time constant setting.

        Returns:
            TimeConstant: The current time constant setting.
        """
        return TimeConstant.from_raw_value(int(self.query("OFLT?")))

    @mark_command
    def set_time_constant(self, time_constant: TimeConstant) -> int:
        """Sets the time constant.

        Args:
            time_constant (TimeConstant): The time constant setting to apply.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"OFLT {time_constant.raw_value}")

    @mark_query
    def get_filter_slope(self) -> FilterSlope:
        """Queries the filter slope setting.

        Returns:
            FilterSlope: The current filter slope setting.
        """
        return FilterSlope.from_raw_value(int(self.query("OFSL?")))

    @mark_command
    def set_filter_slope(self, filter_slope: FilterSlope) -> int:
        """Sets the filter slope.

        Args:
            filter_slope (FilterSlope): The filter slope setting to apply.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"OFSL {filter_slope.raw_value}")

    @mark_query
    def get_sync_filter_state(self) -> SyncFilterState:
        """Queries the state of the synchronization filter.

        Returns:
            SyncFilterState: The current state of the synchronization filter.
        """
        return SyncFilterState.from_raw_value(int(self.query("SYNC?")))

    @mark_command
    def set_sync_filter_state(self, state: SyncFilterState) -> int:
        """Sets the state of the synchronization filter.

        Args:
            state (SyncFilterState): The synchronization filter state to apply.

        Returns:
            int: Status code indicating the success of the operation.
        """
        return self.command(f"SYNC {state.raw_value}")

    @mark_query
    def get_output(self, parameter: int) -> float:
        return float(self.query(f"OUTP? {parameter}"))

    @mark_query
    def get_display_output(self, parameter: int) -> float:
        return float(self.query(f"OUTR? {parameter}"))

    @mark_query
    def get_x(self) -> float:
        return float(self.query("OUTP? 1"))

    @mark_query
    def get_y(self) -> float:
        return float(self.query("OUTP? 2"))

    @mark_query
    def get_xy(self) -> list[float]:
        return [float(s) for s in self.query("SNAP? 1,2").split(",")]

    @mark_query
    def get_display_buffer_length(self) -> int:
        return int(self.query("SPTS?"))
