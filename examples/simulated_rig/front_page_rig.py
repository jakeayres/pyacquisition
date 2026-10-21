"""The front page's experiment, with a simulated sample behind its instruments.

The documentation's front page shows `examples/front_page.py` running. What its
interface shows is recorded from this experiment: the same instruments,
measurements and units, with the real `SR_830` and `Lakeshore_350` drivers.
Only their devices are simulated. Each driver talks to a mock resource that
answers its messages from a simulation, so the interface lists every query and
command the real drivers have: the cryostat in simulated.py, and here, a
superconducting film whose voltage the lock-in reads. It loses its resistance
as it cools through its transition, at 75 K.

    uv run examples/simulated_rig/front_page_rig.py
"""

import math
import random

from pyacquisition import Experiment, Measurement
from pyacquisition.core.adapters.mock import MockResource
from pyacquisition.instruments import SR_830, Clock, Lakeshore_350
from pyacquisition.instruments.lakeshore.lakeshore_350 import (
    InputChannel,
    OutputChannel,
    State,
)
from simulated import SimulatedCryostat


class SuperconductingFilm:
    """A thin superconducting film, measured four-wire with a lock-in: an AC
    current through it, and the voltage across it, in phase (x) and out of
    phase (y).

    Above its transition its resistance rises with temperature, as a metal's
    does. Through the transition, over a kelvin or so, it falls to nothing.

    Args:
        cryostat (SimulatedCryostat): Where the film is, for its temperature.
        transition (float): The middle of the transition, in kelvin.
        width (float): How sharp it is, in kelvin.
        current (float): The excitation, in amps.
    """

    def __init__(self, cryostat, transition=75.0, width=0.3, current=10e-6):
        self._cryostat = cryostat
        self._transition = transition
        self._width = width
        self._current = current
        self._frequency = 17.77

    def resistance(self, kelvin: float) -> float:
        """In ohms, at a temperature in kelvin."""
        normal = 0.8 + 0.045 * kelvin
        return normal / (1.0 + math.exp(-(kelvin - self._transition) / self._width))

    def _kelvin(self):
        return self._cryostat.get_temperature(InputChannel.INPUT_A)

    def get_x(self) -> float:
        """The voltage in phase with the current, in volts."""
        return self._current * self.resistance(self._kelvin()) + random.gauss(0.0, 3e-8)

    def get_y(self) -> float:
        """The voltage out of phase: only a little pickup, in volts."""
        return 4e-7 + random.gauss(0.0, 3e-8)

    def get_frequency(self) -> float:
        """The reference frequency, in hertz."""
        return self._frequency


class SimulatedDevice(MockResource):
    """A mock resource whose replies, and what its commands do, come from a
    simulation.

    Args:
        resource_name (str): The address the instrument would have.
        replies (dict): Replies keyed by query header (`"KRDG?"`), each a
            callable taking the normalised query.
        commands (dict): Callables keyed by command header (`"SETP"`), each
            taking the command's arguments as text.
    """

    def __init__(self, resource_name, replies, commands=None):
        super().__init__(resource_name, responses=replies)
        self._commands = commands or {}

    def write(self, message):
        header, _, arguments = message.strip().partition(" ")
        command = self._commands.get(header.upper())
        if command is not None:
            command(arguments.strip())
        return super().write(message)


def lakeshore_device(cryostat, address):
    """A Lakeshore 350's messages, answered by a simulated cryostat."""
    output = OutputChannel.OUTPUT_1

    def set_setpoint(arguments):  # "1,65.000"
        cryostat.set_setpoint(output, float(arguments.split(",")[1]))

    def set_ramp(arguments):  # "1,1,20.000"
        _, state, rate = arguments.split(",")
        cryostat.set_ramp(output, State.from_raw_value(int(state)), float(rate))

    def ramp(_):
        return f"{int(cryostat._ramp_on)},{cryostat.get_ramp(output):.3f}"

    def ramping(_):
        return int(abs(cryostat.get_setpoint(output) - cryostat._target) > 1e-9)

    return SimulatedDevice(
        address,
        replies={
            "KRDG?": lambda _: f"{cryostat.get_temperature(InputChannel.INPUT_A):.4f}",
            "SETP?": lambda _: f"{cryostat.get_setpoint(output):.4f}",
            "RAMP?": ramp,
            "RAMPST?": ramping,
        },
        commands={"SETP": set_setpoint, "RAMP": set_ramp},
    )


def sr_830_device(sample, address):
    """An SR 830's messages, answered from the sample it measures."""
    return SimulatedDevice(
        address,
        replies={
            "OUTP? 1": lambda _: f"{sample.get_x():.6e}",
            "OUTP? 2": lambda _: f"{sample.get_y():.6e}",
            "FREQ?": lambda _: f"{sample.get_frequency():.4f}",
        },
    )


class MyExperiment(Experiment):
    data_path = "my_data"

    def setup(self):
        cryostat = SimulatedCryostat("cryostat", temperature=85.0)
        sample = SuperconductingFilm(cryostat, transition=75.0)

        clock = Clock("clock")
        self.add_instrument(clock)
        self.add_measurement(Measurement("time", clock.time, unit="s"))

        lockin = SR_830("lockin", sr_830_device(sample, "GPIB0::7::INSTR"))
        self.add_instrument(lockin)
        self.add_measurement(Measurement("x", lockin.get_x, unit="V"))
        self.add_measurement(Measurement("y", lockin.get_y, unit="V"))

        cryo = Lakeshore_350(
            "lakeshore", lakeshore_device(cryostat, "GPIB0::12::INSTR")
        )
        self.add_instrument(cryo)
        self.add_measurement(
            Measurement(
                "T",
                cryo.get_temperature,
                input_channel="INPUT_A",
                unit="K",
            )
        )


if __name__ == "__main__":
    MyExperiment().run()
