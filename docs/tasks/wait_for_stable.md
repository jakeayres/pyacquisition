# Wait For Stable

`WaitForStable` waits until a measurement has settled: until it has stayed in a band for a set time, without drifting. Queue it after a change, such as a new setpoint, instead of waiting a time you guessed. **Every experiment with measurements has it**, listed as **WaitForStable** in **Add task**.

It watches the readings as they arrive with the rows, once each measurement period, so it sees what the plot and the data file see, and asks nothing more of the instrument.

It asks for:

| Input | Meaning |
|---|---|
| `measurement` | The column to watch, picked from the experiment's measurements and calculations. A calculation's columns are listed when it names them: a [`Calculation`](../usage/calculations.md#keeping-state-between-rows) by its `columns`, and a plain function by its `units` in `add_calculation`. |
| `tolerance` | How far a reading may be from the target, or from the middle of the band, in the measurement's units. |
| `hold` | How many minutes the readings must stay in the band. |
| `max_drift` | How fast the readings may rise or fall, in the measurement's units per minute. 0, the default, doesn't check it. |
| `target` | The value to be stable at, such as the setpoint. Leave it blank for readings that may settle anywhere. |
| `timeout` | How many minutes to wait before giving up. 0, the default, waits as long as it takes. |
| `continue_on_timeout` | When the time runs out, log a warning and carry on with the queue, instead of failing. |

**With a `target`**, every reading of the last `hold` minutes must be within `tolerance` of it. Use the setpoint when the measurement is the sensor the controller holds at it. A heater that can't reach the setpoint then never counts as stable.

**Without one**, the readings may settle anywhere, in a band twice `tolerance` wide. Use this for a thermometer on the sample, which may sit a little off the setpoint because of the gradient between it and the control sensor.

**`max_drift`** catches a slow drift that still fits in the band: a line through the readings of the last `hold` minutes must rise or fall by no more than `max_drift` a minute.

A reading outside the band starts the time again, from the next one. A failed reading is skipped. Pausing the task starts the time again when it resumes, because the readings weren't watched while it was paused. While it waits, its progress says how long the readings have been in the band, and how fast they are drifting.

If the time runs out, the task fails, which pauses the queue, so the tasks behind it don't run at a temperature that never settled. With `continue_on_timeout`, it logs a warning instead, and the queue carries on.

Used as a subtask of a task of your own, after a ramp:

```python
await self.run_subtask(RampTemperature("lakeshore", "OUTPUT_1", 10.0, 2.0))  # (1)
await self.run_subtask(
    WaitForStable("T", tolerance=0.005, hold=5, max_drift=0.001, target=10.0)  # (2)
)
```

<div class="gs-legend pa-notes" markdown>

1. Ramp the setpoint to 10 K at 2 K a minute. [RampTemperature](ramp_temperature.md) finishes when the setpoint gets there, which says nothing about the sample.
2. Then wait until `T` has stayed within 5 mK of 10 K for 5 minutes, drifting by less than 1 mK a minute.

</div>

To wait only until a reading passes a value, use [WaitForValue](wait_for_value.md).

## Reference

::: pyacquisition.tasks.WaitForStable
