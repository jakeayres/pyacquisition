# Experiment options

Every option of an experiment, as a class attribute of your `Experiment` subclass, with its key in a [config file](config_file.md). [Set the experiment's options](../usage/options.md) shows them in use.

```python
class Lab(Experiment):
    data_path = "cooldown_1"
    measurement_period = 0.5
    console_log_level = "INFO"
```

Set them in the class body: there is no `__init__` to write. If you write one, call `super().__init__()` first.

| Option | Meaning | Default | In a config file |
|---|---|---|---|
| `root_path` | The folder that the other paths are relative to. | `"."` | `[experiment] root_path` |
| `data_path` | The folder for the data files, inside `root_path`. | `"data"` | `[data] path` |
| `data_file_extension` | The extension of the data files, without the dot. | `"data"` | `[data] file_extension` |
| `data_delimiter` | The character between the columns of the data files. | `","` | `[data] delimiter` |
| `history_points` | The most rows kept in memory for the interface's plots, from 100 to 100,000,000, where each numeric column takes 8 bytes a row. | `500000` | `[data] history_points` |
| `trace_history_mb` | The most memory, in megabytes, that the recent traces kept for the interface's trace and map panels may take. | `64` | `[data] trace_history_mb` |
| `trace_file_mb` | The size, in megabytes, past which a data file's traces go on in a new part of its trace file. | `500` | `[data] trace_file_mb` |
| `trace_pending_mb` | The most memory, in megabytes, that traces waiting to be written may take while their file can't be written, past which the oldest are dropped. | `256` | `[data] trace_pending_mb` |
| `log_path` | The folder for the log file, inside `root_path`. | `"logs"` | `[logging] path` |
| `log_file_name` | The name of the log file. | `"debug.log"` | `[logging] file_name` |
| `console_log_level` | The least serious messages shown in the console. | `"DEBUG"` | `[logging] console_level` |
| `file_log_level` | The least serious messages written to the log file. | `"DEBUG"` | `[logging] file_level` |
| `gui_log_level` | The least serious messages shown in the interface's log. | `"DEBUG"` | `[logging] gui_level` |
| `api_server_host` | The address the API server listens on. | `"localhost"` | `[api_server] host` |
| `api_server_port` | The port the API server listens on. | `8000` | `[api_server] port` |
| `api_server_fallback_ports` | Ports to try in turn if `port` is taken by another program. | `()` | `[api_server] fallback_ports` |
| `measurement_period` | The time between measurements, in seconds. | `0.25` | `[rack] period` |
| `gui` | Whether the interface has a window of its own, as well as being at the API server's address in a browser. | `True` | `[gui] run` |
| `auto_tasks` | Whether the tasks that come with an instrument, such as `RampTemperature` for a Lakeshore, can be queued when the instrument is in the experiment. | `True` | `[experiment] auto_tasks` |

The log levels, from the most to the least verbose, are `TRACE`, `DEBUG`, `INFO`, `SUCCESS`, `WARNING`, `ERROR` and `CRITICAL`.

## Where a value comes from

An option can be set in several places. The first of these that gives it wins:

1. **An argument** to `from_config` or to the class: `Lab.from_config("rig.toml", gui=False)`, or `Lab(gui=False)`.
2. **The config file**, for an experiment made with `from_config`.
3. **A class attribute** of your experiment, or a property that works it out.
4. **The default** above.

## Mistakes

An option is checked when the experiment is made, and a wrong value stops it with a message:

```text
ValueError: `measurement_period` must be a positive number, got 'fast'
```

A class attribute whose name is close to an option's, but isn't one, is refused as soon as the class is defined, since it would do nothing:

```text
TypeError: `data_pth` in MyExperiment looks like a misspelling of the option `data_path`, so it would do nothing. Use `data_path`, or give `data_pth` a different name if it is something else.
```
