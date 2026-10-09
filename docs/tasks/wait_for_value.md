# Wait For Value

`WaitForValue` waits until a measurement goes below or above a value, such as a cryostat cooling below 2 K, or a pressure falling below 1e-5 mbar. **Every experiment with measurements has it**, listed as **WaitForValue** in **Add task**.

It watches the readings as they arrive with the rows, once each measurement period, so it sees what the plot and the data file see, and asks nothing more of the instrument.

It asks for:

| Input | Meaning |
|---|---|
| `measurement` | The column to watch, picked from the experiment's measurements and calculations. A calculation's columns are listed when it names them: a [`Calculation`](../usage/calculations.md#keeping-state-between-rows) by its `columns`, and a plain function by its `units` in `add_calculation`. |
| `condition` | `BELOW` or `ABOVE` the threshold. |
| `threshold` | The value to pass, in the measurement's units. |
| `hold` | How many seconds the reading must stay past the threshold, so that one noisy reading doesn't end the wait. 0, the default, ends it at the first. |
| `timeout` | How many minutes to wait before giving up. 0, the default, waits as long as it takes. |
| `continue_on_timeout` | When the time runs out, log a warning and carry on with the queue, instead of failing. |

If the reading is past the threshold already, it finishes at once. While it waits, its progress says how far the reading has to go, and the time left at the rate it is moving.

If the time runs out, the task fails, which pauses the queue, so the tasks behind it don't run as if the reading had got there. With `continue_on_timeout`, it logs a warning instead, and the queue carries on.

Used as a subtask of a task of your own:

```python
await self.run_subtask(WaitForValue("T", "BELOW", 2.0, timeout=120))  # (1)
```

<div class="gs-legend pa-notes" markdown>

1. Wait until the column `T` is below 2, for at most two hours. The condition can be text, as here, or a member of `Condition`, imported from `pyacquisition.tasks.wait`.

</div>

To wait until a reading has settled, rather than passed a value, use [WaitForStable](wait_for_stable.md).

## Reference

::: pyacquisition.tasks.WaitForValue
