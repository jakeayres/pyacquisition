"""Tasks that sweep a magnet powered by an Oxford Instruments Mercury IPS.

The sweep is a sequence of small tasks. Each one that moves the magnet knows what
pausing it means: a pause puts the magnet on hold, and a resume sends it on its way
again, after checking that the system is normal. A task made of them, such as
`SweepMagneticField`, needs no hooks of its own.

These are also a worked example of writing a task that controls hardware. Every
value that matters is read back and checked with `self.expect()`.
"""

from dataclasses import dataclass

from ..core import Task
from ..instruments.oxford_instruments.mercury_ips import (
    ActivityStatus,
    Mercury_IPS,
    ModeStatusN,
    SwitchHeaterStatus,
    SystemStatusM,
)
from .files import NewFile
from .ramps import ramp_progress


def _read(psu, getter: str):
    """A reading for the progress, or None if it can't be had. The progress is
    only shown, so a failed reading must not stop the sweep."""
    try:
        return getattr(psu, getter)()
    except Exception:  # noqa: BLE001
        return None


class _Sweep:
    """Follows a sweep from where it started to where it is going, for the
    task's progress, at the rate the magnet was set to when it started."""

    def __init__(self, task, psu, target):
        self.task = task
        self.psu = psu
        self.target = target
        self.start = _read(psu, "get_output_field")
        rate = _read(psu, "get_field_sweep_rate")  # tesla a minute
        self.per_second = rate / 60 if isinstance(rate, (int, float)) else 0.0

    def show(self):
        now = _read(self.psu, "get_output_field")
        if not isinstance(now, (int, float)) or not isinstance(self.start, (int, float)):
            return
        fraction, remaining = ramp_progress(
            self.start, now, self.target, per_second=self.per_second
        )
        self.task.set_progress(fraction, remaining=remaining, note=f"{now:g} T")


@dataclass
class RampMagnet(Task):
    """Sweep the magnet to a field. Pausing holds it, and resuming sends it on."""

    magnet_psu: str
    setpoint: float

    @property
    def description(self) -> str:
        return f"Sweeping field to {self.setpoint} T"

    async def run(self, experiment):
        psu = experiment.instruments[self.magnet_psu]

        psu.set_target_field(self.setpoint)
        await self.sleep(1)
        self.expect(psu.get_setpoint_field(), self.setpoint, "Setpoint")

        psu.to_setpoint()
        await self.sleep(1)
        self.expect(psu.get_activity_status(), ActivityStatus.TO_SETPOINT, "Activity")

        self.log(f"Sweeping field to {self.setpoint} T")
        sweep = _Sweep(self, psu, self.setpoint)

        def arrived():
            sweep.show()
            return psu.get_sweep_status() == ModeStatusN.REST

        await self.wait_until(arrived)
        self.log(f"Reached setpoint field of {self.setpoint} T")

    def on_pause(self, experiment):
        experiment.instruments[self.magnet_psu].hold()

    def on_resume(self, experiment):
        psu = experiment.instruments[self.magnet_psu]
        # A quench or a fault while it was held must not be followed by a sweep.
        self.expect(psu.get_system_status(), SystemStatusM.NORMAL, "System status")
        psu.to_setpoint()

    async def teardown(self, experiment):
        experiment.instruments[self.magnet_psu].hold()


@dataclass
class RampMagnetToZero(Task):
    """Sweep the magnet to zero field. Pausing holds it, and resuming sends it on."""

    magnet_psu: str

    @property
    def description(self) -> str:
        return "Sweeping field to 0 T"

    async def run(self, experiment):
        psu = experiment.instruments[self.magnet_psu]

        psu.to_zero()
        await self.sleep(1)
        self.expect(psu.get_activity_status(), ActivityStatus.TO_ZERO, "Activity")

        self.log("Sweeping field to 0 T")
        sweep = _Sweep(self, psu, 0.0)

        def arrived():
            sweep.show()
            return psu.get_sweep_status() == ModeStatusN.REST

        await self.wait_until(arrived)
        self.log("Reached zero field")

    def on_pause(self, experiment):
        experiment.instruments[self.magnet_psu].hold()

    def on_resume(self, experiment):
        psu = experiment.instruments[self.magnet_psu]
        self.expect(psu.get_system_status(), SystemStatusM.NORMAL, "System status")
        psu.to_zero()

    async def teardown(self, experiment):
        experiment.instruments[self.magnet_psu].hold()


# The stages of SweepMagneticField, for its progress: check the magnet, switch
# the heater on, sweep up, sweep back down, and switch the heater off.
STAGES = 5


@dataclass
class SweepMagneticField(Task):
    """Sweep magnetic field to setpoint, and then back to zero.

    It checks the magnet before it starts and afterwards, switches the switch heater
    on and off around the sweep, and reads back and checks what it sets. Pausing
    holds the magnet, wherever in the sweep it is, and resuming carries on.

    Registered by itself when there is a Mercury IPS.

    Args:
        magnet_psu (str): The id of the Mercury IPS.
        setpoint (float): The field to sweep to, in tesla.
        ramp_rate (float): The sweep rate, in tesla per minute.
        new_chapter (bool): Not used.
    """

    applies_to = {"magnet_psu": (Mercury_IPS,)}

    magnet_psu: str
    setpoint: float
    ramp_rate: float
    new_chapter: bool = False

    @property
    def description(self) -> str:
        return f"Sweeping field to {self.setpoint} T at {self.ramp_rate} T/min"

    async def run(self, experiment):
        psu = experiment.instruments[self.magnet_psu]

        # Set the magnet to 'HOLD' (in case it is clamped), and check it is fit to move
        self.set_progress(0, of=STAGES, note="Checking the magnet")
        self.log('Setting magnet to "hold"')
        psu.hold()
        await self.sleep(1)
        self.expect(psu.get_system_status(), SystemStatusM.NORMAL, "System status")
        self.expect(psu.get_activity_status(), ActivityStatus.HOLD, "Activity")

        self.set_progress(1, of=STAGES, note="Switching the switch heater on")
        self.log("Switching switch heater on")
        psu.heater_on()
        await self.sleep(15)
        self.expect(
            psu.get_switch_heater_status(), SwitchHeaterStatus.ON, "Switch heater"
        )

        psu.set_field_sweep_rate(self.ramp_rate)
        await self.sleep(1)
        self.expect(psu.get_field_sweep_rate(), self.ramp_rate, "Ramp rate")

        self.set_progress(2, of=STAGES, note=f"Sweeping to {self.setpoint:g} T")
        await self.run_subtask(NewFile(file_name=f"Field Sweep to {self.setpoint}T"))
        await self.run_subtask(RampMagnet(self.magnet_psu, self.setpoint))

        self.set_progress(3, of=STAGES, note="Sweeping to 0 T")
        await self.run_subtask(NewFile(file_name="Field Sweep to 0T"))
        await self.run_subtask(RampMagnetToZero(self.magnet_psu))

        self.set_progress(4, of=STAGES, note="Switching the switch heater off")
        self.log("Switching switch heater off")
        psu.heater_off()
        await self.sleep(15)
        self.expect(
            psu.get_switch_heater_status(),
            SwitchHeaterStatus.OFF_AT_ZERO,
            "Switch heater",
        )
        self.set_progress(STAGES, of=STAGES)

    async def teardown(self, experiment):
        psu = experiment.instruments[self.magnet_psu]
        psu.hold()  # however it ended, the magnet must not be left sweeping
        self.log(f"Magnet status: {psu.get_activity_status().name}")
        # A quench or a fault shows here, and fails the task.
        self.expect(psu.get_system_status(), SystemStatusM.NORMAL, "System status")
