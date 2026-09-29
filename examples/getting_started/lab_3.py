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

    def setup(self):
        self.add_calculation(lambda row: {"power": row["wave"] ** 2})


if __name__ == "__main__":
    Lab.from_config("rig.toml").run()
