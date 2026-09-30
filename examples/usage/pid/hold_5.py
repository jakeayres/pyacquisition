from pyacquisition import Experiment, Measurement
from pyacquisition.core.instrument import (
    SoftwareInstrument,
    mark_command,
    mark_query,
)
from pyacquisition.instruments import SR_830, Clock, Lakeshore_350
from pyacquisition.tasks import PID
from stage import SimulatedStage

EXCITATION = 100e-9  # amps: the lock-in's 1 V sine out, through 10 MΩ
HEATER = Lakeshore_350.OutputChannel.OUTPUT_1


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

        lakeshore.set_control_mode(HEATER, Lakeshore_350.ControlMode.OPEN_LOOP)
        lakeshore.set_manual_output(HEATER, 0.0)
        lakeshore.set_heater_range(HEATER, Lakeshore_350.HeaterRange.RANGE_3)

        def heater(percent):
            """Sets the heater's output, in percent of its range."""
            lakeshore.set_manual_output(HEATER, percent)

        pid = PID(
            read=resistance,
            write=heater,
            setpoint=1650.0,
            kp=1.0,
            ki=0.2,
            output_min=0.0,
            output_max=100.0,
            inverted=True,
            label="sample",
        )
        self.add_task_manager("control").add_task(pid)
        self.add_instrument(Controls("pid", pid))

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
        self.add_measurement(
            Measurement(
                "heater",
                lakeshore.get_heater_output,
                unit="%",
                output_channel=HEATER,
            )
        )
        self.add_measurement(
            Measurement("setpoint", lambda: pid.setpoint, unit="Ω")
        )

    def teardown(self):
        lakeshore = self.instruments["lakeshore"]
        lakeshore.set_heater_range(HEATER, Lakeshore_350.HeaterRange.OFF)
        print("The heater is off.")


class Controls(SoftwareInstrument):
    """The PID's setpoint and gains, to change from the Instruments tab."""

    name = "PID Controls"

    def __init__(self, uid, pid):
        super().__init__(uid)
        self._pid = pid

    @mark_query
    def get_setpoint(self) -> float:
        """The thermometer's resistance the PID holds, in ohms."""
        return self._pid.setpoint

    @mark_command
    def set_setpoint(self, ohms: float) -> None:
        """Sets the thermometer's resistance to hold, in ohms."""
        self._pid.setpoint = ohms

    @mark_command
    def set_gains(self, kp: float, ki: float) -> None:
        """Sets the proportional and integral gains."""
        self._pid.kp = kp
        self._pid.ki = ki


if __name__ == "__main__":
    Hold().run()
