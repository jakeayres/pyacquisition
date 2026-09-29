# Experiment Options

This page lists the options of an `Experiment`, and the two hooks, `setup()` and `teardown()`, that you can override. [Getting Started](../getting_started/python_api.md#experiment-setup) uses `setup()` to put an instrument into a known state, and `teardown()` to leave it safe, as part of a complete first experiment.

## `setup()` and `teardown()`

`Experiment` provides two hooks that you can override:

| Method | Called | Use it to |
|---|---|---|
| `setup()` | Once, just before the experiment starts running | Put instruments into a known state, and add instruments, measurements, calculations and tasks |
| `teardown()` | Once, after the experiment has ended | Clean up, for example put an instrument into a safe state |

!!! warning "Instruments and measurements must be added before the experiment runs"
    Add them in `setup()`. Calling `add_instrument()` or `add_measurement()` once the experiment is running raises a `RuntimeError`. The interface builds its menus, and registers each instrument's functions, when the experiment starts, so it could not otherwise know about them.

## Experiment options

Set an option by naming it in the body of your experiment class. Every option has a default, so you only need to set the ones you want to change.

```python
class MyExperiment(Experiment):
    root_path = "C:/data"
    data_path = "cooldown_1"
    console_log_level = "INFO"
    measurement_period = 0.5

    def setup(self):
        ...
```

This saves data to `C:/data/cooldown_1`, keeps the terminal quiet, and records every half second. There is no `__init__` to write, so there is nothing in it to get wrong.

| Option | Default | Meaning |
|---|---|---|
| `root_path` | `"."` | The base folder for the data and log folders below. |
| `data_path` | `"data"` | Folder for data files, inside `root_path`. |
| `data_file_extension` | `"data"` | File extension for data files. |
| `data_delimiter` | `","` | Column separator in data files. |
| `measurement_period` | `0.25` | Target time between measurement cycles, in seconds. |
| `log_path` | `"logs"` | Folder for the log file, inside `root_path`. |
| `log_file_name` | `"debug.log"` | Name of the log file. |
| `console_log_level` | `"DEBUG"` | How much is printed in the terminal. `"DEBUG"` is very verbose. `"INFO"` is quieter. |
| `file_log_level` | `"DEBUG"` | How much is written to the log file. |
| `gui_log_level` | `"DEBUG"` | How much is shown in the interface's log window. |
| `api_server_host` | `"localhost"` | Address of the local API server. |
| `api_server_port` | `8000` | Port of the local API server. Use a different port for each experiment running at the same time. |
| `api_server_fallback_ports` | `()` | Ports to try in turn if `api_server_port` is taken by another program, such as `[8001, 8002, 8003]`. The experiment moves to the first free one, logs which, and the interface follows it. |
| `gui` | `True` | Set to `False` to run without the interface's window. It can still be opened in a browser at the API server's address. |
| `auto_tasks` | `True` | Register the tasks that come with an instrument, such as `RampTemperature` for a Lakeshore, when the instrument is in the experiment. Set to `False` to register the ones you want yourself. See [tasks that are already included](tasks.md#tasks-that-are-already-included). |

The log levels are `TRACE`, `DEBUG`, `INFO`, `SUCCESS`, `WARNING`, `ERROR` and `CRITICAL`.

### Mistakes are caught

The options are checked when the experiment is created, so a mistake stops it at once with a message, rather than misbehaving later:

```text
ValueError: `measurement_period` must be a positive number, got 'fast'
```

A misspelt option would otherwise be ignored without a word, and your data would go to the wrong folder. So a name in your class that is close to an option, but is not one, is refused as soon as the class is defined:

```text
TypeError: `data_pth` in MyExperiment looks like a misspelling of the option `data_path`, so it would do nothing.
```

Other names are fine. You can keep your own constants and helper methods in the class, such as `sample_name = "S1"`, as long as they are not close to an option.

### Computing an option

An option can be a property, when its value has to be worked out:

```python
from datetime import date


class MyExperiment(Experiment):

    @property
    def data_path(self):
        return f"data_{date.today():%Y-%m-%d}"
```

### Passing options as arguments

Options can also be given as arguments when the experiment is created, and an argument wins over the class attribute. This is handy for running the same experiment two ways:

```python
MyExperiment(gui=False).run()
```

If you also describe the rig in a [TOML file](toml_config.md), the file wins over the class attribute, and an argument wins over both. See [the order of precedence](toml_config.md#combining-a-config-file-with-python).

!!! tip "You do not need an `__init__`"
    Setting the options in the class body means you never have to write `__init__` or call `super().__init__()`. If you do write one, call `super().__init__()` first, and put the rest of your set-up in `setup()`, where it belongs.
