from dataclasses import dataclass

from keithley_2400 import Keithley_2400
from pyacquisition import Experiment, Measurement, Task
from pyacquisition.tasks import NewFile

# What a 2400 answers :READ? with, for the mock to give back
READING = (
    "+1.000000E+00,+1.021450E-06,+9.910000E+37,+2.515590E+03,+2.150800E+04"
)


@dataclass
class FrequencySweep(Task):
    """Sweep the lock-in's frequency at one amplitude, into a file of its own."""

    amplitude: float = 0.1  # volts
    start_hz: float = 100.0
    stop_hz: float = 200.0
    points: int = 21
    seconds_per_point: float = 1.0

    async def run(self, experiment):
        lockin = experiment.instruments["lockin"]
        lockin.set_reference_amplitude(self.amplitude)
        lockin.set_frequency(self.start_hz)
        await self.run_subtask(NewFile(file_name=f"{self.amplitude:g} V"))
        step = (self.stop_hz - self.start_hz) / (self.points - 1)
        for i in range(self.points):
            lockin.set_frequency(self.start_hz + i * step)
            await self.sleep(self.seconds_per_point)
        self.log(f"Swept at {self.amplitude:g} V")


class Lab(Experiment):
    """The rig is in rig.toml. What a file can't say goes here."""

    def setup(self):
        lockin = self.instruments["lockin"]
        lockin.set_frequency(137.0)

        self.add_calculation(lambda row: {"power": row["wave"] ** 2})
        self.register_task(FrequencySweep, label="Frequency Sweep")

        smu = Keithley_2400(
            "smu",
            "GPIB0::24::INSTR",
            adapter="mock",
            responses={":READ?": READING},
        )
        self.add_instrument(smu)
        smu.set_voltage(0.0)
        smu.set_output(True)
        self.add_measurement(Measurement("current", smu.get_current, unit="A"))

    def teardown(self):
        lockin = self.instruments["lockin"]
        lockin.set_reference_amplitude(0.004)
        print("The lock-in's output is turned down.")

        smu = self.instruments["smu"]
        smu.set_output(False)
        print("The 2400's output is off.")


if __name__ == "__main__":
    Lab.from_config("rig.toml").run()
