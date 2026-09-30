# Magnet sweeps

`SweepMagneticField` sweeps a magnet powered by an Oxford Instruments [Mercury IPS](../instruments/mercury_ips.md) to a field and back to zero. **It is registered by itself when there is a Mercury IPS in the experiment**, and listed as **Sweep Magnetic Field** in **Add task**.

```python
from pyacquisition.instruments import Mercury_IPS


class MyExperiment(Experiment):
    def setup(self):
        self.add_instrument(Mercury_IPS("magnet_psu", "GPIB0::25::INSTR"))  # (1)
```

<div class="gs-legend pa-notes" markdown>

1. Adding the power supply registers `SweepMagneticField`: there is no `register_task` to write.

</div>

The task takes the `setpoint` in tesla and the `ramp_rate` in tesla per minute. The id of the power supply is filled in for you when there is one Mercury IPS. With two, the form asks which. To register it yourself instead, for example to choose the label, set `auto_tasks = False` and use `self.register_task(SweepMagneticField, label="Sweep Field")`. See [tasks that come with an instrument](overview.md#with-an-instrument).

## What it does, and what it checks

The magnet is the power supply, so every step is checked before the next one is taken. A check that fails stops the task there, and nothing further is sent to the magnet.

| Step | Checked |
|---|---|
| Put the magnet on **hold** | The system status is `NORMAL`, and the activity is `HOLD`. |
| Switch the **switch heater on**, wait 15 s | The heater reads `ON`. |
| Set the **ramp rate** | It reads back as the value that was set. |
| Set the **setpoint** and **sweep to it** | The setpoint reads back as set, and the activity is `TO_SETPOINT`. It then waits until the sweep is at rest. |
| **Sweep to zero** | The activity is `TO_ZERO`. It then waits until the sweep is at rest. |
| Switch the **switch heater off**, wait 15 s | The heater reads `OFF_AT_ZERO`. |
| **Finally**, always | The magnet is put on hold, and the system status must be `NORMAL`. A quench or a fault shows here, and fails the task. |

A new data file is started before each sweep, `Field Sweep to <setpoint>T` and `Field Sweep to 0T`.

## Pausing, resuming and aborting

- **Pause** puts the magnet on hold, wherever in the sweep it is.
- **Resume** first checks that the system status is `NORMAL`, then sends the magnet on its way again, towards the setpoint or towards zero, whichever it was heading for. If the system is not normal, the magnet stays on hold and the task fails.
- **Abort** stops the task where it is, and its clean-up puts the magnet on hold. The switch heater is left as it was.

A task that fails pauses the queue, so nothing else runs while the magnet is in that state.

## The pieces

The sweep is built from two smaller tasks, which you can use on their own or in a task of your own:

- `RampMagnet(magnet_psu, setpoint)` sweeps to a field.
- `RampMagnetToZero(magnet_psu)` sweeps to zero.

Each one knows what pausing it means. Pausing holds the magnet, and resuming sends it on its way. A larger task made of them needs no `on_pause()` or `on_resume()` of its own, which is why `SweepMagneticField` has none. They are also a worked example of [writing a task that controls hardware](../../usage/write_task.md#hold-the-hardware-when-paused), with every value read back and checked with [`self.expect()`](../python_api/task.md#pyacquisition.core.task_manager.task.Task.expect). Read the source, and write your own for your requirements.

## Reference

::: pyacquisition.tasks.field_sweep.SweepMagneticField

::: pyacquisition.tasks.field_sweep.RampMagnet

::: pyacquisition.tasks.field_sweep.RampMagnetToZero
