import asyncio
import random
import time
from dataclasses import dataclass

from pyacquisition import Experiment, Measurement, Task
from pyacquisition.core.instrument import SoftwareInstrument, mark_command, mark_query
from pyacquisition.instruments.software import Clock, RandomNumberGenerator, SignalGenerator
from pyacquisition.tasks import PID, NewFile, WaitFor

#
#  This should be put pytested
#


#
#  Example: running tasks at the same time
#
#  Run "Record With Restarts" from the Tasks menu, then watch the 'chirp' column in a
#  plot: it sweeps up in frequency, and jumps back to the start every `every` seconds.
#  Run "Parallel Waits" and watch the Logs window.
#


@dataclass
class RestartSignal(Task):
    """Restart the signal generator every `every` seconds, until stopped."""

    every: int = 20

    async def run(self, experiment):
        generator = experiment.instruments["signal_generator"]
        while True:
            for _ in range(self.every):
                await asyncio.sleep(1)  # every loop needs an await, or nothing else can run
                yield None  # and yield often, so that it can be paused or stopped
            generator.restart()
            yield "Restarted the signal generator"


@dataclass
class RecordWithRestarts(Task):
    """Record to a new file, with the signal restarting in the background."""

    seconds: int = 60
    every: int = 20

    async def run(self, experiment):
        await self.run_subtask(NewFile(file_name="restarts"))
        yield "Started a new file"

        # RestartSignal never finishes by itself. alongside() runs it for as long as
        # the block does, and stops it (running its teardown) when the block ends.
        async with self.alongside(RestartSignal(every=self.every)):
            await self.run_subtask(WaitFor(seconds=self.seconds))
            yield "Finished recording"

        yield "The restarts have stopped"


@dataclass
class ParallelWaits(Task):
    """Wait two different times at once. It takes as long as the longer one."""

    seconds_a: int = 5
    seconds_b: int = 10

    async def run(self, experiment):
        # Both waits start together (see the Logs window), and run_subtasks() returns
        # when the slower one is done: after `seconds_b`, not `seconds_a + seconds_b`.
        await self.run_subtasks(
            WaitFor(seconds=self.seconds_a), WaitFor(seconds=self.seconds_b)
        )
        yield "Both waits are over"


#
#  Example: a PID controller
#
#  A simulated furnace (power in, temperature out) is held at a setpoint by a PID task
#  that runs for the whole experiment on its own task manager, so the main queue is
#  free for other tasks. Plot 'furnace_temperature' and 'furnace_power'.
#
#  Try it (the interface starts number boxes at 0, so fill in every box):
#    1. Instruments -> furnace_pid -> Set Setpoint 60, and watch the temperature follow.
#    2. Set Gains: kp 5, ki 0, kd 0. Nothing changes yet: ki = 0 keeps the integral
#       where it was, so the output does not jump.
#    3. Set Setpoint 80. With no integral action it settles short of it, at about 76.
#    4. Set Gains: kp 5, ki 0.5, kd 0. The integral closes the gap, and it reaches 80.
#


class Furnace(SoftwareInstrument):
    """A simulated furnace: 100 % power settles at 100 degrees, with a slow response."""

    name = "Furnace"

    def __init__(self, uid, noise=0.05):
        super().__init__(uid)
        self._noise = noise
        self._temperature = 20.0
        self._power = 0.0
        self._last = time.monotonic()

    def _advance(self):
        now = time.monotonic()
        dt, self._last = now - self._last, now
        target = 20.0 + 0.8 * self._power
        self._temperature += dt * (target - self._temperature) / 20.0  # 20 s time constant

    @mark_query
    def temperature(self) -> float:
        self._advance()
        return self._temperature + random.gauss(0.0, self._noise)

    @mark_command
    def set_power(self, percent: float) -> float:
        self._advance()
        self._power = percent
        return percent


class PIDControls(SoftwareInstrument):
    """Lets the interface change a running PID, which it cannot do by itself."""

    name = "PID Controls"

    def __init__(self, uid, pid):
        super().__init__(uid)
        self._pid = pid

    @mark_command
    def set_setpoint(self, setpoint: float) -> float:
        self._pid.setpoint = setpoint  # the PID reads this on every cycle
        return setpoint

    @mark_command
    def set_gains(self, kp: float, ki: float, kd: float) -> float:
        self._pid.kp, self._pid.ki, self._pid.kd = kp, ki, kd
        return kp

    @mark_query
    def get_setpoint(self) -> float:
        return self._pid.setpoint


class MyExperiment(Experiment):


    def __init__(self):
        super().__init__(data_path='data', log_path='data')

    
    def setup(self):
        
        clock = Clock("clock")
        self.add_instrument(clock)

        measurement = Measurement('time_ms', clock.timestamp_ms)
        self.add_measurement(measurement)

        measurement = Measurement('time', clock.time)
        self.add_measurement(measurement)


        rng = RandomNumberGenerator("rng")
        self.add_instrument(rng)

        measurement = Measurement('random', rng.uniform, low=0, high=1)
        self.add_measurement(measurement)


        signal_generator = SignalGenerator("signal_generator")
        self.add_instrument(signal_generator)

        chirp = Measurement('chirp', 
            signal_generator.chirp,
            start_frequency=0.1,
            end_frequency=1.0,
            duration=120.0,
            amplitude=1.0,
            )
        self.add_measurement(chirp)


        self.register_task(RecordWithRestarts, label="Record With Restarts")
        self.register_task(ParallelWaits, label="Parallel Waits")


        furnace = Furnace("furnace")
        self.add_instrument(furnace)

        pid = PID(
            read=furnace.temperature,
            write=furnace.set_power,
            setpoint=40.0,
            kp=5.0,
            ki=0.5,
            output_min=0.0,      # always set limits that suit the hardware
            output_max=100.0,
            final_output=0.0,    # power off when the PID stops, however it stops
            label="furnace PID",
        )
        self.add_instrument(PIDControls("furnace_pid", pid))

        # The PID never finishes by itself, so it gets a task manager of its own.
        # Queueing it here starts it when the experiment starts.
        control = self.add_task_manager("control")
        control.add_task(pid)

        self.add_measurement(Measurement('furnace_temperature', furnace.temperature))
        self.add_measurement(Measurement('furnace_power', lambda: pid.output))
        self.add_measurement(Measurement('furnace_setpoint', lambda: pid.setpoint))