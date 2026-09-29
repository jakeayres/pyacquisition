from dataclasses import dataclass

from pyacquisition import Experiment, Measurement, Task
from pyacquisition.tasks import NewFile, WaitFor
from thermometer import Sensor, Thermometer


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

        thermometer = Thermometer("thermometer")
        self.add_instrument(thermometer)
        temperature = thermometer.get_temperature
        self.add_measurement(
            Measurement("T_sample", temperature, sensor=Sensor.SAMPLE, unit="K")
        )
        self.add_measurement(
            Measurement("T_stage", temperature, sensor=Sensor.STAGE, unit="K")
        )

    def teardown(self):
        lockin = self.instruments["lockin"]
        lockin.set_reference_amplitude(0.004)
        print("The lock-in's output is turned down.")


if __name__ == "__main__":
    Lab.from_config("rig.toml").run()
