# Data files

Where an experiment writes, what its files are called, and what is in them. [Measurements and data files](../usage/measurements.md#reading-your-data) reads them back.

## Folders

| What | Where | Set by |
|---|---|---|
| Data files | `<root_path>/<data_path>`, by default `./data` | [`root_path`, `data_path`](experiment_options.md) |
| Trace files | Beside their data file | |
| The log | `<root_path>/<log_path>/<log_file_name>`, by default `./logs/debug.log` | [`log_path`, `log_file_name`](experiment_options.md) |
| Saved sequences | `<root_path>/sequences`, one JSON file each | |

The data and log folders are made as the experiment starts, and the sequences folder when a sequence is first saved.

## File names

`<block>.<step> <title>.<extension>`, such as `01.00 start.data` or `03.01 run 1.data`.

| Part | Meaning |
|---|---|
| **block** | Starts at `00`, and goes up by one each time the experiment runs, from the highest already in the folder, so no earlier file is written over. |
| **step** | Starts at `00` in each block, and goes up by one with each new file in it. |
| **title** | The first file of a block is `start`. A new file takes the title it is given, by the `NewFile` task or the top bar's **Data file**. |
| **extension** | [`data_file_extension`](experiment_options.md), `data` by default. |

A new file can start a new block instead of a new step: `increment_block` in `NewFile`, or **Start a new block** in the interface.

## The data file

Text, one row per measuring cycle, with the columns separated by [`data_delimiter`](experiment_options.md), a comma by default. The first line is the header, the columns' names:

```text
time,wave,power
0.16650605201721191,0.19601460359092643,0.038421724820908026
0.3735530376434326,0.43711576663514384,0.19107019344102952
```

| Columns, in order | Names |
|---|---|
| The measurements | Their names |
| The calculations | The columns they make |
| Each trace's | `<trace>_index`, the trace's number in the trace file, on the rows it was taken with, and `<trace>_<reduction>` for each reduction |

- **The columns are the first row's.** Every later row lines up with the header. A column a function returns that wasn't in the first row is left out, with a warning in the log.
- **A measurement that fails** keeps its last good value, and the error is logged. One that has never had a value is empty.
- **A calculation that fails** is empty for that row, and the error is logged.
- **A row without a trace** has that trace's columns empty.

An empty value reads as `NaN` in pandas.

## The trace file

A data file's traces are in an [HDF5](https://www.hdfgroup.org/solutions/hdf5/) file beside it, with the same name ending `.h5`: `00.01 sweep.data` has `00.01 sweep.h5`. Past [`trace_file_mb`](experiment_options.md) it goes on in parts: `00.01 sweep.001.h5`, `00.01 sweep.002.h5`.

Each trace is a group named after it, with a row per trace taken:

| Dataset | Shape | Holds |
|---|---|---|
| `trace` | (n) | Each trace's number: the `<trace>_index` of its row in the data file. |
| `point` | (m) | 0 to m − 1. |
| `time_start`, `time` | (n) | When it started, and when it was fetched, in Unix seconds. |
| `rows_start`, `rows` | (n) | How many rows the data file had then. |
| `points` | (n) | Each trace's length. Values past it are `NaN`. |
| `x_start`, `x_stop` | (n) | The axis's ends, for a linear axis... |
| `x` | (n, m) | ...or its values, for any other. |
| `<channel>` | (n, m) | The values, one dataset for each channel. |
| `row_start.<column>`, `row.<column>` | (n) | The latest row's numeric values when it started, and when it was fetched. |

The group's attributes are `name`, `x_name`, `x_unit`, `unit`, `channels` and `axis` (`linear` or `explicit`), and the file's are `pyacquisition_version`, `data_file`, `part` and `created`. `trace` and `point` are laid out as NetCDF4 dimensions, so xarray reads a trace as a dataset:

```python
import xarray as xr

spectra = xr.load_dataset("data/00.01 sweep.h5", group="spectrum", engine="h5netcdf")
```

`read_traces` reads every part in order, without xarray (see [Traces](python_api/traces.md)):

```python
from pyacquisition import read_traces

traces = read_traces("data/00.01 sweep.data", "spectrum")
```
