# Usage

[Getting Started](../getting_started/installation.md) takes you from nothing to a working, automated experiment. Each page here takes one thing you may want to do next, and shows how. Read them in any order, when you need them. For the full list of an option, driver or task, see [Reference](../reference/index.md).

## After Getting Started

| When you have done | Go further with |
|---|---|
| [0. Installation](../getting_started/installation.md) | [Connect a real instrument](connect_instrument.md), when you connect real hardware |
| [1. The Config File](../getting_started/config_file.md) | [Tune your measurements](measurements.md), [Read your data](read_data.md), [Build a config in the interface](setup_page.md), and [the interface and the API](running.md) |
| [2. The Python API](../getting_started/python_api.md) | [Set the experiment's options](options.md), [Calculate new columns](calculations.md), [Write a task](write_task.md), [Sweep a temperature](sweep.md), [Queue, pause and save tasks](queue.md) and [Hold a temperature with PID](pid.md) |

## Instruments

| Page | Covers |
|---|---|
| [Connect a real instrument](connect_instrument.md) | Your lock-in on GPIB, USB or serial instead of `mock`: its address, the adapter, and a second instrument from Python. About 10 minutes. |
| [Write a software instrument](software_instrument.md) | A disk-space monitor: a query, a command, and a choice, in the Instruments tab and the data file. About 15 minutes. |
| [Write a hardware instrument](hardware_instrument.md) | A driver for a Keithley 2400 SourceMeter: messages sent, replies taken apart, and the device's codes as a choice, tried on `mock`. About 20 minutes. |
| [Verifying instruments on real hardware](../dev/verifying_hardware.md) | Checking a driver against the device it drives. |

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
| [Hold a temperature with PID](pid.md) | A furnace held by the `PID` task on a queue of its own, recorded, and tuned from the interface while it runs. About 15 minutes. |

## The experiment

| Page | Covers |
|---|---|
| [Set the experiment's options](options.md) | A data folder for each sample and day, a quieter terminal, a port of its own, and which wins, the class or the file. About 10 minutes. |
| [Build a config in the interface](setup_page.md) | A rig's config file written from forms with `pyacquisition new`, checked as you go, and run from the same window. About 10 minutes. |
| [The interface and the API](running.md) | Starting and stopping, running without a window, the web API, and a standalone application. |
