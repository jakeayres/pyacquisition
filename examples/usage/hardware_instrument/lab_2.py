from dataclasses import dataclass

from keithley_2400 import Keithley_2400
from pyacquisition import Experiment, Measurement, Task
from pyacquisition.tasks import NewFile, WaitFor

# What a 2400 answers :READ? with, for the mock to give back
READING = (
    "+1.000000E+00,+1.021450E-06,+9.910000E+37,+2.515590E+03,+2.150800E+04"
)


@dataclass
class Record(Task):
    """Record a few files, one after another."""

    files: int = 3
    seconds: int = 10

    async def run(self, experiment):
        for i in range(self.files):
            await self.run_subtask(NewFile(file_name=f"run {i + 1}"))
            await self.run_subtask(WaitFor(seconds=self.seconds))
            self.log(f"Recorded {i + 1} of {self.files}")


class Lab(Experiment):
    """The rig is in rig.toml. What a file can't say goes here."""

    def setup(self):
        lockin = self.instruments["lockin"]
        lockin.set_frequency(137.0)

        self.add_calculation(lambda row: {"power": row["wave"] ** 2})
        self.register_task(Record, label="Record")

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
