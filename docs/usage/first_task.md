# 4. Your First Task

<p class="pa-meta" markdown="span">About 12 minutes · Needs [lesson 3](recording_data.md)</p>

So far you have driven the rig by clicking. In this lesson you will write a **task**: a procedure that runs on your experiment by itself. You will write one that ramps the cryostat to a temperature and waits until it gets there.

## What a task is

A task is a procedure that you want to run on your experiment: ramp a temperature, wait an hour, start a new file, sweep a field. Tasks are run from a queue, one at a time, and can be paused or aborted while they run.

You write a task as a class with a `run()` method. Everything else (the queue, the buttons, the log messages, the form to queue it with) comes for free.

A few tasks are already included. Open the **Queue** tab (press ++2++) and press **Add task**:

![The Add a task window, with the standard tasks](../images/tutorial/add-task.png){ .pa-shot .pa-medium }

`NewFile` starts a new data file, `WaitFor` waits for a time, and `WaitUntil` waits until a clock time. Your own tasks will join them in a moment. Press **Done** to close it.

## Write the task

Add this to `my_experiment.py`, above your `MyExperiment` class. The notes beside the code say what each part does:

<div class="pa-annot" data-source="examples/tutorial/step_4_first_task.py:task" markdown>

<div class="pa-ide" markdown>

```python title="my_experiment.py" linenums="1" hl_lines="1-3 5-6 8-10 12-16 18-22 24-28"
--8<-- "examples/tutorial/step_4_first_task.py:task"
```

</div>

<div class="pa-annot__notes" markdown="0">
<div class="pa-note" style="--from: 1; --to: 3" data-contains="class SetTemperature"><b>A task is a dataclass</b><span>Every task is a <code>@dataclass</code> that inherits <code>Task</code>. Its docstring describes it when you queue it.</span></div>
<div class="pa-note" style="--from: 5; --to: 6" data-contains="ramp_rate"><b>Inputs</b><span>Annotated attributes become its form: int, float, str or bool.</span></div>
<div class="pa-note" style="--from: 8; --to: 10" data-contains="description"><b>Describe it</b><span>Shown for a task waiting in the queue. Optional, but worth writing.</span></div>
<div class="pa-note" style="--from: 12; --to: 16" data-contains="self.log"><b>The work</b><span><code>run()</code> is <code>async</code>. Instrument calls are ordinary calls, and <code>self.log</code> writes to the log.</span></div>
<div class="pa-note" style="--from: 18; --to: 22" data-contains="wait_until"><b>Wait, never sleep</b><span><code>wait_until</code> checks every second, and it is where the task can be paused or aborted.</span></div>
<div class="pa-note" style="--from: 24; --to: 28" data-contains="teardown"><b>Always runs</b><span><code>teardown()</code> runs however the task ends: finished, aborted or failed. Here it stops the ramp where the sample is.</span></div>
</div>

</div>

An input without a default, like `kelvin`, must be given. One with a default, like `ramp_rate`, may be left out when you create the task in code. `experiment.instruments` is how a task reaches the instruments you added in `setup()`, by id.

`run()` is an `async` method, which sounds like more than it is. You only need three rules:

1. **Wait with `await self.sleep(seconds)` or `await self.wait_until(condition)`.** They wait without freezing anything else, and they are the places where you can **pause or abort** the task. Here, `wait_until` checks every second whether the temperature is within 0.05 K of the target. Never use `time.sleep()` in a task: it would freeze the whole experiment while it waits.
2. **Say what is happening with `self.log("...")`.** Whatever you log is written to the log, labelled with the name of the task.
3. **Everything else is ordinary Python.** Loops, conditions, calling instrument methods, arithmetic. Instrument calls are normal function calls with no `await`.

Read `run()` again with those rules in mind. It sets the ramp rate and the setpoint (two commands), logs what it did, and waits until the temperature is within 0.05 K of the target. When it gets there, it logs a message and finishes.

**Why `teardown()` matters.** It **always runs when the task ends**: when it finishes, when you abort it, and when it hits an error. Use it to leave your instruments somewhere safe. Wherever the task stopped, the setpoint is set to the temperature the sample is at right now, so the controller stops ramping and simply holds. Without it, aborting a ramp to 4 K would leave the setpoint at 4 K and the cryostat still heading there.

!!! warning "Inputs cannot be called `start`, `name`, `run` and so on"
    A task already has attributes called `name`, `description`, `parameters`, `run`, `setup`, `teardown`, `pause`, `resume`, `abort`, `log` and `sleep` (and a few more), and `register_task` uses `label`. Do not name an input after any of them. The full list of pitfalls is in [Writing tasks](tasks.md#things-to-watch-for).

## Register it

A task must be registered in `setup()` to be queued from the interface. Add the imports the task needs at the top of the file, and this line at the end of `setup()`:

```python
self.register_task(SetTemperature, label="Set Temperature")
```

Pass the class itself, not an instance: no brackets. `label` is the name it is listed by. Here is the whole file, with everything that is new highlighted:

```python title="my_experiment.py" linenums="1" hl_lines="2 4 6-10 14-16 18-19 21-23 25-29 31-35 37-41 71"
--8<-- "examples/tutorial/step_4_first_task.py"
```

## Run it

```
uv run my_experiment.py
```

Open the **Queue** tab, press **Add task**, and pick **Set Temperature**. Its form has a box for each input, under the docstring. `Ramp Rate` already says `30`, its default in your code, and `Kelvin` is marked with a star because it has none. Type `4` into `Kelvin`.

![Set Temperature in the Add a task window, with kelvin 4 and ramp_rate 30](../images/tutorial/set-temperature-form.png){ .pa-shot .pa-medium }

Press **Add to queue**, then **Done**. The task joins the queue and starts at once. Look at what happened:

![The Queue tab shows SetTemperature running, and the plot shows T falling](../images/tutorial/task-running.png){ .pa-shot }

- The **Queue** tab shows `SetTemperature` running, with its description, its inputs and how long it has been running. Its name is in the top bar too, whichever tab is open.
- The plot shows `T` falling.
- The **Logs** tab (press ++4++) follows the task: the task manager took it from the queue, the task started, and then the message you logged, `Ramping to 4.0 K`.

About forty seconds later the log reads `Arrived at 4.0 K`, the queue says **Nothing is running**, and the task is done. Queue it again with `Kelvin` `20` to warm back up.

!!! success "Checkpoint"
    Running **Set Temperature** with `kelvin` 4 takes `T` from 20 K down to 4 K, the log shows `Ramping to 4.0 K` and then `Arrived at 4.0 K`, and the **Queue** tab goes back to **Nothing is running**.

??? failure "Something not working?"
    - **`T` dives to the target in a few seconds instead of ramping for about forty.** `ramp_rate` was `0`, and the simulated controller treats a rate of zero as "no ramp, jump to the setpoint". Leave it at `30`.
    - **The task never finishes.** It is waiting for `T` to be within 0.05 K of `kelvin`. Check that `kelvin` is a temperature the simulated cryostat can reach, such as 4 or 20.
    - **`Set Temperature` is not in the list.** Check that the `register_task` line is inside `setup()`, and that you passed the class and not `SetTemperature()`.
    - **The task ends at once, and the queue pauses.** An error inside a task does not crash the experiment. An alert says which task failed and why, and the **Logs** tab has it as `Task failed: ...`. The queue pauses, so that nothing else runs on top of a task that failed. Fix the cause, and press **Resume** in the **Queue** tab.

## What you learned

- A **task** is a `@dataclass` class with an `async def run()`.
- **Wait with `await self.sleep()` and `await self.wait_until()`** (that is where it can be paused and aborted), **say what is happening with `self.log()`**, and put safe-state code in **`teardown()`**.
- Task inputs become its form, which starts at their defaults.
- Register a task in `setup()` to run it from the interface.

Everything about how tasks run and what can go wrong is in [Writing tasks](tasks.md).

Next: [build a whole sweep out of tasks like this one](building_a_sweep.md).
