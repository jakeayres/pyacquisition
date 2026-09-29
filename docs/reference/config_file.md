# Config file

Every table and key a TOML config file can hold. [1. The Config File](../getting_started/config_file.md) builds one step by step, and [`pyacquisition new`](../usage/setup_page.md) writes one from forms.

A file is run with `pyacquisition run --toml rig.toml`, or read in Python with `Experiment.from_config("rig.toml")`. Every table is optional, and an empty file is a valid experiment. The file is [TOML](https://toml.io/en/).

```toml
[instruments]
clock = { instrument = "Clock" }

[instruments.lockin]
instrument = "SR_830"
adapter = "pyvisa"
resource = "GPIB0::8::INSTR"

[measurements]
time = { instrument = "clock", method = "time" }
x = { instrument = "lockin", method = "get_x", unit = "V" }

[rack]
period = 0.5
```

## `[experiment]`

| Key | Meaning | Default | Kind |
|---|---|---|---|
| `root_path` | The folder that the other paths are relative to. | `"."` | text (a folder) |
| `auto_tasks` | Whether the tasks that come with an instrument, such as `RampTemperature` for a Lakeshore, can be queued when the instrument is in the experiment. | `true` | true or false |

## `[rack]`

| Key | Meaning | Default | Kind |
|---|---|---|---|
| `period` | The time between measurements, in seconds. | `0.25` | number (seconds) |

## `[instruments]`

One entry for each instrument. The entry's name is the instrument's name, which the rest of the file and the interface use. A long entry can be a table of its own, `[instruments.lockin]`.

Each instrument needs a name of its own: a second with the same name replaces the first. A name can't be one that the experiment's own addresses start with, which are `docs`, `experiment`, `history`, `logs`, `managers`, `rack`, `scribe`, `sequences`, `stream`, `task_manager`, `tasks`, `traces` and `ui`, since the instrument's queries are served under its name (`/lockin/get_x`).

| Key | Meaning | Example |
|---|---|---|
| `instrument` | The driver: a name from the [instruments](instruments/overview.md). Required. | `"SR_830"` |
| `adapter` | How the computer reaches a hardware instrument: `pyvisa`, `prologix`, `mock` or `record`. See [Adapters](adapters.md). Hardware instruments only. | `"pyvisa"` |
| `resource` | The instrument's address, in the adapter's form. Hardware instruments only. | `"GPIB0::8::INSTR"` |
| `args` | Options for the connection, such as `timeout`, `read_termination` and `responses`. See [Adapters](adapters.md). Hardware instruments only. | `{ timeout = 10000 }` |

A software instrument, such as `Clock`, takes `instrument` alone. An instrument that can't be opened, at a wrong address say, is left out with a warning in the log, and the rest of the experiment still starts.

## `[measurements]`

One entry for each measurement. The entry's name is the measurement's, and its column's in the data file.

| Key | Meaning | Example |
|---|---|---|
| `instrument` | The name of an instrument in `[instruments]`. Required. | `"lockin"` |
| `method` | One of that instrument's queries. Required. | `"get_x"` |
| `args` | The query's arguments, by name. | `{ frequency = 0.2 }` |
| `unit` | The unit, shown in the interface. It doesn't change the data file. | `"V"` |

An argument that is a choice is given as text: the member's name or its label, in any case, such as `input_channel = "INPUT_A"`. A value that names no member is refused, with the valid ones listed.

## `[calculations]`

One table for each calculation, `[calculations.<name>]`, where `<name>` is the new column's. They run in the order they are written, after the measurements, and each can use the columns above it.

| Key | Meaning | Example |
|---|---|---|
| `calculation` | Which one: `Sum` or `RollingMean`. Required. | `"RollingMean"` |
| `inputs` | `Sum` only: the columns to add together. | `["v1", "v2"]` |
| `column` | `RollingMean` only: the column to average. | `"x"` |
| `window` | `RollingMean` only: how many values to average, at least 1. | `10` |
| `unit` | The new column's unit, shown in the interface. | `"V"` |

See [Calculations](calculations.md) for what each makes.

## `[traces]`

One table for each trace, `[traces.<name>]`, where `<name>` is the trace's.

| Key | Meaning | Example |
|---|---|---|
| `instrument` | The name of an instrument in `[instruments]`. Required. | `"analyser"` |
| `method` | One of that instrument's trace methods. Required. | `"get_spectrum"` |
| `every` | Take one every so many seconds, on its own clock. | `10` |
| `every_rows` | Take one with every so many rows, which wait for it. | `1` |
| `reduce` | Reductions, each a column on the trace's row: `mean`, `min`, `max`, `sum`, `std`, `peak_x` or `integral`. | `["mean", "peak_x"]` |
| `reduce_units` | A reduction's unit, where it isn't the trace's. | `{ mean = "dB" }` |
| `channels` | The channels, where the instrument doesn't say. | `["X", "Y"]` |
| `timeout` | The most seconds a trace may take. | `300` |
| `unit` | The channels' unit, where the instrument's isn't the one to show. | `"dBm"` |
| `x_unit` | The axis's unit, likewise. | `"Hz"` |
| `args` | The trace method's arguments, by name. | `{ span = 1e6 }` |

Give `every` or `every_rows`, not both. With neither, a trace is taken only when asked, by the `AcquireTrace` task or **Acquire now**.

## `[data]`

| Key | Meaning | Default | Kind |
|---|---|---|---|
| `path` | The folder for the data files, inside `root_path`. | `"data"` | text (a folder) |
| `file_extension` | The extension of the data files, without the dot. | `"data"` | text |
| `delimiter` | The character between the columns of the data files. | `","` | text |
| `history_points` | The most rows kept in memory for the interface's plots, from 100 to 100,000,000, where each numeric column takes 8 bytes a row. | `500000` | whole number |
| `trace_history_mb` | The most memory, in megabytes, that the recent traces kept for the interface's trace and map panels may take. | `64` | number (MB) |
| `trace_file_mb` | The size, in megabytes, past which a data file's traces go on in a new part of its trace file. | `500` | number (MB) |
| `trace_pending_mb` | The most memory, in megabytes, that traces waiting to be written may take while their file can't be written, past which the oldest are dropped. | `256` | number (MB) |

## `[api_server]`

| Key | Meaning | Default | Kind |
|---|---|---|---|
| `host` | The address the API server listens on. | `"localhost"` | text |
| `port` | The port the API server listens on. | `8000` | whole number |
| `fallback_ports` | Ports to try in turn if `port` is taken by another program. | `[]` | list of whole numbers |

With `fallback_ports`, an experiment whose port is taken moves to the first free one, logs which, and the interface follows it. If every one is taken, the experiment stops before setting anything up, with an error that lists each port and why it couldn't be used.

## `[logging]`

| Key | Meaning | Default | Kind |
|---|---|---|---|
| `path` | The folder for the log file, inside `root_path`. | `"logs"` | text (a folder) |
| `file_name` | The name of the log file. | `"debug.log"` | text |
| `console_level` | The least serious messages shown in the console. | `"DEBUG"` | log level |
| `file_level` | The least serious messages written to the log file. | `"DEBUG"` | log level |
| `gui_level` | The least serious messages shown in the interface's log. | `"DEBUG"` | log level |

The log levels, from the most to the least verbose, are `TRACE`, `DEBUG`, `INFO`, `SUCCESS`, `WARNING`, `ERROR` and `CRITICAL`.

## `[gui]`

| Key | Meaning | Default | Kind |
|---|---|---|---|
| `run` | Whether the interface has a window of its own, as well as being at the API server's address in a browser. | `true` | true or false |

## Mistakes in the file

The whole file is checked before anything starts: every table, instrument, measurement, calculation and trace. A key that isn't in the tables above is refused, with a suggestion when it is close to one, and so is a value of the wrong kind, such as `period = "fast"`, a driver that doesn't exist, or a method an instrument doesn't have. Every mistake is listed at once:

```text
pyacquisition run: my_experiment.toml has 2 problems:
  - Unknown key 'pth' in [data] (did you mean 'path'?). Valid keys: path, file_extension, delimiter, history_points, trace_history_mb, trace_file_mb, trace_pending_mb.
  - Instrument 'lockin': there is no driver called 'SR830' (did you mean 'SR_830'?).
```

In Python, `from_config` raises the same list, as a `ConfigError`, which is a kind of `ValueError`. An instrument that is described correctly but can't be opened is not a mistake in the file, and is left out with a warning.

An option set in the file and in Python takes the value in [the order of precedence](experiment_options.md#where-a-value-comes-from).
