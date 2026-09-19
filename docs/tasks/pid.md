# PID

`PID` holds a value at a setpoint. Every `period` seconds it reads a measured value, works out an output with a PID controller, and writes the output. It is not registered by default. Import it from `pyacquisition.tasks`.

It is not tied to any instrument: you give it two functions, one that **reads** the value and one that **writes** the output. That makes it work for a temperature, a pressure, a field, or anything else that you can read and set.

## Example

This holds a simulated furnace at 60 °C for the whole experiment. Save the furnace in a file called `furnace.py`:

```python title="furnace.py" linenums="1"
import time

from pyacquisition.core.instrument import SoftwareInstrument, mark_command, mark_query


class Furnace(SoftwareInstrument):
    """A simulated furnace: power in, temperature out."""

    name = "Furnace"

    def __init__(self, uid):
        super().__init__(uid)
        self._temperature = 20.0
        self._power = 0.0
        self._last = time.monotonic()

    def _advance(self):
        now = time.monotonic()
        dt, self._last = now - self._last, now
        target = 20.0 + 0.8 * self._power  # 100 % power settles at 100 degrees
        self._temperature += dt * (target - self._temperature) / 20.0

    @mark_query
    def temperature(self) -> float:
        self._advance()
        return self._temperature

    @mark_command
    def set_power(self, percent: float) -> float:
        self._advance()
        self._power = percent
        return percent
```

Then the experiment:

```python title="my_experiment.py" linenums="1"
from pyacquisition import Experiment, Measurement
from pyacquisition.tasks import PID

from furnace import Furnace


class MyExperiment(Experiment):
    def setup(self):
        furnace = Furnace("furnace")
        self.add_instrument(furnace)

        pid = PID(
            read=furnace.temperature, # (1)!
            write=furnace.set_power, # (2)!
            setpoint=60.0,
            kp=5.0,
            ki=0.5,
            output_min=0.0, # (3)!
            output_max=100.0,
            label="furnace",
        )

        self.add_task_manager("pid").add_task(pid) # (4)!

        self.add_measurement(Measurement("temperature", furnace.temperature))
        self.add_measurement(Measurement("power", lambda: pid.output)) # (5)!
        self.add_measurement(Measurement("error", lambda: pid.error))


if __name__ == "__main__":
    MyExperiment().run()
```

1. `read` is any function that takes no arguments and returns the measured value. Pass the method, not its result: no brackets. For a method that needs arguments, use a `lambda` or `functools.partial`, for example `lambda: sensor.get_temperature(Channel.A)`.
2. `write` is any function that takes the output. It is called on every cycle, and once more when the PID ends.
3. Always set limits that suit your hardware. Here the output is a heater power between 0 and 100 %.
4. Give the PID a [task manager of its own](../usage/running_tasks.md#several-task-managers), so that it runs for the whole experiment while the main queue is free for everything else. Queueing it there starts it when the experiment starts. Nothing else queued on that task manager would run, because the PID never finishes, so name it for what it holds, such as `"pid"`, and keep it for the PID.
5. The PID's output and error are ordinary attributes, so record them like any other measurement. See [What the PID is doing](#what-the-pid-is-doing).

Run it, and plot `temperature` and `power`. The temperature rises with the heater at full power, and settles at 60 °C with the power at about 50 %.

## Settings

| Setting | Meaning |
|---|---|
| `read`, `write` | The functions that measure the value and apply the output. |
| `setpoint` | The value to hold. |
| `kp` | Proportional gain, in output per unit of error. The default is 1. |
| `ki` | Integral gain, in output per (error × second). The default is 0. |
| `kd` | Derivative gain, in output per (error ÷ second). The default is 0. |
| `output_min`, `output_max` | Limits on the output. By default there are none. |
| `period` | Seconds between cycles. The default is 1. |
| `derivative_filter` | Time constant, in seconds, of a filter on the derivative term. The default of 0 has no filter, which makes a noisy signal noisy in the output. |
| `inverted` | `False` if raising the output raises the value (a heater). `True` if it lowers it (a cooler). |
| `initial_output` | The output that is already applied when the PID starts, so that it takes over smoothly. By default it starts from `kp` × error. |
| `final_output` | Written when the PID ends, however it ends. The default is 0. **Set it to something safe for your hardware.** |
| `duration` | Stop after this many seconds. The default of 0 runs until it is stopped. |
| `max_failures` | Stop with an error after this many failed cycles in a row. The default is 5. |
| `label` | The name shown in the **Logs** window. Give each PID its own. |

## How it works

- **The integral stops at the limits.** If the output is at a limit and the error would push it further, the integral does not grow. The output comes off the limit as soon as the error changes sign, with no delay from a built-up integral.
- **The derivative uses the measured value**, not the error, so changing the setpoint does not kick the output.
- **The integral is kept in units of the output**, so changing `ki` while it runs does not make the output jump.
- **It uses the real time between cycles**, not the period, so a slow instrument does not distort the integral or the derivative. After a long gap, such as a pause, the integral counts for at most five periods.
- **Pausing holds the output** where it was, like any task. Resuming carries on from there.

## Changing settings while it runs

The settings `setpoint`, `kp`, `ki`, `kd`, `output_min`, `output_max`, `period` and `derivative_filter` are read on every cycle. Change them by assigning to them, from your own code:

```python
pid.setpoint = 80.0
pid.kp = 8.0
```

For example, a task can step the setpoint through a series of values, holding each one for a while:

```python
from dataclasses import dataclass

from pyacquisition import Task
from pyacquisition.tasks import PID, WaitFor


@dataclass
class Staircase(Task):
    """Step the PID's setpoint up through a series of values."""

    pid: PID # (1)!
    hold_seconds: int = 300

    async def run(self, experiment):
        for setpoint in [40.0, 60.0, 80.0]:
            self.pid.setpoint = setpoint
            yield f"Setpoint {setpoint}"
            await self.run_subtask(WaitFor(seconds=self.hold_seconds))
```

1. A task receives the PID as an input, like any other object. Queue it in `setup()` with `self.task_managers["main"].add_task(Staircase(pid))`, next to the PID on its own task manager. Because its input is an object, it is created in code and is not registered for the interface.

The interface cannot change these while it runs, because a PID is created in code. To be able to change the setpoint from the interface, put it in a small [software instrument](../usage/custom_instruments.md) whose command sets `pid.setpoint`, and give the instrument the PID.

## What the PID is doing

In the **Task Queue** window, the PID's card shows its setpoint and gains, and once it is running, the latest measured `value`, `output` and `error`, refreshed about once a second.

`pid.process_value`, `pid.output` and `pid.error` are the last measured value, output and error. Use them in a measurement, as in the example, to record them in the data file alongside everything else: `Measurement("power", lambda: pid.output)`. The value is `nan` until the PID has read for the first time.

## When something goes wrong

- **A failed cycle is logged and skipped.** If `read` or `write` raises an error (an instrument times out, say), or the reading is not a number, the output stays where it was and the PID tries again on the next cycle.
- **Too many in a row stops it.** After `max_failures` failed cycles in a row, the PID stops with an error. It never carries on blind.
- **It always writes `final_output`.** That happens when it is aborted, when it reaches its `duration`, when the experiment shuts down, and when it stops with an error.
- **The error reaches the parent.** If the PID is running as a subtask, or [alongside](../usage/composing_tasks.md#in-the-background-alongside) another block of work, the error interrupts that work and is raised there. See [Composing tasks](../usage/composing_tasks.md).

!!! warning "The software cannot protect the hardware if it stops"
    If the Python process dies, nothing writes `final_output`, and the instrument keeps whatever output it was last given. For anything that can be damaged or is dangerous, such as a heater, set limits on the instrument itself, and use its own over-temperature protection, as a second line of defence.

!!! note "The PID shares one thread with everything else"
    It takes turns with the rest of the experiment, so a very slow `read` or `write` delays its cycles. The PID uses the real elapsed time, so the control stays correct, just slower. It is well suited to the slow loops of a lab (a period of about a second), and not to control that needs precise timing.

## Using the controller without a task

`PIDController` is the calculation on its own: give it the setpoint, the measured value and the time since the last call, and it returns the output. Use it if you want a PID somewhere other than a task, for example in a [calculation](../usage/calculations.md).

```python
from pyacquisition.tasks import PIDController

controller = PIDController(kp=5.0, ki=0.5, output_min=0.0, output_max=100.0)
output = controller.update(setpoint=60.0, process_value=42.0, dt=1.0)
```

## Reference

::: pyacquisition.tasks.PID

::: pyacquisition.tasks.PIDController
