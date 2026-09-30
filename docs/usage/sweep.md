# Sweep a temperature

<p class="pa-meta" markdown="span">About 20 minutes · Needs [Getting Started](../getting_started/python_api.md), and [Write a task](write_task.md) helps</p>

Most measurements are made at a series of settings: temperatures, fields, gate voltages. A **sweep** steps through them, and records at each. In this tutorial you write one for temperature, `Sweep`, built from tasks you have already: `SetTemperature` goes to each temperature, `NewFile` starts a file for it, and `WaitFor` records there. A safety check runs alongside, and stops everything if the sample gets too warm. A temperature that can't be reached is skipped, and the sweep carries on.

You carry on with `sample.py` from [Write a task](write_task.md), beside `simulated.py`: a cryostat, and a lock-in on a sample in it, which stand in for a Lakeshore 350 and an SR830. The sample's signal falls away as it warms through 14 K.

<div class="gs" data-files="sample.py:versions" data-lines="26" data-term-lines="3" markdown>

<div class="gs-stage" markdown>

<div class="gs-notes" markdown>

<section class="gs-step" data-given markdown>

## Start from SetTemperature

```python title="sample.py"
--8<-- "examples/usage/sweep/sample_1.py"
```

This is `sample.py` as [Write a task](write_task.md) left it: the sample in the cryostat, and `SetTemperature`, which takes it to a temperature and waits until it is there. If you haven't done that tutorial, copy it.

??? abstract "simulated.py: a cryostat, and a lock-in on a sample in it, simulated"
    Save this beside `sample.py`. It stands in for real hardware, and you don't need to read it.

    ```python title="simulated.py"
    --8<-- "examples/simulated_rig/simulated.py"
    ```

**More:** [Write a task](write_task.md), which builds it.
{ .gs-more }

</section>

<section class="gs-step" markdown>

## Run tasks from a task: the sweep

```python title="sample.py" hl_lines="1 11 67-89"
--8<-- "examples/usage/sweep/sample_2.py"
```

`Sweep` is a task made of others. `run_subtask` runs one from start to end, and waits for it: `SetTemperature` to go to each temperature, then `NewFile` to start a file named after it, then `WaitFor` to record there for `dwell` seconds. So each file starts once the sample is at its temperature. Pausing or aborting the sweep reaches whichever subtask is running, with its own hooks.

`set_progress(i, of=count)` counts the steps. The inputs are `start_kelvin` and `stop_kelvin`, since a task has a `start` of its own.

**More:** [`run_subtask`](../reference/python_api/task.md#pyacquisition.core.task_manager.task.Task.run_subtask), [`NewFile`](../reference/tasks/new_file.md), and [`WaitFor`](../reference/tasks/wait_for.md).
{ .gs-more }

</section>

<section class="gs-step" markdown>

## Keep watch in the background

```python title="sample.py" hl_lines="83-89 93-105"
--8<-- "examples/usage/sweep/sample_3.py"
```

`alongside` runs a task in the background while the block under it runs, and stops it when the block ends. `Interlock` checks the sample every second, and raises an error if it is above 25 K. An error in a background task stops the block, so the sweep stops, `SetTemperature`'s `teardown` holds the cryostat where it is, and the queue pauses.

Every loop in a task needs a wait, here `self.sleep(1)`, or nothing else can run. `run_subtasks` runs several tasks at once, and waits for them all.

**More:** [`alongside`](../reference/python_api/task.md#pyacquisition.core.task_manager.task.Task.alongside), and [`run_subtasks`](../reference/python_api/task.md#pyacquisition.core.task_manager.task.Task.run_subtasks).
{ .gs-more }

</section>

<section class="gs-step" markdown>

## Carry on after an error

```python title="sample.py" hl_lines="87-91"
--8<-- "examples/usage/sweep/sample_4.py"
```

A temperature the cryostat can't reach in an hour, perhaps below its base, makes `SetTemperature` raise `TimeoutError`. Caught here, the sweep logs a warning and goes on to the next temperature, with no file for the one it skipped. Any other error still stops it.

Catch the errors you expect, never everything (`except:`). Aborting a task raises an error in it too, and catching that would stop you aborting.

**More:** [`Task`](../reference/python_api/task.md), and [`wait_until`'s `timeout`](../reference/python_api/task.md#pyacquisition.core.task_manager.task.Task.wait_until).
{ .gs-more }

</section>

<section class="gs-step" data-result="[Sweep] Task completed." markdown>

## Register it, and run the experiment

```python title="sample.py" hl_lines="136"
--8<-- "examples/usage/sweep/sample_5.py"
```

```bash
uv run sample.py
```

In the **Queue** tab, choose **Add task**, then **Sweep**, and give **Start Kelvin** 10, **Stop Kelvin** 16, **Step** 2 and **Dwell** 30. Its bar counts the temperatures, with the subtask running under it. Plot `x` against `T`: the signal falls as the sample warms through 14 K. In `data`, a file for each temperature: `10 K`, `12 K`, `14 K` and `16 K`.

Then try the interlock: a sweep from 22 to 30 K stops at about 25 K, since it checks once a second.

**More:** [the Queue tab](../reference/interface.md#the-dock), and [Read your data](read_data.md), to read a sweep's files together.
{ .gs-more }

</section>

</div>

</div>

</div>

## What you built

A sweep from 10 K to 16 K, on its way to 16 K:

<div class="gs-shot" markdown>

![The interface running sample.py: x against T from 12 to 15.4 K, falling through 14 K, from the files 00.02 12 K.data and 00.03 14 K.data, and the Queue tab, where Sweep from 10.0 to 16.0 K is at 3 of 4, going to 16 K, with Interlock and SetTemperature, at 62% and 15.24 K, running under it](../images/usage/sweep/sweep.png){ .pa-shot }

<span class="gs-pin" style="--x: 9.8%; --y: 70.3%">1</span>
<span class="gs-pin" style="--x: 24.8%; --y: 76.4%">2</span>
<span class="gs-pin" style="--x: 72.8%; --y: 9.2%">3</span>
<span class="gs-pin" style="--x: 59.8%; --y: 27.7%">4</span>

</div>

<div class="gs-legend" markdown>

1. **The sweep.** Its description, and its progress in temperatures: 3 of 4, going to 16 K.
2. **Its subtasks.** `Interlock` in the background, and `SetTemperature`, with its own progress.
3. **A file for each temperature.** Now `14 K`, with `12 K` before it, fainter on the plot.
4. **The transition.** The signal falls away as the sample warms through 14 K.

</div>

!!! success "Checkpoint"
    Queued from 10 to 16 K in steps of 2, the sweep writes `10 K.data`, `12 K.data`, `14 K.data` and `16 K.data`, each numbered on from the file before, and logs `[Sweep] Task completed.` Plotted against `T`, `x` falls from about 2.3 mV at 10 K through 14 K. Queued from 22 to 30 K, it stops at about 25 K, with the alert `Sweep failed` and `RuntimeError: The sample is at 25.05 K: too warm`, say, and the queue paused.

??? failure "Something not working?"
    - **The sweep stops with `RuntimeError: The sample is at 25.05 K: too warm`, and the queue pauses.** That is the interlock, doing its job: the sweep went above 25 K. Set `limit` to what your sample can take.
    - **The sweep fails at once with `float division by zero`.** **Step** was 0.
    - **The experiment freezes when the sweep starts.** A loop has no wait in it: every loop in a task needs one, such as `await self.sleep(1)`.
    - **The sweep can't be aborted.** A bare `except:` catches the abort. Catch the error you expect, such as `TimeoutError`.

## What you learned

- A task can run others with `await self.run_subtask(...)`, one after another, and pausing or aborting it reaches them.
- `NewFile` in a sweep gives each step a data file of its own.
- `alongside` runs a task in the background for as long as a block runs, and an error in it stops the block. `run_subtasks` runs several at once.
- A `try` around a subtask catches an error you expect, and carries on.

Next: [Queue, pause and save tasks](running_tasks.md), to run sweeps one after another, and save the queue to run again.
