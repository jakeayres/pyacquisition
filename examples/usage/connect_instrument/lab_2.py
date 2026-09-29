from dataclasses import dataclass

from pyacquisition import Experiment, Measurement, Task
from pyacquisition.instruments import Keithley_2000
from pyacquisition.tasks import NewFile, WaitFor


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

        dmm = Keithley_2000("dmm", "GPIB0::16::INSTR", timeout=10000)
        self.add_instrument(dmm)
        self.add_measurement(Measurement("v", dmm.get_reading, unit="V"))

    def teardown(self):
        lockin = self.instruments["lockin"]
        lockin.set_reference_amplitude(0.004)
        print("The lock-in's output is turned down.")


if __name__ == "__main__":
    Lab.from_config("rig.toml").run()
