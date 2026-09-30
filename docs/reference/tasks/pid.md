# PID

`PID` holds a value at a setpoint. Every `period` seconds it reads a measured value, works out an output with a PID controller, and writes the output. It is not registered by default. Import it from `pyacquisition.tasks`.

It is not tied to any instrument: you give it two functions, one that **reads** the value and one that **writes** the output. That makes it work for a temperature, a pressure, a field, or anything else that you can read and set.

[Hold a temperature with PID](../../usage/pid.md) shows it in use: a sample held at a temperature through a thermometer read by a lock-in and a Lakeshore's heater, on a queue of its own, with its setpoint changed from the interface.

## Example

```python
from pyacquisition.tasks import PID

pid = PID(
    read=resistance,  # (1)
    write=heater,
    setpoint=1650.0,
    kp=1.0,  # (2)
    ki=0.2,
    output_min=0.0,  # (3)
    output_max=100.0,
    inverted=True,  # (4)
    label="sample",  # (5)
)
self.add_task_manager("control").add_task(pid)  # (6)
```

<div class="gs-legend pa-notes" markdown>

1. The functions themselves, with no brackets: the PID calls `read()` for the value, here a thermometer's resistance, and `write(output)` with the output, here a heater's, every cycle.
2. Gains, in output per unit of error: 1 % of the heater's range per ohm off, and 0.2 % per ohm-second.
3. The heater's own range: the output never goes outside it.
4. More heat lowers the value, as it does a RuOx thermometer's resistance.
5. The name in the **Logs** window. Give each PID its own.
6. A queue of its own, since a PID never finishes: the main queue stays free for the rest of the experiment.

</div>

For a method that needs arguments, give a `lambda`: `read=lambda: sensor.get_temperature(Channel.A)`. A task on a task manager of its own starts with the experiment.

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
| `inverted` | `False` if raising the output raises the value (a heater and a thermometer that reads kelvin). `True` if it lowers it (a cooler, or a heater and a resistive thermometer whose resistance falls as it warms, such as a RuOx or a Cernox). |
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
pid.setpoint = 1560.0
pid.kp = 0.5
```

A task of your own can change them too, given the PID as an input. Such a task is made in code, since a form can't show a PID.

The interface can't change them directly, because a PID is made in code. A small software instrument whose commands set them can, as in [Hold a temperature with PID](../../usage/pid.md#change-the-setpoint-and-gains-from-the-interface).

## What the PID is doing

In the **Queue** tab, the PID's card shows its setpoint and gains, and once it is running, the latest measured `value`, `output` and `error`, refreshed about once a second.

`pid.process_value`, `pid.output` and `pid.error` are the last measured value, output and error. Use them in a measurement, as in the example, to record them in the data file alongside everything else: `Measurement("power", lambda: pid.output)`. The value is `nan` until the PID has read for the first time.

## When something goes wrong

- **A failed cycle is logged and skipped.** If `read` or `write` raises an error (an instrument times out, say), or the reading is not a number, the output stays where it was and the PID tries again on the next cycle.
- **Too many in a row stops it.** After `max_failures` failed cycles in a row, the PID stops with an error. It never carries on blind.
- **It always writes `final_output`.** That happens when it is aborted, when it reaches its `duration`, when the experiment shuts down, and when it stops with an error.
- **The error reaches the parent.** If the PID is running as a subtask, or [alongside](../python_api/task.md#pyacquisition.core.task_manager.task.Task.alongside) another block of work, the error interrupts that work and is raised there. See [Sweep a temperature](../../usage/sweep.md#keep-watch-in-the-background).

!!! warning "The software cannot protect the hardware if it stops"
    If the Python process dies, nothing writes `final_output`, and the instrument keeps whatever output it was last given. For anything that can be damaged or is dangerous, such as a heater, set limits on the instrument itself, and use its own over-temperature protection, as a second line of defence.

!!! note "The PID shares one thread with everything else"
    It takes turns with the rest of the experiment, so a very slow `read` or `write` delays its cycles. The PID uses the real elapsed time, so the control stays correct, just slower. It is well suited to the slow loops of a lab (a period of about a second), and not to control that needs precise timing.

## Using the controller without a task

`PIDController` is the calculation on its own: give it the setpoint, the measured value and the time since the last call, and it returns the output. Use it if you want a PID somewhere other than a task, for example in a [calculation](../../usage/calculations.md).

```python
from pyacquisition.tasks import PIDController

controller = PIDController(kp=5.0, ki=0.5, output_min=0.0, output_max=100.0)
output = controller.update(setpoint=60.0, process_value=42.0, dt=1.0)  # (1)
```

<div class="gs-legend pa-notes" markdown>

1. One step: the output for a value of 42 against a setpoint of 60, one second after the last. Call it each time there is a new value.

</div>

## Reference

::: pyacquisition.tasks.PID

::: pyacquisition.tasks.PIDController
