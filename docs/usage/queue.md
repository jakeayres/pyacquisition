# Queue, pause and save tasks

<p class="pa-meta" markdown="span">About 15 minutes · Needs [Getting Started](../getting_started/python_api.md), and [Sweep a temperature](sweep.md) helps, and a lock-in and a Lakeshore 350 on your cryostat</p>

The **queue** is how an experiment runs a night's work: the tasks in it run one after another, while you do something else. In this tutorial you plan one: a sweep as the sample warms, and another as it cools, to see whether it behaves the same both ways. You start every run with a task queued in code, pause and abort what is running, rearrange what is waiting, and save the queue as a **sequence** to run again another night.

You carry on with `sample.py` from [Sweep a temperature](sweep.md): the lock-in and the Lakeshore at your addresses, with `SetTemperature` and `Sweep`.

<div class="gs" data-files="sample.py:versions" data-lines="24" data-term-lines="3" markdown>

<div class="gs-stage" markdown>

<div class="gs-notes" markdown>

<section class="gs-step" data-given markdown>

## Start from the sweep

```python title="sample.py"
--8<-- "examples/usage/queue/sample_1.py"
```

This is `sample.py` as [Sweep a temperature](sweep.md) left it: the lock-in and the Lakeshore, `SetTemperature`, and `Sweep`, which steps the temperature with a file at each step. If you haven't done that tutorial, copy it, with your addresses.

**More:** [Sweep a temperature](sweep.md), which builds it.
{ .gs-more }

</section>

<section class="gs-step" markdown>

## Queue a task as the experiment starts

```python title="sample.py" hl_lines="137-138"
--8<-- "examples/usage/queue/sample_2.py"
```

`task_managers["main"]` is the queue the interface shows, and `add_task` puts a task in it from code. Queued in `setup()`, it runs as soon as the experiment starts: here every run begins by taking the sample to 10 K. Choose where your runs should start.

A task queued in code takes any inputs, since no form has to show them.

**More:** [`task_managers`](../reference/python_api/experiment.md#pyacquisition.core.experiment.Experiment.task_managers), and [the task manager](../reference/python_api/task_manager.md).
{ .gs-more }

</section>

<section class="gs-step" markdown>

## Queue a night's work

```bash
uv run sample.py
```

`SetTemperature` is running, from `setup()`. In the **Queue** tab, choose **Add task**, then **Sweep**: **Start Kelvin** 10, **Stop Kelvin** 20, **Step** 2 and **Dwell** 60, say, and **Add to queue**. Then another, from 20 back to 10. The window stays open, so you can add them in turn, and **Done** closes it.

They wait under **2 queued**, numbered, and each starts when the one before has finished. You can leave them to run.

**More:** [the Queue tab](../reference/interface.md#the-dock).
{ .gs-more }

</section>

<section class="gs-step" markdown>

## Pause, resume and abort

**Pause** stops the running task at its next wait, and calls its `on_pause`, so `SetTemperature` holds the cryostat. Nothing new starts. **Resume** carries on from there.

**Abort**, once you confirm, stops the running task at once, and its `teardown` runs. Then the queue **pauses**, since the tasks behind it may rely on it having finished. Press **Resume** to go on with them. A task that fails pauses the queue in the same way, with an alert saying why.

**More:** [pausing, and what a task does then](write_task.md#hold-the-hardware-when-paused).
{ .gs-more }

</section>

<section class="gs-step" markdown>

## Rearrange what is waiting

Each waiting task has buttons: **up** and **down** move it one place, the copy button queues it again straight after itself, and **×** removes it. Or drag it by the handle at its left. The running task's copy button queues it again too.

**Clear queue** removes every waiting task, after asking, and leaves the running one alone.

**More:** [the Queue tab](../reference/interface.md#the-dock).
{ .gs-more }

</section>

<section class="gs-step" markdown>

## Save the queue as a sequence

Choose **Save…**, name it `hysteresis`, and **Save**. It says `Saved 2 tasks as hysteresis.`, then `Not saved, because they weren't queued from the interface or the API: SetTemperature.` A sequence keeps each task as it was queued, from a form or the API, so the task from `setup()` isn't in it. That one runs every time anyway.

It is saved in `sequences/hysteresis.json`, beside `data`, a file you can copy to another experiment.

**More:** [sequences in the Web API](../reference/web_api.md#sequences).
{ .gs-more }

</section>

<section class="gs-step" markdown>

## Load it again

Another night, choose **Load…**: `hysteresis` is listed with its tasks, and **Load** queues them after anything already waiting. Loading is all or nothing: if a task can't be queued, because its inputs no longer fit, say, nothing is, and it says why.

**More:** [sequences in the Web API](../reference/web_api.md#sequences), to load one from a script.
{ .gs-more }

</section>

</div>

</div>

</div>

!!! success "Checkpoint"
    `SetTemperature` runs as the experiment starts, and the two sweeps wait behind it, under **2 queued**. **Save…** says `Saved 2 tasks as hysteresis.`, and `sequences/hysteresis.json` holds the two sweeps. **Load…** lists `hysteresis`, and loading it queues the same two sweeps again.

??? failure "Something not working?"
    - **The queue stops after an abort, or after a task fails.** That is on purpose: press **Resume** to go on, or **Clear queue** first.
    - **A task queued in `setup()` is missing from a saved sequence.** Only tasks queued from the interface or the API are saved, and saving says which were left out.
    - **Loading a sequence queues nothing, and names a task.** That task isn't registered in this experiment, or an input no longer fits it. Loading is all or nothing.
    - **The tasks behind a PID never start.** A task that never finishes holds up its whole queue. Give it a queue of its own: see [Hold a temperature with PID](pid.md).

## What you learned

- The queue runs its tasks one after another. `task_managers["main"].add_task` queues one from code, which runs as the experiment starts.
- **Pause** holds the running task, and calls its `on_pause`. **Abort** stops it and runs its `teardown`, and then the queue pauses, as it does after a failure.
- Waiting tasks can be moved, copied and removed.
- **Save…** keeps the queue as a sequence, a file in `sequences`, and **Load…** queues it again.

Next: [Hold a temperature with PID](pid.md) runs a control loop on a second queue, beside this one.
