from pyacquisition import Experiment, Measurement
from pyacquisition.instruments import SR_830, Lakeshore_350


class MyExperiment(Experiment):
    data_path = "my_data"

    def setup(self):
        lockin = SR_830("lockin", "GPIB0::7::INSTR")
        self.add_instrument(lockin)
        self.add_measurement(Measurement("x", lockin.get_x))
        self.add_measurement(Measurement("y", lockin.get_y))

        cryo = Lakeshore_350("lakeshore", "GPIB0::12::INSTR")
        self.add_instrument(cryo)
        self.add_measurement(
            Measurement("T", cryo.get_temperature, input_channel="INPUT_A")
        )


if __name__ == "__main__":
    MyExperiment().run()
