# The Interface and the API

[Lesson 1](first_experiment.md) introduces running an experiment and the window it opens. This page has the detail: every part of the interface, running without a window, and the local web API.

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

The window is a page served by the experiment itself, so you can also open it in a browser at [http://localhost:8000](http://localhost:8000) (the API server's address), on this computer or another. It has three parts: a slim bar across the top, the plots filling the window, and a **dock** of tabs along the bottom.

![The interface of the first experiment](../images/tutorial/first-run.png){ .pa-shot }

**The top bar**

| Part | What it does |
|---|---|
| **Data file** | The file being written. Click it for its folder (with buttons to copy the path and to open it), and to start a new file: type a title, tick **Start a new block** if you want one, and it shows the name the file will get. |
| **Measurements** | How often everything is measured, such as **Every 0.25 s**. Click it to change the period. It also says how long the loops really take, which is longer than the period if measuring takes longer, and then a **slow** marker appears on it. The button beside it pauses and resumes measuring. |
| **Running task** | The task that is running, and how far along it is, if it says. Click it to open the **Queue** tab. |
| **Bell** | Alerts: an error logged, a task that failed, data that stopped arriving, or the connection to the experiment lost. Each shows for a few seconds, and the bell keeps a list. |
| **Connected** | Whether the experiment is answering. If it stops, the page reconnects by itself when it can. |
| Keyboard, moon and power buttons | The keyboard shortcuts, the light or dark theme (it follows Windows until you choose), and stopping the experiment. |

**The plots**

Each plot shows one or more columns against another. The chips along its top are the columns plotted, each in its own colour (the same colour as its tile in the **Values** tab): click one to hide or show it, click its **×** to take it off, and use **+ Add** to add another. **against** chooses the horizontal axis. **Lines**, **Points** and **Both** choose how it is drawn. The axis button sets fixed limits or a log scale for either axis, the download button saves the plot as a picture, the data in view as a CSV file, or a Python script that draws it, as it looks or as a figure for a paper, and the last buttons copy or remove the plot.

- **Zoom** by dragging a box. A thin box zooms one axis only. **Pan** by dragging with Shift or the middle button, or by scrolling. Ctrl and the scroll wheel zoom about the pointer.
- While zoomed or panned, the plot holds that view as data arrives, and says **Autoscale off**. **Autoscale** there, or a double-click, sets it following the data again.
- Hover over a plot to read the values of the nearest row.
- **+ Add plot** adds another (up to six), and **Link x-axes** zooms and pans the x axes of plots against the same column together.
- The plots show the whole of the current data file, and the file before it, drawn fainter (the key at the top right hides or shows it). Calculated columns can be plotted too.
- **Export**, then **Python script (matplotlib)**, shows a script that draws the plot again with matplotlib, for a paper or a slide, with **Copy** to put it on the clipboard and **Save…** to save it as a file. It draws the same columns, labels, log axes, marks and colours, and the same limits if the plot was zoomed or had fixed limits. It reads the data files where they are (or beside itself, if they have moved), and draws the whole of each file as it stands when you run it, not only what the plot held. It needs pandas and matplotlib (`pip install pandas matplotlib`). It is plain code, meant to be changed: fonts, sizes, labels, anything.
- **Publication figure (APS style)** shows a script like it that draws a figure for a paper, in the style of APS journals (PRB, PRL): one column (3.375 in) wide and square, serif fonts, ticks inward on all four sides, and each axis scaled so its numbers are short, with the SI prefix in its unit (`x (mV)`, not `x (V)` with numbers like 0.0024). Running it saves the figure as a PDF beside the script. The size, the labels, the scales and every part of the style are plain lines at the top of the script, to change as you like.

    ![A figure of x and y against T through a transition, one APS column wide, from the simulated rig](../images/plots/publication-figure.png){ .pa-shot .pa-small }

**The dock**

| Tab | Shows |
|---|---|
| **Values** | A tile for each column: its latest value, its unit, where it comes from, and a small graph of its recent values. |
| **Queue** | Each task manager's queue: the task running, with how far along it is and **Abort**, and the tasks waiting, which can be dragged into a new order, moved, copied or removed. **Add task** queues a task from a form, **Pause** and **Resume** hold the queue, and **Save…** and **Load…** keep a queue as a sequence to use again. |
| **Instruments** | Every instrument, with its queries and commands. Pick one, fill in its form, and press **Read** or **Send**. The answers are kept beside the form, with how long each call took, and a button to copy it. |
| **Logs** | What the experiment is doing, as it does it, one line per message. Choose which levels to show, and search. Click a message to see all of it. |

Drag the top edge of the dock to make it taller or shorter, and click the open tab (or the arrow at the right) to hide it. The plots, the dock and the theme are remembered for the next run of the same experiment.

**The keyboard**

| Key | Does |
|---|---|
| ++space++ | Holds every plot where it is, or sets them all following the data again. |
| ++1++ to ++4++ | Opens the **Values**, **Queue**, **Instruments** or **Logs** tab. |
| ++grave++ | Hides or shows the dock. |
| ++t++ | Switches between the light and dark themes. |
| ++ctrl+k++ | Searches every task and every instrument's queries and commands, to queue one or call one from the same forms. |
| ++question++ | Lists these shortcuts. |

None of them do anything while you are typing in a box.

## Your data

Data is written to a comma separated file in a `data` folder, or the folder you chose with `data_path`. Each file has a header row of measurement names, then one row per measurement cycle:

```
time
0.030038833618164062
0.295818567276001
0.5458414554595947
```

Every measurement you add becomes another column.

Files are named `<block>.<step> <title>.data`, for example `00.00 start.data`.

- Each time you run the experiment, a new **block** is started, so nothing from a previous run is overwritten. The first run in a folder writes `00.00 start.data`, the next run `01.00 start.data`, and so on.
- Within a block, starting a new file increments the **step**: `00.01 gaussian.data`, `00.02 uniform.data`. You can start a new file from the **Data file** button in the top bar, or from a task. [Measurements and data files](measurements.md) covers this in more detail.

The log is written to `logs/debug.log` (see [`log_path` and `log_file_name`](setting_up.md#experiment-options)).

## Stopping

Close the window, or press the power button at the right of the top bar. Either asks first, and then shuts down the whole experiment cleanly, including `teardown()`. (Closing a browser tab that shows the page does not stop the experiment: only the window's own close button does.)

## Running without a window

Set `gui = False` to run without a window, for example on a computer with no display. Data is still recorded, tasks still run, and the interface can still be opened in a browser at the API server's address.

```python
class MyExperiment(Experiment):
    data_path = "my_data"
    gui = False
```

## The API

While the experiment is running it serves a local HTTP API, and the interface is simply a client of it. Everything you can do from the interface you can also do with a plain web request, from a browser, a notebook or another script.

Open [http://localhost:8000/docs](http://localhost:8000/docs) in your browser (adjust the port if you changed `api_server_port`) for an interactive page listing every endpoint, where you can try them out. For example, with the experiment above running, [http://localhost:8000/clock/time](http://localhost:8000/clock/time) returns the clock reading.

## An alternative way to start

`pyacquisition new rig.toml` opens a window in which you build or change a TOML config from forms, and run it from there. See [Setting Up in the Interface](setup_page.md).

`pyacquisition --py my_experiment.py` finds the first `Experiment` class in the file, creates it and runs it, so the file needs no `if __name__ == "__main__":` block. It only works for experiments in a single, self-contained file: modules that sit next to your script are not importable this way. Otherwise use `python my_experiment.py`.

## A standalone application

`pyacquisition build` freezes an experiment into an application that runs on a PC with no Python installed, such as the lab PC. It needs PyInstaller, which is not installed with `pyacquisition`: add it with `uv add pyacquisition[build]`.

```
uv run pyacquisition build --py my_experiment.py
```

This makes `dist/my_experiment.exe`, a single file to copy to the other PC. `--toml rig.toml` builds from a TOML file instead, and puts `config.toml` beside the executable, where you can edit it without building again. `--onedir` builds a folder instead of one file, which starts faster, `--console` keeps a console window open to show errors, `--name` names it, and `--icon` gives it an `.ico` icon.

The window needs the **Microsoft Edge WebView2 Runtime** on the PC it runs on. Windows 11 has it, and so does Windows 10 with a current Edge. On a PC without it, the window says so, with where to download it, and the experiment runs regardless: open its address in a browser meanwhile.
