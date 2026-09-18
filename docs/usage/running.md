# Running an Experiment

## Start it

Run your script like any other Python script:

```
python my_experiment.py
```

or, if you manage your project with `uv`:

```
uv run my_experiment.py
```

After a moment a window opens. The experiment is now running: it is polling your measurements and saving them to a file.

## Always use a main guard

The script above ends with:

```python
if __name__ == "__main__":
    MyExperiment().run()
```

This is not optional. The graphical interface runs in a **separate process**, which starts by importing your script again. Without the guard, that second process would try to start a second experiment of its own. On Windows this fails straight away with an error such as *"An attempt has been made to start a new process before the current process has finished its bootstrapping phase"*.

Put `MyExperiment().run()` (and anything else that starts things running) under `if __name__ == "__main__":`.

## The interface

The interface has a menu bar across the top and four windows.

**Windows**

| Window | Shows |
|---|---|
| **Current File** | The data file (and its folder) that is being written. |
| **Task Queue** | Whether the task manager is running or paused, the task that is running now, and the tasks waiting behind it. |
| **Live Data** | The latest value of every measurement, updating as it arrives. |
| **Logs** | Messages from the experiment as they happen, in colour by severity. |

**Menus**

| Menu | Contains |
|---|---|
| **Scribe** | Controls for the data file, including starting a new one. |
| **Rack** | Pause and resume measuring, and change the measurement period. |
| **Instruments** | One submenu per instrument, with every query and command it offers. |
| **Task Manager** | Pause, resume and abort the running task, and manage the queue. |
| **Tasks** | One entry for every task you have registered. |
| **Plots** | **New Plot** opens a live plot of your measurements. |

Choosing an item from a menu opens a small window that describes what it does, has a box for each input it needs, and a **Send Request** button. The reply appears in the window.

Try it. Open **Instruments → clock**, choose **Time** and press **Send Request** to read the clock, then open **Plots → New Plot** to watch `time` on a live plot.

## Your data

Data is written to a comma separated file in the folder you chose with `data_path`. Each file has a header row of measurement names, then one row per measurement cycle:

```
time
0.030038833618164062
0.295818567276001
0.5458414554595947
```

Every measurement you add becomes another column.

Files are named `<block>.<step> <title>.data`, for example `00.00 start.data`.

- Each time you run the experiment, a new **block** is started, so nothing from a previous run is overwritten. The first run in a folder writes `00.00 start.data`, the next run `01.00 start.data`, and so on.
- Within a block, starting a new file increments the **step**: `00.01 gaussian.data`, `00.02 uniform.data`. You can start a new file from the **Scribe** menu, or from a task. [Measurements and data files](measurements.md) covers this in more detail.

The log is written to `debug.log` (see [`log_path` and `log_file_name`](setting_up.md#experiment-options)).

## Stopping

Close the window. This shuts down the whole experiment cleanly, including `teardown()`.

## Running without the interface

Pass `gui=False` to run headless, for example on a computer with no display. Data is still recorded and tasks still run.

```python
super().__init__(data_path="my_data", gui=False)
```

## The API

While the experiment is running it serves a local HTTP API, and the interface is simply a client of it. Everything you can do from the menus you can also do with a plain web request, from a browser, a notebook or another script.

Open [http://localhost:8000/docs](http://localhost:8000/docs) in your browser (adjust the port if you changed `api_server_port`) for an interactive page listing every endpoint, where you can try them out. For example, with the experiment above running, [http://localhost:8000/clock/time](http://localhost:8000/clock/time) returns the clock reading.

## An alternative way to start

`pyacquisition --py my_experiment.py` finds the first `Experiment` class in the file, creates it and runs it, so the file needs no `if __name__ == "__main__":` block. It only works for experiments in a single, self-contained file: modules that sit next to your script are not importable this way. Otherwise use `python my_experiment.py`.
