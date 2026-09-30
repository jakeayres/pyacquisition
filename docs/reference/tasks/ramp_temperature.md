# Ramp Temperature

`RampTemperature` ramps the setpoint of a Lakeshore 340 or 350 output to a temperature, at a rate, and waits until the setpoint has got there. **It is registered by itself when there is a Lakeshore in the experiment**, and listed as **Ramp Temperature** in **Add task**.

```python
from pyacquisition.instruments import Lakeshore_350


class MyExperiment(Experiment):
    def setup(self):
        self.add_instrument(Lakeshore_350("lakeshore", "GPIB0::12::INSTR"))  # (1)
```

<div class="gs-legend pa-notes" markdown>

1. Adding the controller registers `RampTemperature`: there is no `register_task` to write.

</div>

It asks for:

| Input | Meaning |
|---|---|
| `output_channel` | The output to ramp, as text such as `OUTPUT_1`, or its label `Output 1`, in any case. |
| `setpoint` | The temperature to ramp to. |
| `ramp_rate` | The ramp rate, in kelvin per minute. |

The id of the controller is filled in for you when there is one Lakeshore. With two, such as a 340 and a 350, the form asks which, in the box for `lakeshore`.

Used as a subtask of a task of your own, it takes the id first, and the channel can be a member or text:

```python
await self.run_subtask(
    RampTemperature("lakeshore", Lakeshore_350.OutputChannel.OUTPUT_1, 4.2, 2.0)  # (1)
)
await self.run_subtask(RampTemperature("lakeshore", "OUTPUT_1", 4.2, 2.0))  # (2)
```

<div class="gs-legend pa-notes" markdown>

1. The controller's id, the output as a member of its `OutputChannel`, then the setpoint, 4.2 K, and the rate, 2.0 K a minute.
2. The same, with the output as text.

</div>

It does not stop the ramp if it is paused or aborted, so add a `teardown()` of your own to a task that needs the setpoint held. To turn the automatic registration off, see [tasks that come with an instrument](overview.md#with-an-instrument).

## Reference

::: pyacquisition.tasks.RampTemperature
