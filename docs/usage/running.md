# The Interface and the API

[Getting Started](../getting_started/config_file.md) runs a first experiment and opens its window. This page has the detail: every part of the interface, running without a window, and the local web API.

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

The window's parts, its keyboard shortcuts and the command palette are in [The interface](../reference/interface.md).

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

The log is written to `logs/debug.log` (see [`log_path` and `log_file_name`](../reference/experiment_options.md)).

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
