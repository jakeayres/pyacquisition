# 2. The Python API

<p class="pa-meta" markdown="span">About 10 minutes · Needs [1. The Config File](config_file.md), and a little Python</p>

A config file says what the rig is, but not what to do with it. For that there is Python: a column worked out from others as each row is recorded, say, or a procedure the experiment runs by itself. In this part you keep `rig.toml` as it is, and write a short Python file beside it that builds on it. It uses a class, a function and a `for` loop, and nothing harder.

<div class="gs" data-mode="versions" data-file="lab.py" data-lines="20" data-term-lines="4" markdown>

<div class="gs-stage" markdown>

<div class="gs-notes" markdown>

<section class="gs-step" data-new-file data-result="The same interface, now called Lab." markdown>

## Run the file from Python

Make a file called `lab.py` beside `rig.toml`, and run it:

```python title="lab.py"
--8<-- "examples/getting_started/lab_1.py"
```

```bash
uv run lab.py
```

Every experiment is an `Experiment`, and `Lab` is a kind of your own, which adds nothing yet. `Lab.from_config("rig.toml")` makes a `Lab` with the file's instruments and measurements, and `.run()` starts it, as `pyacquisition --toml` did.

The window is the same, but titled `Lab`, after the class. Keep `.run()` under `if __name__ == "__main__":`: the interface starts by importing this file again, and without that line it would start a second experiment.

**More:** [combining a config file with Python](../usage/toml_config.md#combining-a-config-file-with-python), and [why the main guard matters](../usage/running.md#always-use-a-main-guard).
{ .gs-more }

</section>

<section class="gs-step" markdown>

## Add a column

```python title="lab.py" hl_lines="7 8"
--8<-- "examples/getting_started/lab_2.py"
```

`setup()` is where an experiment adds what the file can't. It runs once as the experiment starts, after the file's instruments and measurements are in.

A **calculation** is a function of each row, a `dict` of column names to values, that returns new columns. This one makes `power`, the square of `wave`. It is saved beside `wave` in the data file, and can be plotted like any measurement.

**More:** [calculations](../usage/calculations.md), with built-in ones such as a rolling mean, and [`setup()`](../usage/setting_up.md#setup-and-teardown).
{ .gs-more }

</section>

<section class="gs-step" markdown>

## Write a task

```python title="lab.py" hl_lines="1 3 4 7-18"
--8<-- "examples/getting_started/lab_3.py"
```

A **task** is a procedure: the experiment runs it from its queue, and goes on measuring while it does. It is a `dataclass` of `Task`. Its fields, with their types and defaults, are its inputs, and `run()` does the work. `run()` is `async`, so that waiting doesn't stop the measuring.

`Record` runs two ready-made tasks in turn, `files` times: `NewFile` starts a new data file, and `WaitFor` waits `seconds` seconds while rows go into it. `run_subtask()` runs a task and waits for it to finish, and `self.log()` writes to the **Logs** tab. The imports grow, to bring in `Task` and the two tasks.

**More:** [writing tasks](../usage/tasks.md), [what `run_subtask()` does](../usage/composing_tasks.md#what-run_subtask-does), and the ready-made [NewFile](../tasks/new_file.md) and [WaitFor](../tasks/wait_for.md).
{ .gs-more }

</section>

<section class="gs-step" markdown>

## Register it

```python title="lab.py" hl_lines="26"
--8<-- "examples/getting_started/lab_4.py"
```

`register_task` offers `Record` in the interface. It is listed in **Add task**, with its docstring as its description, and a form made from its fields, for `files` and `seconds`.

`label` is the name it is registered under. Without one, it is the class's name.

**More:** [registering tasks](../usage/tasks.md#registering-tasks), and [the tasks that come with PyAcquisition](../tasks/overview.md).
{ .gs-more }

</section>

<section class="gs-step" data-result="Record is in Add task. Queue it." markdown>

## Run it

```bash
uv run lab.py
```

A running experiment doesn't see changes to its file, so run it again.

In the **Queue** tab, choose **Add task**, then **Record**. Change its inputs if you like, and choose **Add to queue**. With nothing else waiting, it starts at once. It makes a new data file named `run 1` and records into it for 10 s, then `run 2`, then `run 3`, each with a `power` column.

In `data` they are numbered on from this run's first file: `03.01 run 1.data` after `03.00 start.data`, if you have run every step.

**More:** [the queue](../usage/running_tasks.md), and [pausing, resuming and aborting a task](../usage/running_tasks.md#pause-resume-and-abort).
{ .gs-more }

</section>

</div>

</div>

</div>

## What you built

Your task, in **Add task**, with a form made from its fields:

![The Add a task window: Record is in the list with its description, and its form asks for Files and Seconds](../images/getting_started/add-task.png){ .pa-shot }

And running. The queue shows `Record` and the step it is on, and the plot draws the new file over the one before it:

![Record running: the top bar shows 00.02 run 2.data and Record, and the queue shows WaitFor half done](../images/getting_started/record-running.png){ .pa-shot }

!!! success "Checkpoint"
    **Record** is in **Add task**. Queued, it writes three files, `run 1` to `run 3`, and each has a `power` column beside `wave`.

??? failure "Something not working?"
    - **Record isn't in Add task.** Run `uv run lab.py`, not `uv run pyacquisition --toml rig.toml`: the file on its own doesn't know about your task. Then check the `register_task` line.
    - **An error about a new process and bootstrapping (Windows).** `.run()` is not under the `if __name__ == "__main__":` line.

## What you learned

- `from_config` makes an experiment of your own class from the file. The file still describes the rig, and the class adds what a file can't say, in `setup()`.
- A **calculation** makes new columns from each row, saved beside the measurements.
- A **task** is a dataclass with an `async` `run()`. It can run other tasks, and once registered it is in **Add task**, with a form made from its fields.

Next: [Advanced Usage](../usage/advanced.md) takes each part further, a topic to a page.
