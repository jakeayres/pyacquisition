# Usage

Each page here is a short tutorial for one thing you may want to do after [Getting Started](../getting_started/installation.md), in the same format: a file built up a step at a time, beside the terminal. Read them in any order, when you need them. For every option, driver or task, see [Reference](../reference/index.md).

## Instruments

| Page | Covers |
|---|---|
| [Connect a real instrument](connect_instrument.md) | Your lock-in on GPIB, USB or serial instead of `mock`: its address, the adapter, and a second instrument from Python. About 10 minutes. |
| [Write a software instrument](software_instrument.md) | A disk-space monitor: a query, a command, and a choice, in the Instruments tab and the data file. About 15 minutes. |
| [Write a hardware instrument](hardware_instrument.md) | A driver for a Keithley 2400 SourceMeter: messages sent, replies taken apart, and the device's codes as a choice, tried on `mock`. About 20 minutes. |
| [Verify a driver on real hardware](verify_driver.md) | Getting Started's lock-in checked against its driver, read-only and then setting by setting, with a report to keep, and your own driver checked from Python. About 20 minutes. |

## Data

| Page | Covers |
|---|---|
| [Tune your measurements](measurements.md) | A sample in a cryostat: units, a choice as an argument, a slow value read less often, and what a failed reading leaves in the file. About 10 minutes. |
| [Read your data](read_data.md) | Your data files in pandas: find them, read one, plot it, read every file of a run, and let the interface write the script. About 10 minutes. |
| [Calculate new columns](calculations.md) | Columns worked out as you record: a noisy signal smoothed, its size, and how fast the sample is cooling. About 15 minutes. |
| [Record spectra and traces](traces.md) | A spectrum taken when you ask and with every row, reduced to a column, mapped against temperature, and read back. About 15 minutes. |

## Tasks

| Page | Covers |
|---|---|
| [Write a task](write_task.md) | `SetTemperature`: go to a temperature and wait until it's there, with progress, a check of what was asked, and the cryostat held when paused. About 20 minutes. |
| [Sweep a temperature](sweep.md) | A sweep made of tasks, with a file for each temperature, a safety interlock alongside, and a temperature it can't reach skipped. About 20 minutes. |
| [Queue, pause and save tasks](queue.md) | A night's work queued, paused, rearranged, and saved as a sequence to run again. About 15 minutes. |
| [Hold a temperature with PID](pid.md) | A sample held at a temperature by the `PID` task, through its thermometer's resistance on an SR830 and a Lakeshore's heater in open loop, on a queue of its own, and tuned from the interface while it runs. About 20 minutes. |

## The experiment

| Page | Covers |
|---|---|
| [Set the experiment's options](options.md) | A data folder for each sample and day, a quieter terminal, a port of its own, and which wins, the class or the file. About 10 minutes. |
| [Build a config in the interface](setup_page.md) | A rig's config file written from forms with `pyacquisition new`, checked as you go, and run from the same window. About 10 minutes. |
| [Drive an experiment from a script](api_script.md) | The lab run with no window, and driven by a script over the web API: a value read, a command sent, two files recorded, and the experiment stopped. About 15 minutes. |
| [Build a standalone app](standalone_app.md) | An experiment frozen into an app for a lab PC with no Python, from a config file or a script. About 15 minutes. |

## After Getting Started

| In Getting Started, you | Go further with |
|---|---|
| [Installed PyAcquisition](../getting_started/installation.md) | [Connect a real instrument](connect_instrument.md), with a VISA library, and [Build a standalone app](standalone_app.md), for a lab PC with no Python |
| [Described a rig in a config file](../getting_started/config_file.md) | [Tune your measurements](measurements.md), [Read your data](read_data.md) and [Build a config in the interface](setup_page.md) |
| [Added an instrument with `mock`](../getting_started/config_file.md#add-a-hardware-instrument) | [Connect a real instrument](connect_instrument.md), [Write a hardware instrument](hardware_instrument.md) and [Verify a driver on real hardware](verify_driver.md) |
| [Ran it from Python](../getting_started/python_api.md) | [Set the experiment's options](options.md), [Write a software instrument](software_instrument.md) and [Drive an experiment from a script](api_script.md) |
| [Added a calculated column](../getting_started/python_api.md#add-calculations) | [Calculate new columns](calculations.md) and [Record spectra and traces](traces.md) |
| [Wrote and queued a task](../getting_started/python_api.md#tasks-custom-automation) | [Write a task](write_task.md), [Sweep a temperature](sweep.md), [Queue, pause and save tasks](queue.md) and [Hold a temperature with PID](pid.md) |
