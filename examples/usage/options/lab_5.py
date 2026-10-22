import time
from dataclasses import dataclass

from pyacquisition import Experiment, Task
from pyacquisition.tasks import NewFile


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
        self.register_task(FrequencySweep, label="Frequency Sweep")

    def teardown(self):
        lockin = self.instruments["lockin"]
        lockin.set_reference_amplitude(0.004)
        print("The lock-in's output is turned down.")


if __name__ == "__main__":
    Lab.from_config("rig.toml").run()
