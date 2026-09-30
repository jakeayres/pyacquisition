# Sweep a temperature

<p class="pa-meta" markdown="span">About 20 minutes · Needs [Getting Started](../getting_started/python_api.md), and [Write a task](write_task.md) helps, and a lock-in and a Lakeshore 350 on your cryostat</p>

Most measurements are made at a series of settings: temperatures, fields, gate voltages. A **sweep** steps through them, and records at each. In this tutorial you write one for temperature, `Sweep`, built from tasks you have already: `SetTemperature` goes to each temperature, `NewFile` starts a file for it, and `WaitFor` records there. A safety check runs alongside, and stops everything if the sample gets too warm. A temperature that can't be reached is skipped, and the sweep carries on.

You carry on with `sample.py` from [Write a task](write_task.md): a sample measured with an SR830, in a cryostat with a Lakeshore 350, at your instruments' addresses.

<div class="gs" data-files="sample.py:versions" data-lines="26" data-term-lines="3" markdown>

<div class="gs-stage" markdown>

<div class="gs-notes" markdown>

<section class="gs-step" data-given markdown>

## Start from SetTemperature

```python title="sample.py"
--8<-- "examples/usage/sweep/sample_1.py"
```

This is `sample.py` as [Write a task](write_task.md) left it: the lock-in and the Lakeshore, and `SetTemperature`, which takes the sample to a temperature and waits until it is there. If you haven't done that tutorial, copy it, with your addresses.

**More:** [Write a task](write_task.md), which builds it.
{ .gs-more }

</section>

<section class="gs-step" markdown>

## Run tasks from a task: the sweep

```python title="sample.py" hl_lines="1 6 65-87"
--8<-- "examples/usage/sweep/sample_2.py"
```

`Sweep` is a task made of others. `run_subtask` runs one from start to end, and waits for it: `SetTemperature` to go to each temperature, then `NewFile` to start a file named after it, then `WaitFor` to record there for `dwell` seconds. So each file starts once the sample is at its temperature. Pausing or aborting the sweep reaches whichever subtask is running, with its own hooks.

`set_progress(i, of=count)` counts the steps. The inputs are `start_kelvin` and `stop_kelvin`, since a task has a `start` of its own.

**More:** [`run_subtask`](../reference/python_api/task.md#pyacquisition.core.task_manager.task.Task.run_subtask), [`NewFile`](../reference/tasks/new_file.md), and [`WaitFor`](../reference/tasks/wait_for.md).
{ .gs-more }

</section>

<section class="gs-step" markdown>

## Keep watch in the background

```python title="sample.py" hl_lines="81-87 91-103"
--8<-- "examples/usage/sweep/sample_3.py"
```

`alongside` runs a task in the background while the block under it runs, and stops it when the block ends. `Interlock` checks the sample every second, and raises an error if it is above 25 K: set the `limit` your sample can take. An error in a background task stops the block, so the sweep stops, `SetTemperature`'s `teardown` holds the cryostat where it is, and the queue pauses.

Every loop in a task needs a wait, here `self.sleep(1)`, or nothing else can run. `run_subtasks` runs several tasks at once, and waits for them all.

**More:** [`alongside`](../reference/python_api/task.md#pyacquisition.core.task_manager.task.Task.alongside), and [`run_subtasks`](../reference/python_api/task.md#pyacquisition.core.task_manager.task.Task.run_subtasks).
{ .gs-more }

</section>

<section class="gs-step" markdown>

## Carry on after an error

```python title="sample.py" hl_lines="85-89"
--8<-- "examples/usage/sweep/sample_4.py"
```

A temperature the cryostat can't reach in an hour, perhaps below its base, makes `SetTemperature` raise `TimeoutError`. Caught here, the sweep logs a warning and goes on to the next temperature, with no file for the one it skipped. Any other error still stops it.

Catch the errors you expect, never everything (`except:`). Aborting a task raises an error in it too, and catching that would stop you aborting.

**More:** [`Task`](../reference/python_api/task.md), and [`wait_until`'s `timeout`](../reference/python_api/task.md#pyacquisition.core.task_manager.task.Task.wait_until).
{ .gs-more }

</section>

<section class="gs-step" data-result="[Sweep] Task completed." markdown>

## Register it, and run the experiment

```python title="sample.py" hl_lines="135"
--8<-- "examples/usage/sweep/sample_5.py"
```

```bash
uv run sample.py
```

In the **Queue** tab, choose **Add task**, then **Sweep**, and give temperatures your cryostat can reach, such as **Start Kelvin** 10, **Stop Kelvin** 16, **Step** 2 and **Dwell** 30. Its bar counts the temperatures, with the subtask running under it. Plot `x` against `T`. In `data`, each temperature has a file of its own: `10 K`, `12 K`, `14 K` and `16 K`.

To see the interlock act, without taking the sample anywhere it shouldn't go, set its `limit` a little above the sweep's start: the sweep stops soon after the sample passes it, since it checks once a second.

**More:** [the Queue tab](../reference/interface.md#the-dock), and [Read your data](read_data.md), to read a sweep's files together.
{ .gs-more }

</section>

</div>

</div>

</div>

!!! success "Checkpoint"
    Queued from 10 to 16 K in steps of 2, the sweep writes `10 K.data`, `12 K.data`, `14 K.data` and `16 K.data`, each numbered on from the file before, and logs `[Sweep] Task completed.` With the interlock's `limit` below where the sweep goes, it stops soon after the sample passes it, with the alert `Sweep failed` and `RuntimeError: The sample is at … K: too warm`, and the queue paused.

??? failure "Something not working?"
    - **The sweep stops with `RuntimeError: The sample is at … K: too warm`, and the queue pauses.** That is the interlock, doing its job: the sample went above `limit`. Set it to what your sample can take.
    - **The sweep fails at once with `float division by zero`.** **Step** was 0.
    - **The experiment freezes when the sweep starts.** A loop has no wait in it: every loop in a task needs one, such as `await self.sleep(1)`.
    - **The sweep can't be aborted.** A bare `except:` catches the abort. Catch the error you expect, such as `TimeoutError`.

## What you learned

- A task can run others with `await self.run_subtask(...)`, one after another, and pausing or aborting it reaches them.
- `NewFile` in a sweep gives each step a data file of its own.
- `alongside` runs a task in the background for as long as a block runs, and an error in it stops the block. `run_subtasks` runs several at once.
- A `try` around a subtask catches an error you expect, and carries on.

Next: [Queue, pause and save tasks](queue.md), to run sweeps one after another, and save the queue to run again.
