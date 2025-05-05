from enum import Enum
from typing import Union, Tuple
from ...core.instrument import Instrument, mark_query, mark_command


class SystemStatusM(Enum):
    NORMAL = 0
    QUENCHED = 1
    OVERHEATED = 2
    WARMING_UP = 4
    FAULT = 8


class SystemStatusMModel(Enum):
    NORMAL = 'Normal'
    QUENCHED = 'Quenched'
    OVERHEATED = 'Overheaded'
    WARMING_UP = 'Warming up'
    FAULT = 'Fault'


class SystemStatusN(Enum):
    NORMAL = 0
    POSITIVE_VOLTAGE_LIMIT = 1
    NEGATIVE_VOLTAGE_LIMIT = 2
    NEGATIVE_CURRENT_LIMIT = 4
    POSITIVE_CURRENT_LIMIT = 8


class SystemStatusNModel(Enum):
    NORMAL = 'Normal'
    POSITIVE_VOLTAGE_LIMIT = 'On positive voltage limit'
    NEGATIVE_VOLTAGE_LIMIT = 'On negative voltage limit'
    NEGATIVE_CURRENT_LIMIT = 'Outside negative current limit'
    POSITIVE_CURRENT_LIMIT = 'Outside positive current limit'


class ActivityStatus(Enum):
    HOLD = 0
    TO_SETPOINT = 1
    TO_ZERO = 2
    CLAMPED = 4


class ActivityStatusModel(Enum):
    HOLD = 'Hold'
    TO_SETPOINT = 'To setpoint'
    TO_ZERO = 'To zero'
    CLAMPED = 'Clamped'


class RemoteStatus(Enum):
    LOCAL_LOCKED = 0
    REMOTE_LOCKED = 1
    LOCAL_UNLOCKED = 2
    REMOTE_UNLOCKED = 3


class RemoteStatusModel(Enum):
    LOCAL_LOCKED = 'Local and locked'
    REMOTE_LOCKED = 'Remote and locked'
    LOCAL_UNLOCKED = 'Local and unlocked'
    REMOTE_UNLOCKED = 'Remote and unlocked'


class SwitchHeaterStatus(Enum):
    OFF_AT_ZERO = 0
    ON = 1
    OFF_AT_FIELD = 2
    FAULT = 3
    NOT_FITTED = 4


class SwitchHeaterStatusModel(Enum):
    OFF_AT_ZERO = 'Off (closed) at zero field'
    ON = 'On (open)'
    OFF_AT_FIELD = 'Off (closed) at field'
    FAULT = 'Fault'
    NOT_FITTED = 'Not fitted'


class ModeStatusM(Enum):
    FAST_AMPS = 0
    FAST_TESLA = 1
    SLOW_AMPS = 4
    SLOW_TESLA = 5


class ModeStatusMModel(Enum):
    FAST_AMPS = 'Fast sweep (amps)'
    FAST_TESLA = 'Fast sweep (tesla)'
    SLOW_AMPS = 'Slow sweep (amps)'
    SLOW_TESLA = 'Slow sweep (tesla)'


class ModeStatusN(Enum):
    REST = 0
    SWEEPING = 1
    LIMITING = 2
    SWEEPING_LIMITING = 3


class ModeStatusNModel(Enum):
    REST = 'At rest (constant output)'
    SWEEPING = 'Sweeping'
    LIMITING = 'Sweep limiting'
    SWEEPING_LIMITING = 'Sweeping and sweep limiting'



class Mercury_IPS(Instrument):
    """Class for controlling the Oxford Instruments Mercury IPS device."""

    name = 'Mercury_IPS'

    @mark_query
    def identify(self) -> str:
        """Identifies the device.

        Returns:
            str: The identification string.
        """
        return self.query("*IDN?")

    @mark_query
    def remote_and_locked(self) -> str:
        """Sets the device to remote and locked mode.

        Returns:
            str: The response.
        """
        return self.query('C1')

    @mark_query
    def local_and_unlocked(self) -> str:
        """Sets the device to local and unlocked mode.

        Returns:
            str: The response.
        """
        return self.query('C2')

    @mark_query
    def remote_and_unlocked(self) -> str:
        """Sets the device to remote and unlocked mode.

        Returns:
            str: The response.
        """
        return self.query('C3')

    @mark_query
    def get_output_current(self) -> float:
        """Gets the output current.

        Returns:
            float: The output current in amperes.
        """
        return float(self.query("R0")[1:])

    @mark_query
    def get_supply_voltage(self) -> float:
        """Gets the supply voltage.

        Returns:
            float: The supply voltage in volts.
        """
        return float(self.query("R1")[1:])

    @mark_query
    def get_magnet_current(self) -> float:
        """Gets the magnet current.

        Returns:
            float: The magnet current in amperes.
        """
        return float(self.query("R2")[1:])

    @mark_query
    def get_setpoint_current(self) -> float:
        """Gets the setpoint current.

        Returns:
            float: The setpoint current in amperes.
        """
        return float(self.query("R5")[1:])

    @mark_query
    def get_current_sweep_rate(self) -> float:
        """Gets the current sweep rate.

        Returns:
            float: The current sweep rate in amperes per second.
        """
        return float(self.query("R6")[1:])

    @mark_query
    def get_output_field(self) -> float:
        """Gets the output magnetic field.

        Returns:
            float: The output magnetic field in tesla.
        """
        return float(self.query("R7")[1:])

    @mark_query
    def get_setpoint_field(self) -> float:
        """Gets the setpoint magnetic field.

        Returns:
            float: The setpoint magnetic field in tesla.
        """
        return float(self.query("R8")[1:])

    @mark_query
    def get_field_sweep_rate(self) -> float:
        """Gets the field sweep rate.

        Returns:
            float: The field sweep rate in tesla per second.
        """
        return float(self.query("R9")[1:])

    @mark_query
    def get_software_voltage_limit(self) -> float:
        """Gets the software voltage limit.

        Returns:
            float: The software voltage limit in volts.
        """
        return float(self.query("R15")[1:])

    @mark_query
    def get_persistent_current(self) -> float:
        """Gets the persistent current.

        Returns:
            float: The persistent current in amperes.
        """
        return float(self.query("R16")[1:])

    @mark_query
    def get_trip_current(self) -> float:
        """Gets the trip current.

        Returns:
            float: The trip current in amperes.
        """
        return float(self.query("R17")[1:])

    @mark_query
    def get_persistent_field(self) -> float:
        """Gets the persistent magnetic field.

        Returns:
            float: The persistent magnetic field in tesla.
        """
        return float(self.query("R18")[1:])

    @mark_query
    def get_trip_field(self) -> float:
        """Gets the trip magnetic field.

        Returns:
            float: The trip magnetic field in tesla.
        """
        return float(self.query("R19")[1:])

    @mark_query
    def get_switch_heater_current(self) -> float:
        """Gets the switch heater current.

        Returns:
            float: The switch heater current in amperes.
        """
        response = float(self.query("R20")[1:-2])
        return response * 1e-3

    @mark_query
    def get_negative_current_limit(self) -> float:
        """Gets the negative current limit.

        Returns:
            float: The negative current limit in amperes.
        """
        return float(self.query("R21")[1:])

    @mark_query
    def get_positive_current_limit(self) -> float:
        """Gets the positive current limit.

        Returns:
            float: The positive current limit in amperes.
        """
        return float(self.query("R22")[1:])

    @mark_query
    def get_lead_resistance(self) -> float:
        """Gets the lead resistance.

        Returns:
            float: The lead resistance in ohms.
        """
        return float(self.query("R23")[1:-1])

    @mark_query
    def get_magnet_inductance(self) -> float:
        """Gets the magnet inductance.

        Returns:
            float: The magnet inductance in henries.
        """
        return float(self.query("R24")[1:])

    @mark_query
    def hold(self) -> int:
        """Sets the device to hold mode.

        Returns:
            int: The response.
        """
        return self.query("A0")

    @mark_query
    def to_setpoint(self) -> int:
        """Moves the device to the setpoint.

        Returns:
            int: The response.
        """
        return self.query("A1")

    @mark_query
    def to_zero(self) -> int:
        """Moves the device to zero.

        Returns:
            int: The response.
        """
        return self.query("A2")

    @mark_query
    def clamp(self) -> int:
        """Sets the device to clamp mode.

        Returns:
            int: The response.
        """
        return self.query("A4")

    @mark_query
    def switch_heater_off(self) -> str:
        """Turns off the heater.

        Returns:
            str: The response.
        """
        return self.query("H0")

    @mark_query
    def switch_heater_on(self) -> str:
        """Turns on the heater.

        Returns:
            str: The response.
        """
        return self.query("H1")

    @mark_query
    def force_heater_on(self) -> int:
        """Forces the heater to turn on.

        Returns:
            int: The response.
        """
        return self.query("H2")

    @mark_query
    def set_target_current(self, current: float) -> int:
        """Sets the target current.

        Args:
            current (float): The target current in amperes.

        Returns:
            int: The response.
        """
        return self.query(f"I{current:.3f}")

    @mark_query
    def set_target_field(self, field: float) -> int:
        """Sets the target magnetic field.

        Args:
            field (float): The target magnetic field in tesla.

        Returns:
            int: The response.
        """
        return self.query(f"J{field:.3f}")

    @mark_query
    def set_current_sweep_rate(self, rate: float) -> int:
        """Sets the current sweep rate.

        Args:
            rate (float): The current sweep rate in amperes per second.

        Returns:
            int: The response.
        """
        return self.query(f"S{rate:.3f}")

    @mark_query
    def set_field_sweep_rate(self, rate: float) -> int:
        """Sets the field sweep rate.

        Args:
            rate (float): The field sweep rate in tesla per second.

        Returns:
            int: The response.
        """
        return self.query(f"T{rate:.3f}")