from pyacquisition import Experiment, Measurement
from pyacquisition.instruments import (
    SR_830,
    Clock,
    Lakeshore_350,
    PIDController,
)
from pyacquisition.tasks import PID

# The thermometer's current, in amps: here the lock-in's 1 V sine output,
# through a 10 MΩ resistor in series. Set it for your own circuit.
EXCITATION = 100e-9
HEATER = Lakeshore_350.OutputChannel.OUTPUT_1


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

        lockin.set_reference_amplitude(1.0)
        lockin.set_sensitivity(SR_830.Sensitivity.uV_500)
        lockin.set_time_constant(SR_830.TimeConstant.ms_100)

        def resistance():
            """The thermometer's resistance, in ohms."""
            return lockin.get_x() / EXCITATION

        lakeshore.set_control_mode(HEATER, Lakeshore_350.ControlMode.OPEN_LOOP)
        lakeshore.set_manual_output(HEATER, 0.0)
        # The range whose power suits your heater and stage: start low
        lakeshore.set_heater_range(HEATER, Lakeshore_350.HeaterRange.RANGE_3)

        def heater(percent):
            """Sets the heater's output, in percent of its range."""
            lakeshore.set_manual_output(HEATER, percent)

        pid = PID(
            read=resistance,
            write=heater,
            setpoint=1650.0,  # ohms: your thermometer at the temperature you want
            kp=1.0,  # percent per ohm: a start, to tune on your cryostat
            ki=0.2,
            output_min=0.0,
            output_max=100.0,
            inverted=True,
            label="sample",
        )
        self.add_task_manager("control").add_task(pid)
        controller = PIDController("pid", pid)
        self.add_instrument(controller)

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
            Measurement("setpoint", controller.get_setpoint, unit="Ω")
        )

    def teardown(self):
        lakeshore = self.instruments["lakeshore"]
        lakeshore.set_heater_range(HEATER, Lakeshore_350.HeaterRange.OFF)
        print("The heater is off.")


if __name__ == "__main__":
    Hold().run()
