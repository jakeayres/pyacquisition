# The Interface and the API

[Lesson 1](first_experiment.md) introduces running an experiment and the window it opens. This page has the detail: every window and menu, running without the interface, and the local web API.

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

The interface has a menu down the left edge, and its tabs change what is shown in the left part of the window. The right 58% is a live plot of every numeric measurement against one of the measurements, as points, in the colour of its card in **Live Data**, on the same black as the rest of the interface. It stays as it is whichever tab is shown. Everything the plot offers on a right click is there, and so are **Clear** and the **x-axis** choice. The x axis is always a measurement, since the plot has no time of its own: if you want time, measure it, for example with the clock's `timestamp_ms`. It starts as the measurement called `time` if there is one, or else the first. The legend is a column of small coloured pills to the right of the plot, under the plot's choices: click one to hide its points, and click it again to show them, and tick **Normalise** to draw each measurement from 0 to 1 of its own range, which is what to do when the measurements are of very different sizes. **Autofit**, which starts ticked, keeps the axes fitted to the data as it arrives, with a margin of 5% of the range of the data at each side so that the extreme points are not on the edge. It unticks itself as soon as you drag or scroll the plot or its axes, so that it stays where you put it; tick it again to fit the axes again.

**Pages**

| Tab | Shows |
|---|---|
| **Experiment** | The **Data File** and **Live Data** windows, one under the other. |
| **Task Queue** | The task queue: for each task manager, whether it is running or paused, the task that is running now, and the tasks waiting behind it, with a **+** card to add one. |
| **Instruments** | A card for every instrument, with how many endpoints it has. Click a card to list its queries and commands, and click one to open the window that asks for its inputs and sends the request. |
| **Logs** | The **Log**, filling the page: messages from the experiment as they happen, one line each, with a level tag in colour by severity. Choose the lowest level to show with the buttons under the title. |

**Windows on the Experiment and Task Queue pages**

| Window | Shows |
|---|---|
| **Data File** | The data file that is being written and the name the next one would get, and its folder, with a box and button to start the next file. |
| **Live Data** | The latest value of every measurement, updating as it arrives. Its header says whether data is arriving. |

The **Live Data** and **Task Queue** windows have a plain header with a thin line under it. The **Live Data** header turns amber, with a **STALE** badge, if no measurement has arrived for a few seconds, and says **WAITING** before the first one.

The pause icon at the right of the **Live Data** header pauses the measurements. While they are paused the header and its lines turn amber, and the cards are drawn in muted colours, so that it is clear that nothing is updating. Press it again to resume. In the **Task Queue** window the running task is a green card, and it turns amber while the task manager is paused, and red while the task is being aborted. The tasks waiting behind it are blue cards. The icon at the right of the header pauses and resumes the task manager, and the red X on a card aborts the running task or removes a waiting one.

Clicking an endpoint on the **Instruments** page, or a task in the list from the **+** card, opens a small window that describes what it does, has a box for each input it needs, and a **Send Request** button. The reply appears in the window.

Try it. Open the **Instruments** tab, click the **clock** card, choose **Time** and press **Send Request** to read the clock.

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

Set `gui = False` to run headless, for example on a computer with no display. Data is still recorded and tasks still run.

```python
class MyExperiment(Experiment):
    data_path = "my_data"
    gui = False
```

## The API

While the experiment is running it serves a local HTTP API, and the interface is simply a client of it. Everything you can do from the menus you can also do with a plain web request, from a browser, a notebook or another script.

Open [http://localhost:8000/docs](http://localhost:8000/docs) in your browser (adjust the port if you changed `api_server_port`) for an interactive page listing every endpoint, where you can try them out. For example, with the experiment above running, [http://localhost:8000/clock/time](http://localhost:8000/clock/time) returns the clock reading.

## An alternative way to start

`pyacquisition --py my_experiment.py` finds the first `Experiment` class in the file, creates it and runs it, so the file needs no `if __name__ == "__main__":` block. It only works for experiments in a single, self-contained file: modules that sit next to your script are not importable this way. Otherwise use `python my_experiment.py`.
