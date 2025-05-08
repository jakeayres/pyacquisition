from ...core.instrument import BaseEnum, Instrument, mark_query


class SystemStatusM(BaseEnum):
    NORMAL = (0, "Normal")
    QUENCHED = (1, "Quenched")
    OVERHEATED = (2, "Overheated")
    WARMING_UP = (4, "Warming up")
    FAULT = (8, "Fault")


class SystemStatusN(BaseEnum):
    NORMAL = (0, "Normal")
    POSITIVE_VOLTAGE_LIMIT = (1, "On positive voltage limit")
    NEGATIVE_VOLTAGE_LIMIT = (2, "On negative voltage limit")
    NEGATIVE_CURRENT_LIMIT = (4, "Outside negative current limit")
    POSITIVE_CURRENT_LIMIT = (8, "Outside positive current limit")


class ActivityStatus(BaseEnum):
    HOLD = (0, "Hold")
    TO_SETPOINT = (1, "To setpoint")
    TO_ZERO = (2, "To zero")
    CLAMPED = (4, "Clamped")


class RemoteStatus(BaseEnum):
    LOCAL_LOCKED = (0, "Local and locked")
    REMOTE_LOCKED = (1, "Remote and locked")
    LOCAL_UNLOCKED = (2, "Local and unlocked")
    REMOTE_UNLOCKED = (3, "Remote and unlocked")


class SwitchHeaterStatus(BaseEnum):
    OFF_AT_ZERO = (0, "Off (closed) at zero field")
    ON = (1, "On (open)")
    OFF_AT_FIELD = (2, "Off (closed) at field")
    FAULT = (3, "Fault")
    NOT_FITTED = (4, "Not fitted")


class ModeStatusM(BaseEnum):
    FAST_AMPS = (0, "Fast sweep (amps)")
    FAST_TESLA = (1, "Fast sweep (tesla)")
    SLOW_AMPS = (4, "Slow sweep (amps)")
    SLOW_TESLA = (5, "Slow sweep (tesla)")


class ModeStatusN(BaseEnum):
    REST = (0, "At rest (constant output)")
    SWEEPING = (1, "Sweeping")
    LIMITING = (2, "Sweep limiting")
    SWEEPING_LIMITING = (3, "Sweeping and sweep limiting")


class Mercury_IPS(Instrument):
    """Class for controlling the Oxford Instruments Mercury IPS device."""

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
        return self.query("C1")

    @mark_query
    def local_and_unlocked(self) -> str:
        """Sets the device to local and unlocked mode.

        Returns:
            str: The response.
        """
        return self.query("C2")

    @mark_query
    def remote_and_unlocked(self) -> str:
        """Sets the device to remote and unlocked mode.

        Returns:
            str: The response.
        """
        return self.query("C3")

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
