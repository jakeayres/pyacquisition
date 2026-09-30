from pyacquisition import Experiment
from pyacquisition.instruments import SR_830, Clock, Lakeshore_350
from stage import SimulatedStage


class Hold(Experiment):
    """A sample held at a temperature by a PID, through its thermometer."""

    def setup(self):
        stage = SimulatedStage()  # the cryostat, simulated
        clock = Clock("clock")
        # On the rig, give each its address, such as "GPIB0::8::INSTR"
        lockin = SR_830("lockin", stage.lockin)
        lakeshore = Lakeshore_350("lakeshore", stage.lakeshore)
        self.add_instrument(clock)
        self.add_instrument(lockin)
        self.add_instrument(lakeshore)


if __name__ == "__main__":
    Hold().run()
