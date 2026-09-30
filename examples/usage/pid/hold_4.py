from furnace import Furnace
from pyacquisition import Experiment, Measurement
from pyacquisition.core.instrument import (
    SoftwareInstrument,
    mark_command,
    mark_query,
)
from pyacquisition.instruments import Clock
from pyacquisition.tasks import PID


class Hold(Experiment):
    """A furnace, held at a temperature by a PID."""

    def setup(self):
        clock = Clock("clock")
        furnace = Furnace("furnace")
        self.add_instrument(clock)
        self.add_instrument(furnace)

        pid = PID(
            read=furnace.temperature,
            write=furnace.set_power,
            setpoint=60.0,
            kp=5.0,
            ki=0.5,
            output_min=0.0,
            output_max=100.0,
            label="furnace",
        )
        self.add_task_manager("control").add_task(pid)
        self.add_instrument(Controls("pid", pid))

        self.add_measurement(Measurement("time", clock.time, unit="s"))
        self.add_measurement(
            Measurement("temperature", furnace.temperature, unit="°C")
        )
        self.add_measurement(Measurement("power", lambda: pid.output, unit="%"))
        self.add_measurement(
            Measurement("setpoint", lambda: pid.setpoint, unit="°C")
        )


class Controls(SoftwareInstrument):
    """The PID's setpoint and gains, to change from the Instruments tab."""

    name = "PID Controls"

    def __init__(self, uid, pid):
        super().__init__(uid)
        self._pid = pid

    @mark_query
    def get_setpoint(self) -> float:
        """The temperature the PID holds, in degrees C."""
        return self._pid.setpoint

    @mark_command
    def set_setpoint(self, celsius: float) -> None:
        """Sets the temperature to hold, in degrees C."""
        self._pid.setpoint = celsius

    @mark_command
    def set_gains(self, kp: float, ki: float) -> None:
        """Sets the proportional and integral gains."""
        self._pid.kp = kp
        self._pid.ki = ki


if __name__ == "__main__":
    Hold().run()
