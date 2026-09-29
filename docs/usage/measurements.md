# Measurements and Data Files

[Getting Started](../getting_started/config_file.md) introduces measurements and data files. This page covers the rest.

A **measurement** is a value that is read on every cycle, shown live and saved to the data file. You make one from a name and a query method of one of your instruments.

## Adding a measurement

```python
self.add_measurement(Measurement("random", rng.random_number))
```

- The first argument is the **name**. It becomes the column header in the data file and the label in the interface. Each measurement needs a different name.
- The second argument is the query itself. **Pass the method, not its result:** `rng.random_number`, without brackets. If you write `rng.random_number()`, you are passing a single number, and `pyacquisition` will raise an error.

Add measurements in `setup()`, after the instruments they use. Once the experiment is running, the set of measurements is fixed.

## Units

Give a measurement a `unit` to show it beside the value in the interface and on plot axes:

```python
self.add_measurement(Measurement("T", cryo.get_temperature, unit="K"))
```

The unit is for display only. The data file holds the same numbers, with the same column header, either way. `unit` must be text (any text: `"K"`, `"mV"`, `"Ω"`), and like `call_every` it belongs to the measurement, not to the query, so it is never passed to the query.

In a TOML file, add `unit` to the measurement: `T = {instrument = "cryo", method = "get_temperature", unit = "K"}`. Calculated columns can have units too; see [Calculations](calculations.md#units).

## Queries with arguments

If the query needs arguments, pass them to `Measurement` as keyword arguments. They are used on every call:

```python
from pyacquisition.instruments import Calculator

calculator = Calculator("calculator")
self.add_instrument(calculator)
self.add_measurement(Measurement("sum", calculator.add, x=1.0, y=2.0))
```

A keyword argument that the method does not accept is reported straight away, when the measurement is created.

### Choices, such as a channel

Where a method takes a choice (which input to read, which range to use), the choices are an `enum` that the instrument's module defines. You can give the member, or the text that names it:

```python
from pyacquisition.instruments.lakeshore.lakeshore_350 import InputChannel

Measurement("T", cryo.get_temperature, input_channel=InputChannel.INPUT_A) # (1)!
Measurement("T", cryo.get_temperature, input_channel=cryo.InputChannel.INPUT_A) # (2)!
Measurement("T", cryo.get_temperature, input_channel="INPUT_A") # (3)!
```

1. The member, imported from the instrument's module. Your editor completes the names and checks them.
2. The same member, reached from the instrument, with nothing to import. Every instrument has the enums that its queries and commands take as attributes of its class, so `Lakeshore_350.OutputChannel.OUTPUT_1` works too. Your editor completes these as well.
3. The text that names the member. Its name (`"INPUT_A"`) or the label that the interface shows (`"Input A"`) both work, in any case, and spaces and underscores do not matter, so `"input a"` is fine.

All three do the same. Text is worked out when the measurement is created, so a mistake stops the experiment at setup, and says what would have been right:

```text
ValueError: `input_channel`: 'INPUT_Z' is not one of INPUT_A, INPUT_B, INPUT_C, INPUT_D
```

The same works in a [TOML file](toml_config.md#measurements-section): `args = {input_channel = "INPUT_A"}`.

## Slow queries

All measurements are read one after another on every cycle, so one slow query slows every measurement. If a value changes slowly (a temperature, say) you can read it less often with `call_every`:

```python
Measurement("temperature", thermometer.get_temperature, call_every=10)
```

Here the thermometer is queried on every tenth cycle. On the cycles in between, the previous value is written to the file again, so every row still has a complete set of values.

## When a measurement fails

If a query raises an error (for example, an instrument times out), the error is logged, the experiment carries on, and the last good value is recorded instead. Watch the **Logs** window for these messages.

## How often is data recorded?

The target time between cycles is the `measurement_period` option (0.25 seconds by default). If reading all of the measurements takes longer than the period, cycles simply run back to back.

You can pause and resume measuring, and change the period, while the experiment runs, from **Every 0.25 s** (or whatever the period is) in the top bar of the interface, and the button beside it. It also shows how long the loops really take, and says so if measuring is slower than the period.

## Data files

Data is saved as comma separated text in the folder given by `root_path` and `data_path` ([see the options](setting_up.md#experiment-options)). Each file starts with a header row holding the name of every measurement, followed by one row per cycle:

```
time,random
10.96821117401123,0.9304400585290029
11.218265056610107,-0.9332932062270299
11.468185186386108,2.5351544166174342
```

### File names

Files are named `<block>.<step> <title>.<extension>`, for example `00.01 gaussian.data`.

| Part | Meaning |
|---|---|
| **block** | Groups the files of one run. A new block is started each time you run the experiment, so files from earlier runs are never overwritten. |
| **step** | Counts the files within a block, starting at `00`. |
| **title** | A label you choose when you start a new file. The first file is always called `start`. |

### Starting a new file

It is good practice to save each stage of an experiment (a sweep, a cooldown, one condition) to its own file. Start a new file:

- from the interface, with the file name in the top bar. Enter a title, and tick **Start a new block** if you want to start a new block instead of a new step. It shows the name the file will get.
- from a task, using the built-in `NewFile` task. See [Composing tasks](composing_tasks.md).

Data goes to the new file from the next cycle. The **Current File** window always shows where data is going.

### Reading your data

The files are plain CSV, so any tool can read them. With `pandas`, which is installed alongside `pyacquisition`:

```python
import pandas as pd

data = pd.read_csv("my_data/00.01 gaussian.data")
print(data["random"].mean(), data["random"].std())
```

Plot it with whatever you prefer, for example `matplotlib` (which you would need to install separately).

## Viewing data live

Everything that is measured (and calculated) is shown in the **Values** tab, and can be plotted: choose what to plot with the plot's chips and **+ Add**, and what goes on the horizontal axis with **against**. **+ Add plot** adds more plots, up to six. The plots show the whole of the current data file and the one before it. See [the interface](running.md#the-interface) for the rest. An experiment with [traces](traces.md) can add a trace panel or a map of one, too.
