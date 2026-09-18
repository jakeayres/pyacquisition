# Setting Up an Experiment

An experiment is a class that inherits from `Experiment`. You override `setup()` to describe what is in your experiment: which instruments, which measurements and which tasks.

Create a new file called `my_experiment.py`:

```python title="my_experiment.py" linenums="1"
from pyacquisition import Experiment, Measurement
from pyacquisition.instruments import Clock


class MyExperiment(Experiment):

    def __init__(self):
        super().__init__(data_path="my_data") # (1)!

    def setup(self): # (2)!
        clock = Clock("clock") # (3)!
        self.add_instrument(clock)

        self.add_measurement(Measurement("time", clock.time)) # (4)!


if __name__ == "__main__": # (5)!
    MyExperiment().run()
```

1. Options such as where to save data are passed to `Experiment.__init__()`. They are listed [below](#experiment-options). Here, data files will go in a folder called `my_data`.
2. `setup()` is called once, just before the experiment starts running. This is where you add instruments, measurements and tasks.
3. A `Clock` is a built-in software instrument that reports elapsed time. The text `"clock"` is the instrument's **id**, which must be different for every instrument. The next pages explain [instruments](instruments.md) and [measurements](measurements.md) properly.
4. This records the clock's `time` query, under the column name `time`, on every cycle.
5. This line is required. [Running an experiment](running.md#always-use-a-main-guard) explains why.

That is already a complete, working experiment. The [next page](running.md) runs it.

## `setup()` and `teardown()`

`Experiment` provides two hooks that you can override:

| Method | Called | Use it to |
|---|---|---|
| `setup()` | Once, just before the experiment starts running | Add instruments, measurements and tasks |
| `teardown()` | Once, after the experiment has ended | Clean up, for example put an instrument into a safe state |

!!! warning "Instruments and measurements must be added before the experiment runs"
    Add them in `setup()` (or in `__init__()`, after the call to `super().__init__()`). Calling `add_instrument()` or `add_measurement()` once the experiment is running raises a `RuntimeError`. The interface builds its menus, and registers each instrument's functions, when the experiment starts, so it could not otherwise know about them.

## Experiment options

Every option has a default, so you only need to pass the ones you want to change.

| Option | Default | Meaning |
|---|---|---|
| `root_path` | `"."` | The base folder for the data and log folders below. |
| `data_path` | `"."` | Folder for data files, inside `root_path`. |
| `data_file_extension` | `"data"` | File extension for data files. |
| `data_delimiter` | `","` | Column separator in data files. |
| `measurement_period` | `0.25` | Target time between measurement cycles, in seconds. |
| `log_path` | `"."` | Folder for the log file, inside `root_path`. |
| `log_file_name` | `"debug.log"` | Name of the log file. |
| `console_log_level` | `"DEBUG"` | How much is printed in the terminal. `"DEBUG"` is very verbose. `"INFO"` is quieter. |
| `file_log_level` | `"DEBUG"` | How much is written to the log file. |
| `gui_log_level` | `"DEBUG"` | How much is shown in the interface's log window. |
| `api_server_host` | `"localhost"` | Address of the local API server. |
| `api_server_port` | `8000` | Port of the local API server. Use a different port for each experiment running at the same time. |
| `gui` | `True` | Set to `False` to run without the graphical interface. |

For example, to save data to `C:/data/cooldown_1`, keep the terminal quiet, and record every half second:

```python
super().__init__(
    root_path="C:/data",
    data_path="cooldown_1",
    console_log_level="INFO",
    measurement_period=0.5,
)
```
