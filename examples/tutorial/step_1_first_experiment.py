from pyacquisition import Experiment, Measurement
from pyacquisition.instruments import Clock


class MyExperiment(Experiment):
    data_path = "my_data"
    gui_log_level = "INFO"

    def setup(self):
        clock = Clock("clock")
        self.add_instrument(clock)

        self.add_measurement(Measurement("time", clock.time))


if __name__ == "__main__":
    MyExperiment().run()
