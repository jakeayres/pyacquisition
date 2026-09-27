
"Out-of-the-box" functionality of `pyacquisition` is configurable via an input `.toml` file that can be read in via the `Experiment.from_config()` classmethod, or from the command line with `pyacquisition --toml my_configuration_file.toml`. Details of the `.toml` syntax can be found at [toml.io](https://toml.io/en/). Strictly, there are no required sections or keys. An empty `.toml` will run (albeit with no instruments and no measurements). Reasonable defaults are provided.

To build or change a file from forms instead of writing it, use `pyacquisition new` (see [Setting Up in the Interface](setup_page.md)), which keeps the file's comments.

Below is a breakdown of all of the sections and keys available for configuration:

## `[experiment]` Section

General parameters for the experiment.

| Parameter Name | Description                          | Default Value |
|----------------|--------------------------------------|---------------|
| `root_path` | The folder that the other paths are relative to. | `.`           |
| `auto_tasks` | Whether the tasks that come with an instrument, such as `RampTemperature` for a Lakeshore, can be queued when the instrument is in the experiment. | `true`        |


## `[rack]` Section

Configuration of the `rack` object which manages the polling of instruments.

| Parameter Name | Description                          | Default Value |
|----------------|--------------------------------------|---------------|
| `period` | The time between measurements, in seconds. | `0.25`        |


## `[instruments]` Section

The software and hardware instruments to connect to. Each instrument is configured in a single key-value entry. The key is the unqiue name ascribed to the instrument. The value is a dictionary-like entry configuring the instrument. 

**For software instruments** only the instrument class name (eg `Clock`) needs to be provided. For example, to configure a software clock, the following `.toml` can be used:

```toml
[instruments]
my_clock = {instrument = "Clock"}
```

| Parameter Name | Description                          | Example Value  |
|----------------|--------------------------------------|---------------|
| instrument       | The name of the instrument class to be instantiated.       | `Clock` |

**For hardware instruments** an additional adapter and resource string need to be provided. For example, to configure a Stanford Research SR830 lock-in amplifier connected using pyvisa on GPIB address 7, one could use:

```toml
[instruments]
my_lockin = {instrument = "SR_830", adapter = "pyvisa", resource = "GPIB0::7::INSTR"}
```

| Parameter Name | Description                          | Example Value  |
|----------------|--------------------------------------|---------------|
| instrument       | The name of the instrument class to be instantiated.       | `SR_830`, `Lakeshore_350` |
| adapter | The communication adapter to use: `pyvisa` for hardware, `prologix` for hardware behind a Prologix GPIB-USB controller, or `mock` to run the instrument without the device | `pyvisa`, `prologix`, `mock` |
| resource | The resource string associated with the instrumeent | `GPIB0::10:INSTR` |

An instrument that cannot be opened, for example because its address is wrong, is skipped with a warning in the log, and the rest of the experiment still starts. In Python, [the instrument raises an error instead](instruments.md#adding-hardware-instruments).


### Instruments behind a Prologix GPIB-USB controller

A [Prologix GPIB-USB controller](https://prologix.biz) shows up as a virtual COM port. Set `adapter = "prologix"` and give the serial port and the instrument's GPIB address as the resource, separated by `::`:

```toml
[instruments]
lockin = {instrument = "SR_830", adapter = "prologix", resource = "COM3::7"}
current = {instrument = "Keithley_6221", adapter = "prologix", resource = "COM3::12", args = {read_termination = "\n"}}
```

Instruments then work as they would over GPIB with `pyvisa`, and take the same `args` (`timeout`, `read_termination`, `write_termination`, ...). On Linux the port looks like `/dev/ttyUSB0::12`. A secondary address goes last, as in `COM3::9::0`.

- **Several instruments, one controller.** Give each its own address on the same port. The port is opened once and shared, and instruments used from different threads do not interfere.
- **Replies.** As with GPIB, a reply ends on EOI. If an instrument does not assert EOI, set `read_termination` to what it sends at the end of a message, for example `"\n"`.
- **Long waits.** The controller waits at most 3 seconds for a reply. A longer `timeout` still works, by asking again until it runs out.
- **The controller's settings** are managed for you. The adapter turns off the saving of settings to the controller's EEPROM, so switching between instruments does not wear it out.

### Running hardware instruments without the device

Set `adapter = "mock"` to run a hardware instrument class with no device connected, for example to develop a task or to test a config away from the lab. Any `resource` string is accepted.

```toml
[instruments]
current = {instrument = "Keithley_6221", adapter = "mock", resource = "GPIB0::12::INSTR"}
```

The mock has no model of the instrument. It answers each query from the first rule that applies:

1. A reply you configured with `responses`.
2. The value last written: after `set_current(1e-3)`, `get_current()` returns `1e-3`, so every setter and getter pair round-trips.
3. `"0"`, so a getter that was never set still returns a number.

Queries that read something the instrument would measure, such as a temperature, therefore return `0` unless you give them a reply. Do this with `args`:

```toml
[instruments]
temperature = {instrument = "Lakeshore_350", adapter = "mock", resource = "mock", args = {responses = {"KRDG? A" = ["4.20", "4.21", "4.19"]}}}
```

A list of replies is returned in turn, holding on the last one. A key is either a whole query (`"KRDG? A"`) or just its header (`"KRDG?"`), and the whole query wins.

## `[measurements]` Section

Define the instrument methods to poll. The key is a unique label assigned to the measurement (e.g. 'time', 'voltage', 'temperature'). The value is a dictionary encoding the instrument associated with the measurement, the method to be polled and any arguments that the method should be called with. The value assigned to `instrument` **must** be present as a key in the `[instruments]` section. The value assigned to `method` **must** be the name of a method of the instrument. Refer to the relevant instrument documentation for a list of available methods and their arguments.

| Parameter Name | Description                          | Example Value    |
|----------------|--------------------------------------|------------------|
| `instrument`   | The name of the instrument           | `my_clock`       |
| `method`       | The method to poll                   | `timestamp_ms`   |
| `args`         | (optional) Arguments to call `method` with.      |                  |
| `unit`         | (optional) The unit, shown beside the value in the interface. Display only. | `"K"` |

!!! Note
    If a method takes an argument that is a member of an `Enum`, give the text that names it, and it is resolved against the enum's members. Use the member's name (`"FLOAT"`) or its label (`"Float"`), in any case. For example, `args = {grounding = "FLOAT"}` for the method below. A value that names no member is refused, and the message lists the valid ones.


    ```python
    class InputGrounding(Enum):
	    FLOAT = 0
	    GROUND = 1

    ...

    def instrument_method(grounding: InputGrounding):
        ...

    ```


## `[calculations]` Section

Make new columns from the measurements, as [calculations](calculations.md) do in Python, with the built-in `Sum` and `RollingMean`. Each is a table under `[calculations]`, and its key is the name of the new column. `calculation` names which one it is:

| Calculation | Keys | Makes |
|---|---|---|
| `Sum` | `inputs`: a list of one or more columns | The sum of the columns. |
| `RollingMean` | `column`: a column. `window`: a whole number, at least 1 | The mean of the last `window` values of the column. It is `NaN` until that many have been seen. |

Either can have a `unit`, which is shown in the interface, as a measurement's is. For example:

```toml
[calculations.total]
calculation = "Sum"
inputs = ["x", "y"]
unit = "V"

[calculations.x_smooth]
calculation = "RollingMean"
column = "x"
window = 10
```

They run in the order they are written, after the measurements, and are saved to the data file after them. Each can use the measurements and the calculations above it. A calculation that names a column that doesn't exist yet, an unknown `calculation` or key, or a value of the wrong kind is refused when the file is loaded. A calculation whose measurement is left out, because its instrument couldn't be opened, is left out too, with a warning.

For anything other than these two, such as `x / 1e-6`, write the calculation in Python and [combine the file with Python](#combining-a-config-file-with-python).


## `[data]` Section

The `[data]` section describes the configuration of the data files.

| Parameter Name | Description                          | Default Value |
|----------------|--------------------------------------|---------------|
| `path` | The folder for the data files, inside `root_path`. | `data`        |
| `file_extension` | The extension of the data files, without the dot. | `data` |
| `delimiter` | The character between the columns of the data files. | `,` |
| `history_points` | The most rows kept in memory for the interface's plots, from 100 to 100,000,000, where each numeric column takes 8 bytes a row. | `500000` |


## `[api_server]` Section

The `[api_server]` section defines the properties of the FastAPI backend that serves the interface, and the API that it and your scripts use. This may be changed to avoid (for example) port conflicts with other services that are running.

| Parameter Name         | Description                          | Default Value          |
|------------------------|--------------------------------------|------------------------|
| `host` | The address the API server listens on. | `localhost`            |
| `port` | The port the API server listens on. | `8000`                 |
| `fallback_ports` | Ports to try in turn if `port` is taken by another program. | `[]` (none) |

With fallback ports, an experiment that finds its port taken, for example by another experiment already running, moves to the first free one instead of failing to start. The port it ends up on is logged, and the GUI connects to it by itself:

```toml
[api_server]
port = 8000
fallback_ports = [8001, 8002, 8003]
```

If every one of them is taken, the experiment stops before setting anything up, with an error that lists each port and why it couldn't be used.


## `[logging]` Section

This section defines the various logging levels and location of log files produced during program execution. Allowed levels are `TRACE`, `DEBUG`, `INFO`, `SUCCESS`, `WARNING`, `ERROR` and `CRITICAL`.

| Parameter Name  | Description                          | Default Value |
|-----------------|--------------------------------------|---------------|
| `path` | The folder for the log file, inside `root_path`. | `logs` |
| `console_level` | The least serious messages shown in the console. | `DEBUG`       |
| `gui_level` | The least serious messages shown in the interface's log. | `DEBUG`       |
| `file_level` | The least serious messages written to the log file. | `DEBUG`       |
| `file_name` | The name of the log file. | `debug.log`   |


## `[gui]` Section

| Parameter Name | Description                          | Default Value |
|----------------|--------------------------------------|---------------|
| `run` | Whether the interface has a window of its own, as well as being at the API server's address in a browser. | `true` |


## Mistakes in the file

The `[experiment]`, `[rack]`, `[data]`, `[api_server]`, `[logging]` and `[gui]` sections are checked, and so is `[calculations]` (see above). A key that is not in the tables above is refused, with a suggestion when it is close to one, and so is a value of the wrong kind, such as `period = "fast"`. A misspelt key would otherwise be ignored and the default used, silently.

```text
ValueError: Unknown key 'pth' in [data] (did you mean 'path'?). Valid keys: path, file_extension, delimiter.
```


## Combining a config file with Python

Call `from_config` on your own experiment class to combine the two. The class holds the parts that are easier to write in Python (tasks, calculations, options that do not change), and the file describes the rig. It is an ordinary `Experiment` subclass, so its [options](setting_up.md#experiment-options) are class attributes:

```python
class MyExperiment(Experiment):
    data_path = "my_data"
    measurement_period = 0.5

    def setup(self):
        self.register_task(TemperatureSweep, label="Temperature Sweep")


MyExperiment.from_config("rig.toml").run()
```

An option can come from several places. The first of these that gives one wins:

1. **An argument to `from_config`** (or to the class), for example `from_config("rig.toml", gui=False)`.
2. **The config file.**
3. **A class attribute** of your experiment.
4. **The built-in default.**

So if `rig.toml` sets `[rack] period = 1.0` and the class says `measurement_period = 0.5`, the experiment measures every second, and an option the file does not mention keeps the class's value.