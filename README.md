# PyAcquisition

<figure markdown="span">
  ![PyAcquisition](logo.png){ width="500" }
</figure>

`pyacquisition` is a powerful Python package designed to simplify the process of recording scientific data and controlling laboratory instruments. It abstracts away the complexities of instrument communication, task scheduling (both concurrent and sequential), data recording, and logging, allowing you to focus on the science. Whether you're managing a single instrument or orchestrating a complex experimental workflow, `pyacquisition` provides a framework that simplifies the process dramatically.

Check out the [installation](basic/installation.md) and [getting started](basic/getting_started.md) pages to get going.

## Objectives

**Be an 'all-python' solution** for interfacing with instruments and automating experimental procedures. Python has become the first choice of many for data analysis and scripting. We don't want to have to learn a second language just for interfacing with hardware or generating a GUI. You need *only* use python (and possibly a `.toml` config file).

**Be up and running in minutes**, not hours. `pyacquisition` is designed to be simple and 'batteries-included'. We want to absolutely minimize your development time in all major use-cases.

**Be 'one-size-fits-most'**. There will inevitably be cases that are not well suited to the workflow offered by `pyacquisition`, but it is hoped that we can help in the majority of instances. We've tried to design for maximum flexibility whilst keeping the API reasonably simple.

**Forget the GUI**. User interfaces are difficult and time consuming. Writing a robust GUI in Qt may well take longer than writing the rest of your experiment and analysis code combined. `pyacquisition` generates the entire UI programmatically. 

**Offer minimal barrier to entry** for those who are not advanced python users. Whilst it will be helpful to understand the basics of object oriented and asynchronous programming, getting going with `pyacquisition` is as simple as composing a `.toml` configuration file and running a two-line script. Adding custom functionality can mostly be accomplished by following some worked examples in most cases.

## A Short Example

A short configuration file interfacing with a Stanford Research Instruments SR 830 lock-in amplifier:

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

A short script running the experiment from the configuration file:

```python title="experiment_script.py"
from pyacquisition import Experiment

my_experiment = Experiment.from_config('my_configuration_file.toml')
my_experiment.run()
```

