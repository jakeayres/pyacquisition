The fastest way to get started with `pyacquisition` is to create a `.toml` configuration file and instantiating your experiment with it. This will:

1. Communicate with physical instruments and give you access to all of their functionality within the generated user interface

2. Poll the instruments and record the live data to file

3. Allow you to visualize the data in real time


## Define a simple experiment

```toml title="my_configuration_file.toml" linenums="1"
[experiment]
root_path = "C://data"

[data]
path = "my_data_folder"

[instruments]
clock = {instrument = "Clock"}
lockin = {instrument = "SR_830", adapter = "pyvisa", resource = "GPIB0::7::INSTR"}

[measurements]
time = {instrument = "clock", method = "timestamp_ms"}
voltage = {instrument = "lockin", method = "get_x"}
```

## Run the experiment

Run the experiment from the command line:

`pyacquisition --toml "my_configuration_file.toml"`