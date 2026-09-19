
"Out-of-the-box" functionality of `pyacquisition` is configurable via an input `.toml` file that can be read in via the `Experiment.from_config()` classmethod, or from the command line with `pyacquisition --toml my_configuration_file.toml`. Details of the `.toml` syntax can be found at [toml.io](https://toml.io/en/). Strictly, there are no required sections or keys. An empty `.toml` will run (albeit with no instruments and no measurements). Reasonable defaults are provided.

Below is a breakdown of all of the sections and keys available for configuration:

## `[experiment]` Section

General parameters for the experiment.

| Parameter Name | Description                          | Default Value |
|----------------|--------------------------------------|---------------|
| `root_path`    | Root directory for the experiment. All other paths are relative to this directory.   | `.`           |


## `[rack]` Section

Configuration of the `rack` object which manages the polling of instruments.

| Parameter Name | Description                          | Default Value |
|----------------|--------------------------------------|---------------|
| `period`       | Time period for rack operations. How frequently measurement functions are polled in seconds.    | `0.25`        |


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

!!! Note
    If a method takes arguments that are members of an `Enum`, you can pass a string that will be resolved against the enum members. For example, one could use pass `method = "instrument_method"` and `grouding = "FLOAT"` if 


    ```python
    class InputGrounding(Enum):
	    FLOAT = 0
	    GROUND = 1

    ...

    def instrument_method(grounding: InputGrounding):
        ...

    ```


## `[data]` Section

The `[data]` section describes the configuration of the data files.

| Parameter Name | Description                          | Default Value |
|----------------|--------------------------------------|---------------|
| `path`         | Directory for storing data (relative to the experiment `root_path`).          | `.`           |
| `extension`    | The file extension to use for data files | `.data` |
| `delimiter`    | Delimiter to use for data files | `,` |


## `[api_server]` Section

The `[api_server]` section defines the properties of the FastAPI backend that exposes functionality to the GUI that runs in a seperate process. This may be changed to avoid (for example) port conflicts with other services that are running.

| Parameter Name         | Description                          | Default Value          |
|------------------------|--------------------------------------|------------------------|
| `host`                 | Hostname for the API server.         | `localhost`            |
| `port`                 | Port for the API server.             | `8005`                 |


## `[logging]` Section

This section defines the various logging levels and location of log files produced during program execution. Allowed values are `DEBUG`, `INFO`, `WARNING`, `ERROR`.

| Parameter Name  | Description                          | Default Value |
|-----------------|--------------------------------------|---------------|
| `console_level` | Logging level for console output.    | `INFO`       |
| `gui_level`     | Logging level for output in the GUI.    | `INFO`       |
| `file_level`    | Logging level for file output.       | `DEBUG`       |
| `file_name`     | Name of the log file.                | `debug.log`   |