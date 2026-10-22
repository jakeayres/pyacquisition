from dataclasses import dataclass

from pyacquisition import Experiment, Task


@dataclass
class FrequencySweep(Task):
    """Sweep the lock-in's frequency at one amplitude, into a file of its own."""

    async def run(self, experiment):
        pass


class Lab(Experiment):
    """The rig is in rig.toml. What a file can't say goes here."""

    def setup(self):
        lockin = self.instruments["lockin"]
        lockin.set_frequency(137.0)

        self.add_calculation(lambda row: {"power": row["wave"] ** 2})

    def teardown(self):
        lockin = self.instruments["lockin"]
        lockin.set_reference_amplitude(0.004)
        print("The lock-in's output is turned down.")


if __name__ == "__main__":
    Lab.from_config("rig.toml").run()
