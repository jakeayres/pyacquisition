from pyacquisition import Experiment
from pyacquisition.instruments import SR_830, Clock, Lakeshore_350


class Hold(Experiment):
    """A sample held at a temperature by a PID, through its thermometer."""

    def setup(self):
        clock = Clock("clock")
        # Your instruments' addresses
        lockin = SR_830("lockin", "GPIB0::8::INSTR")
        lakeshore = Lakeshore_350("lakeshore", "GPIB0::12::INSTR")
        self.add_instrument(clock)
        self.add_instrument(lockin)
        self.add_instrument(lakeshore)


if __name__ == "__main__":
    Hold().run()
