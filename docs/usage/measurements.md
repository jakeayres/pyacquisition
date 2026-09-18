# Measurements and Data Files

A **measurement** is a value that is read on every cycle, shown live and saved to the data file. You make one from a name and a query method of one of your instruments.

## Adding a measurement

```python
self.add_measurement(Measurement("random", rng.random_number))
```

- The first argument is the **name**. It becomes the column header in the data file and the label in the interface. Each measurement needs a different name.
- The second argument is the query itself. **Pass the method, not its result:** `rng.random_number`, without brackets. If you write `rng.random_number()`, you are passing a single number, and `pyacquisition` will raise an error.

Add measurements in `setup()`, after the instruments they use. Once the experiment is running, the set of measurements is fixed.

## Queries with arguments

If the query needs arguments, pass them to `Measurement` as keyword arguments. They are used on every call:

```python
from pyacquisition.instruments import Calculator

calculator = Calculator("calculator")
self.add_instrument(calculator)
self.add_measurement(Measurement("sum", calculator.add, x=1.0, y=2.0))
```

A keyword argument that the method does not accept is reported straight away, when the measurement is created.

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

You can pause and resume measuring, and change the period, while the experiment runs, using the **Rack** menu.

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

- from the interface, with **Scribe → Next File Endpoint**. Enter a `title`, and tick `next_block` if you want to start a new block instead of a new step.
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

Everything that is measured is shown in the **Live Data** window. For a graph, choose **Plots → New Plot**. Use the plot's **x-axis** menu to choose what goes on the horizontal axis, and **Clear** to empty it. You can open as many plots as you like.
