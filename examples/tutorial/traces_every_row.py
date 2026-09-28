from pyacquisition import Experiment, Measurement, Trace
from pyacquisition.instruments import Clock
from pyacquisition.instruments.lakeshore.lakeshore_350 import InputChannel
from simulated import SimulatedCryostat, SimulatedSpectrometer
from step_4_first_task import SetTemperature


class MyExperiment(Experiment):
    data_path = "my_data"
    gui_log_level = "INFO"
    measurement_period = 0.5

    def setup(self):
        clock = Clock("clock")
        self.add_instrument(clock)

        cryostat = SimulatedCryostat("lakeshore")
        self.add_instrument(cryostat)

        spectrometer = SimulatedSpectrometer(
            "spectrometer", cryostat, sweep_time=0.2
        )
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
            Trace(
                "spectrum",
                spectrometer.get_spectrum,
                every_rows=1,
                reduce=["mean", "peak_x"],
            )
        )
        # --8<-- [end:trace]

        self.register_task(SetTemperature, label="Set Temperature")


if __name__ == "__main__":
    MyExperiment().run()
