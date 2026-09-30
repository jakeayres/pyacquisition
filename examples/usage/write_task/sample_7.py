from dataclasses import dataclass

from pyacquisition import Experiment, Measurement, Task
from pyacquisition.instruments import SR_830, Clock, Lakeshore_350

# The Lakeshore's input for the sample's thermometer, and its heater's loop
SENSOR = Lakeshore_350.InputChannel.INPUT_A
LOOP = Lakeshore_350.OutputChannel.OUTPUT_1


@dataclass
class SetTemperature(Task):
    """Take the sample to a temperature, and wait until it is there."""

    kelvin: float
    rate: float = 30.0  # kelvin per minute
    tolerance: float = 0.05  # kelvin

    def __post_init__(self):
        super().__post_init__()
        if not 1.5 <= self.kelvin <= 300:
            raise ValueError(f"{self.kelvin} K is out of range: 1.5 to 300 K.")

    @property
    def description(self):
        return f"Go to {self.kelvin} K"

    async def run(self, experiment):
        cryostat = experiment.instruments["cryostat"]
        start = cryostat.get_temperature(SENSOR)
        cryostat.set_ramp(LOOP, Lakeshore_350.State.ON, self.rate)
        cryostat.set_setpoint(LOOP, self.kelvin)
        self.log(f"Ramping to {self.kelvin} K at {self.rate} K/min")

        def arrived():
            kelvin = cryostat.get_temperature(SENSOR)
            done = (kelvin - start) / (self.kelvin - start or 1)
            self.set_progress(done, note=f"{kelvin:.2f} K")
            return abs(kelvin - self.kelvin) <= self.tolerance

        await self.wait_until(arrived, timeout=3600)
        self.log(f"At {self.kelvin} K")

    def on_pause(self, experiment):
        self.hold(experiment)

    def on_resume(self, experiment):
        cryostat = experiment.instruments["cryostat"]
        cryostat.set_setpoint(LOOP, self.kelvin)
        self.log(f"Ramping to {self.kelvin} K again")

    async def teardown(self, experiment):
        self.hold(experiment)

    def hold(self, experiment):
        """Stops the ramp where it has got to."""
        cryostat = experiment.instruments["cryostat"]
        here = cryostat.get_setpoint(LOOP)
        cryostat.set_setpoint(LOOP, here)
        self.log(f"Holding at {here:.2f} K")


class Sample(Experiment):
    """A sample in a cryostat, measured with a lock-in."""

    def setup(self):
        clock = Clock("clock")
        # Your instruments' addresses
        cryostat = Lakeshore_350("cryostat", "GPIB0::12::INSTR")
        lockin = SR_830("lockin", "GPIB0::8::INSTR")
        self.add_instrument(clock)
        self.add_instrument(cryostat)
        self.add_instrument(lockin)

        self.add_measurement(Measurement("time", clock.time, unit="s"))
        self.add_measurement(Measurement("x", lockin.get_x, unit="V"))
        self.add_measurement(Measurement("y", lockin.get_y, unit="V"))
        self.add_measurement(
            Measurement(
                "T",
                cryostat.get_temperature,
                input_channel=SENSOR,
                unit="K",
            )
        )

        self.register_task(SetTemperature, label="Set Temperature")


if __name__ == "__main__":
    Sample().run()
