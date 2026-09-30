from furnace import Furnace
from pyacquisition import Experiment, Measurement
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

        self.add_measurement(Measurement("time", clock.time, unit="s"))
        self.add_measurement(
            Measurement("temperature", furnace.temperature, unit="°C")
        )


if __name__ == "__main__":
    Hold().run()
