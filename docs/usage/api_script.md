# Drive an experiment from a script

<p class="pa-meta" markdown="span">About 15 minutes · Needs [Getting Started](../getting_started/python_api.md)</p>

The interface is one client of a running experiment's **web API**, and your own code can be another. From a script or a notebook, you can read a value, send a command, queue tasks, wait for them, and stop the experiment, so that a series of runs goes on without you. In this tutorial you run Getting Started's lab with no window, and drive it from `drive.py`: set the lock-in's frequency, record two files, and stop.

It starts where [2. The Python API](../getting_started/python_api.md) ends: your `my-lab` project, with `rig.toml` and `lab.py`. `drive.py` uses `requests`, which comes with PyAcquisition.

<div class="gs" data-files="lab.py:versions drive.py:versions" data-lines="22" data-term-lines="7" markdown>

<div class="gs-stage" markdown>

<div class="gs-notes" markdown>

<section class="gs-step" data-given markdown>

## Start from the Getting Started lab

```python title="lab.py"
--8<-- "examples/usage/api_script/lab_1.py"
```

This is `lab.py` as [2. The Python API](../getting_started/python_api.md) left it: an experiment made from `rig.toml`, with the lock-in at 137 Hz, a calculation, and the `Record` task.

**More:** [2. The Python API](../getting_started/python_api.md), which builds it.
{ .gs-more }

</section>

<section class="gs-step" data-result="[Experiment] API server on port 8000" markdown>

## Run the experiment without a window

```python title="lab.py" hl_lines="24"
--8<-- "examples/usage/api_script/lab_2.py"
```

```bash
uv run lab.py
```

`gui = False` runs it with no window: on a PC with no screen, say, or when a script is in charge. It measures, records and runs tasks as before, and the interface is still at `http://localhost:8000`, in a browser, whenever you want to look.

Leave it running, and open a second terminal in `my-lab` for the rest.

**More:** [`gui`, and the other options](../reference/experiment_options.md).
{ .gs-more }

</section>

<section class="gs-step" data-new-file="drive.py" markdown>

## Read a value

```python title="drive.py"
--8<-- "examples/usage/api_script/drive_1.py"
```

```bash
uv run drive.py
```

```text
The lock-in is at 137.0 Hz
```

Every query and command of every instrument is at an address of its own: `/lockin/get_frequency` is the lock-in's `get_frequency`. `call` asks the experiment for one, with its arguments as parameters, and gives the `data` of its answer. `raise_for_status` turns an answer that is an error into a Python error, so a mistake stops the script at once.

**More:** [the Web API](../reference/web_api.md#instruments).
{ .gs-more }

</section>

<section class="gs-step" markdown>

## Send a command

```python title="drive.py" hl_lines="15-16"
--8<-- "examples/usage/api_script/drive_2.py"
```

```bash
uv run drive.py
```

```text
The lock-in is at 137.0 Hz
Now it is at 211.0 Hz
```

A command is called the same way, with its arguments by name: `set_frequency`'s is `frequency`. It answers no data, so `call` gives `None`, and reading the frequency back shows it took.

**More:** [the SR 830's commands](../reference/instruments/sr_830.md).
{ .gs-more }

</section>

<section class="gs-step" markdown>

## Queue a task

```python title="drive.py" hl_lines="18-19"
--8<-- "examples/usage/api_script/drive_3.py"
```

```bash
uv run drive.py
```

```text
Record is queued
```

A registered task is queued at `/tasks/` and its label, in lower case with spaces as `_`: `Record` is `/tasks/record`, with its inputs as parameters. Here it records two files of 5 s each. It runs in its turn, as if queued from the interface, and the script goes on at once.

**More:** [the queue's endpoints](../reference/web_api.md#tasks-and-the-queue).
{ .gs-more }

</section>

<section class="gs-step" markdown>

## Wait for the queue to empty

```python title="drive.py" hl_lines="1 23-26"
--8<-- "examples/usage/api_script/drive_4.py"
```

```bash
uv run drive.py
```

```text
The queue is empty
```

`/task_manager/current_task` is the running task, or `None`, and `/task_manager/task_list` the tasks waiting. The loop asks both every second until neither has anything, so the script carries on once `Record` has finished: here after about 10 s. Then it can read the new data files, and decide what to queue next.

**More:** [the queue's endpoints](../reference/web_api.md#tasks-and-the-queue), and [Read your data](read_data.md).
{ .gs-more }

</section>

<section class="gs-step" data-result="The lock-in's output is turned down." markdown>

## Stop the experiment

```python title="drive.py" hl_lines="28-29"
--8<-- "examples/usage/api_script/drive_5.py"
```

```bash
uv run drive.py
```

```text
The experiment is stopping
```

`/experiment/shutdown` stops the experiment as closing its window would: the queue is stopped, `teardown()` runs, and the connections close. In the first terminal, `lab.py` says `The lock-in's output is turned down.` and ends.

**More:** [the experiment's endpoints](../reference/web_api.md#the-experiment).
{ .gs-more }

</section>

<section class="gs-step" markdown>

## Find every endpoint

With the experiment running, open `http://localhost:8000/docs` in a browser. It lists every address the experiment has, grouped by what they are for, with each one's parameters and what it answers, and **Try it out** calls one from the page. Your own instruments and tasks are there too.

The endpoints a script most often needs are in [Reference › Web API](../reference/web_api.md).

**More:** [the Web API](../reference/web_api.md).
{ .gs-more }

</section>

</div>

</div>

</div>

!!! success "Checkpoint"
    `drive.py` prints `The lock-in is at 137.0 Hz`, `Now it is at 211.0 Hz`, `Record is queued`, `The queue is empty` about 10 s later, and `The experiment is stopping`. `data` has two new files, `run 1` and `run 2`, and `lab.py` ends with `The lock-in's output is turned down.`

??? failure "Something not working?"
    - **`requests.exceptions.ConnectionError: … No connection could be made because the target machine actively refused it`.** No experiment is running at `LAB`'s address: start `lab.py` first, and check its port.
    - **`requests.exceptions.HTTPError: 404 Client Error: Not Found for url: …/lockin/get_frequncy`.** The address is mistyped. `/docs` lists them all.
    - **`requests.exceptions.HTTPError: 422 Client Error: Unprocessable Entity for url: …/lockin/set_frequency?freq=211.0`.** An argument's name or value is wrong: `set_frequency`'s is `frequency`.
    - **The script waits for ever.** The queue is paused, after a task failed or was aborted, so the tasks waiting never start: `/task_manager/status` says `Paused`, and `/task_manager/resume` carries on.

## What you learned

- A running experiment has a web API. Each query and command is at `/<instrument>/<method>`, with its arguments as parameters.
- `gui = False` runs it with no window, and the interface is still in a browser at its address.
- A task is queued at `/tasks/<label>`, and the queue's state is at `/task_manager/...`, so a script can wait for it.
- `/experiment/shutdown` stops the experiment, with its teardown, and `/docs` lists every endpoint.

Next: [Build a standalone app](standalone_app.md), to run an experiment on a PC with no Python.
