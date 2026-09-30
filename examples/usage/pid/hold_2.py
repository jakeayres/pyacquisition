from pyacquisition import Experiment, Measurement
from pyacquisition.instruments import SR_830, Clock, Lakeshore_350
from stage import SimulatedStage

EXCITATION = 100e-9  # amps: the lock-in's 1 V sine out, through 10 MΩ


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

        lockin.set_reference_amplitude(1.0)
        lockin.set_sensitivity(SR_830.Sensitivity.uV_500)
        lockin.set_time_constant(SR_830.TimeConstant.ms_100)

        def resistance():
            """The thermometer's resistance, in ohms."""
            return lockin.get_x() / EXCITATION

        self.add_measurement(Measurement("time", clock.time, unit="s"))
        self.add_measurement(Measurement("R", resistance, unit="Ω"))
        self.add_measurement(
            Measurement(
                "T",
                lakeshore.get_temperature,
                unit="K",
                input_channel=Lakeshore_350.InputChannel.INPUT_A,
            )
        )


if __name__ == "__main__":
    Hold().run()
