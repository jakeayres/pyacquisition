from dataclasses import dataclass

from pyacquisition import Experiment, Measurement, Task, Trace
from pyacquisition.instruments import Clock
from pyacquisition.instruments.lakeshore.lakeshore_350 import InputChannel
from pyacquisition.tasks import AcquireTrace
from set_temperature import SetTemperature
from simulated import SimulatedCryostat, SimulatedSpectrometer


# --8<-- [start:sweep]
@dataclass
class SpectrumSweep(Task):
    """Take a spectrum at each temperature from low to high."""

    low: float
    high: float
    step: float

    @property
    def description(self):
        return f"Spectra from {self.low} to {self.high} K"

    async def run(self, experiment):
        points = round((self.high - self.low) / self.step) + 1
        for i in range(points):
            kelvin = self.low + i * self.step
            await self.run_subtask(SetTemperature(kelvin))
            await self.run_subtask(AcquireTrace(trace="spectrum"))
            self.log(f"Spectrum {i + 1} of {points}, at {kelvin:g} K")
        # --8<-- [end:sweep]


class MyExperiment(Experiment):
    data_path = "my_data"
    gui_log_level = "INFO"

    def setup(self):
        clock = Clock("clock")
        self.add_instrument(clock)

        cryostat = SimulatedCryostat("lakeshore")
        self.add_instrument(cryostat)

        spectrometer = SimulatedSpectrometer("spectrometer", cryostat)
        self.add_instrument(spectrometer)

        self.add_measurement(Measurement("time", clock.time))
        self.add_measurement(
            Measurement(
                "T",
                cryostat.get_temperature,
                input_channel=InputChannel.INPUT_A,
                unit="K",
            )
        )

        # --8<-- [start:trace]
        self.add_trace(
            Trace("spectrum", spectrometer.get_spectrum, reduce=["peak_x"])
        )
        # --8<-- [end:trace]

        self.register_task(SetTemperature, label="Set Temperature")
        self.register_task(SpectrumSweep, label="Spectrum Sweep")


if __name__ == "__main__":
    MyExperiment().run()
