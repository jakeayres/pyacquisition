
"Out-of-the-box" functionality of `pyacquisition` is confiigurable via an input `.toml` file that can be read in via the `Experiment.from_config()` classmethod as shown in the [Getting Started](getting_started.md) page. Details of the `.toml` syntax can be found at [toml.io](https://toml.io/en/). Strictly, there are no required sections or keys. An empty `.toml` will run.

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
| adapter | The communication adapter to use. Currently only `pyvisa` is implemented | `pyvisa` |
| resource | The resource string associated with the instrumeent | `GPIB0::10:INSTR` |


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