# Write a task

<p class="pa-meta" markdown="span">About 20 minutes · Needs [Getting Started](../getting_started/python_api.md), and a lock-in and a Lakeshore 350 on your cryostat</p>

A **task** is a procedure the experiment runs from a queue, while it goes on measuring: go to a temperature, wait an hour, start a new file. [2. The Python API](../getting_started/python_api.md) builds one out of two that come with PyAcquisition. In this tutorial you write one that drives hardware: `SetTemperature` takes a sample to a temperature and waits until it is there, shows how far along it is, refuses a temperature it shouldn't go to, and holds the cryostat where it is if you pause it. You will use it in most experiments with a cryostat.

You write `sample.py` in your `my-lab` project, for a sample measured with an SR830 in a cryostat with a Lakeshore 350. Change the addresses, the input and the loop to your own. With a Lakeshore 340, use `Lakeshore_340`: the task's commands are the same.

<div class="gs" data-files="sample.py:versions" data-lines="26" data-term-lines="3" markdown>

<div class="gs-stage" markdown>

<div class="gs-notes" markdown>

<section class="gs-step" data-given markdown>

## Start from your measurements

```python title="sample.py"
--8<-- "examples/usage/write_task/sample_1.py"
```

Copy this into `sample.py`. It is the sample from [Tune your measurements](measurements.md), at its third step: a clock, the Lakeshore and the lock-in at their addresses, measuring the time, the lock-in's `x` and `y`, and the temperature, `T`. `SENSOR` and `LOOP` name the Lakeshore's input for the sample's thermometer and its heater's loop, once, for the task to use.

**More:** [Tune your measurements](measurements.md), which builds it.
{ .gs-more }

</section>

<section class="gs-step" markdown>

## Write a task with inputs

```python title="sample.py" hl_lines="1 3 11-22"
--8<-- "examples/usage/write_task/sample_2.py"
```

A task is a class based on `Task`, marked `@dataclass`. Its **inputs** are the fields below the docstring: `kelvin`, which the form asks for, and `rate`, which starts at its default. They can be `int`, `float`, `str` or `bool`, which the form can show. The docstring's first line describes it in the interface.

`run()` is what it does. It reaches the cryostat through `experiment.instruments`, turns its ramp on, and sets the setpoint. `self.log` writes to the log, under the task's name.

**More:** [`Task`](../reference/python_api/task.md), and [the Lakeshore 350's commands](../reference/instruments/lakeshore_350.md).
{ .gs-more }

</section>

<section class="gs-step" markdown>

## Wait until it gets there

```python title="sample.py" hl_lines="17 25-30"
--8<-- "examples/usage/write_task/sample_3.py"
```

`self.wait_until` waits until `arrived()` is true, checking it every second, while the experiment goes on measuring. `arrived()` is true once the sample is within `tolerance` of the setpoint. After an hour, `timeout` gives up with a `TimeoutError`, so a heater that has failed doesn't hold up the queue for ever.

A task's waits are where it can be paused and aborted. Wait with them, never `time.sleep()`, which would stop the whole experiment while it waits.

**More:** [`wait_until`](../reference/python_api/task.md#pyacquisition.core.task_manager.task.Task.wait_until), and [`sleep`](../reference/python_api/task.md#pyacquisition.core.task_manager.task.Task.sleep).
{ .gs-more }

</section>

<section class="gs-step" markdown>

## Show its progress

```python title="sample.py" hl_lines="19-21 25 32-33"
--8<-- "examples/usage/write_task/sample_4.py"
```

`self.set_progress` says how far along the task is, as a fraction: here, how much of the way from where the sample started it has come. `note` says what it is doing, the temperature now. The **Queue** tab and the top bar show it as a bar, with an estimate of the time left.

`description` is what the queue says the task is doing, `Go to 10.0 K`, in place of the docstring.

**More:** [`set_progress`](../reference/python_api/task.md#pyacquisition.core.task_manager.task.Task.set_progress), and [`description`](../reference/python_api/task.md#pyacquisition.core.task_manager.task.Task.description).
{ .gs-more }

</section>

<section class="gs-step" markdown>

## Check what was asked

```python title="sample.py" hl_lines="19-22"
--8<-- "examples/usage/write_task/sample_5.py"
```

A task is made when it is queued, and `__post_init__` runs then, so a check there refuses a mistake before anything happens. Here a temperature outside what the cryostat can do, 1.5 to 300 K: set your own. The form shows `500.0 K is out of range: 1.5 to 300 K.`, and nothing is queued.

`super().__post_init__()` must come first. It sets up what the task needs to run.

**More:** [`Task`](../reference/python_api/task.md).
{ .gs-more }

</section>

<section class="gs-step" markdown>

## Hold the hardware when paused

```python title="sample.py" hl_lines="44-60"
--8<-- "examples/usage/write_task/sample_6.py"
```

Pausing a task stops its code, not your hardware: the cryostat would ramp on. `on_pause` says what a pause should do to the hardware, and is called at once. Here it holds the setpoint where the ramp has got to, and `on_resume` sets it ramping again.

`teardown` runs however the task ends, finished, aborted or failed, so it holds the setpoint too. An aborted ramp then stops where it is.

**More:** [`on_pause` and `on_resume`](../reference/python_api/task.md#pyacquisition.core.task_manager.task.Task.on_pause), and [`teardown`](../reference/python_api/task.md#pyacquisition.core.task_manager.task.Task.teardown).
{ .gs-more }

</section>

<section class="gs-step" data-result="[SetTemperature] At 10.0 K" markdown>

## Register it, and run the experiment

```python title="sample.py" hl_lines="87"
--8<-- "examples/usage/write_task/sample_7.py"
```

```bash
uv run sample.py
```

`register_task` offers the task in the interface, as **Set Temperature**. In the **Queue** tab, choose **Add task**, then **Set Temperature**, give **Kelvin** a temperature your cryostat can reach, and **Add to queue**. It starts at once, and its bar fills as `T` gets closer. **Pause** holds the setpoint where the ramp has got to, and the log says `Holding at …` with it. **Resume** ramps on, and the task ends with `At …` once the sample is within `tolerance`.

**More:** [`register_task`](../reference/python_api/experiment.md#pyacquisition.core.experiment.Experiment.register_task), and [the Queue tab](../reference/interface.md#the-dock).
{ .gs-more }

</section>

</div>

</div>

</div>

!!! success "Checkpoint"
    **Set Temperature** is in **Add task**. Queued at 10 K, the **Queue** tab shows `Go to 10.0 K` with a bar that fills as `T` gets closer, and the task ends with `At 10.0 K` in the log once the sample is within 0.05 K. Paused, the log says `Holding at …`, and `T` settles there. Aborted, once you confirm, it logs `Holding at …` and `Task aborted.` Queued at 500 K, the form says `500.0 K is out of range: 1.5 to 300 K.`, and nothing is queued.

??? failure "Something not working?"
    - **The experiment stops as soon as the task starts, with `'SetTemperature' object has no attribute '_abort_event'`.** `__post_init__` doesn't call `super().__post_init__()`. Put it first.
    - **Add to queue says `The server had an error handling the request (HTTP 500)`, and the terminal says `AttributeError: 'SetTemperature' object has no attribute 'kelvin'`.** The class isn't marked `@dataclass`, so it has no inputs.
    - **The task fails at once, with `'float' object is not callable`.** An input has the name of something a task already has, here `start`. Other such names are `name`, `run`, `setup`, `teardown`, `pause`, `resume`, `abort`, `log`, `sleep`, `description` and `parameters`. Choose another, such as `start_kelvin`.
    - **The experiment freezes while the task waits.** It waits with `time.sleep()`, which stops everything. Use `await self.sleep()` or `await self.wait_until()`.

## What you learned

- A task is a `@dataclass` based on `Task`. Its fields are its inputs, and `run()` is what it does, with the instruments from `experiment.instruments`.
- `wait_until` and `sleep` wait while the experiment goes on, and are where a task can be paused or aborted.
- `set_progress` and `description` say what the task is doing, in the **Queue** tab and the top bar.
- A check in `__post_init__` refuses a bad input when the task is queued.
- `on_pause` and `on_resume` say what pausing does to the hardware, and `teardown` leaves it safe however the task ends.

Next: [Sweep a temperature](sweep.md) runs `SetTemperature` at each step of a sweep, with a file for each.
