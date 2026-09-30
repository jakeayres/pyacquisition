import time
from dataclasses import dataclass

from pyacquisition import Experiment, Task
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

    sample = "A"
    console_log_level = "INFO"
    api_server_port = 8001
    api_server_fallback_ports = (8002, 8003)
    measurement_period = 0.5

    @property
    def data_path(self):
        return f"data/sample_{self.sample}/{time.strftime('%Y-%m-%d')}"

    def setup(self):
        lockin = self.instruments["lockin"]
        lockin.set_frequency(137.0)

        self.add_calculation(lambda row: {"power": row["wave"] ** 2})
        self.register_task(Record, label="Record")

    def teardown(self):
        lockin = self.instruments["lockin"]
        lockin.set_reference_amplitude(0.004)
        print("The lock-in's output is turned down.")


if __name__ == "__main__":
    Lab.from_config("rig.toml").run()
