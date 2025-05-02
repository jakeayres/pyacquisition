# Getting Started

Getting started is as simple as composing a `.toml` configuration file and instantiating an `Experiement` using the `Experiment.from_config()` classmethod. All of the in-build functionality of `pyacquisition` can be configured via this method. A simple configuration file that loads a software `Clock` and a Stanford Research `SR_830` lock-in amplifier on GPIB address 7 might look like:

```toml title="my_configuration_file.toml"
[experiment]
root_path = "C://data"

[data]
path = "my_data_folder"

[instruments]
clock = {instrument = "Clock"}
lockin = {instrument = "SR_830", adapter = "pyvisa", resource = "GPIB0:7:INSTR"}

[measurements]
time = {instrument = "clock", method = "timestamp_ms"}
voltage = {instrument = "lockin", method = "get_x"}
```

and the short `python` script for initializing and running your experiment might look like:

```python title="experiment_script.py"
from pyacquisition import Experiment

my_experiment = Experiment.from_config('my_configuration_file.toml')
my_experiment.run()
```

which can be run directly with python (`python experiment_script.py`) or using a dependency manager like `uv` (`uv run experiment_scripy.py`).

Voila! A user interface should be running and recording a stream of timestamped voltages as comma separated values in `C://data/my_data_folder`. All of the functionality of each instrument is available from the top menu.



