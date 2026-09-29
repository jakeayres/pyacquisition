# Usage

[Getting Started](../getting_started/installation.md) takes you from nothing to a working, automated experiment. Each page here takes one thing you may want to do next, and shows how. Read them in any order, when you need them. For the full list of an option, driver or task, see [Reference](../reference/index.md).

## After Getting Started

| When you have done | Go further with |
|---|---|
| [0. Installation](../getting_started/installation.md) | [Adding instruments](instruments.md#adding-hardware-instruments), when you connect real hardware |
| [1. The Config File](../getting_started/config_file.md) | [Measurements and data files](measurements.md), [Setting up in the interface](setup_page.md), and [the interface and the API](running.md) |
| [2. The Python API](../getting_started/python_api.md) | [Experiment options](setting_up.md), [Calculations](calculations.md), [Writing tasks](tasks.md), [Composing tasks](composing_tasks.md) and [Running tasks](running_tasks.md) |

## Instruments

| Page | Covers |
|---|---|
| [Adding instruments](instruments.md) | Adding the included instruments, software and hardware, and finding an instrument's address. |
| [Write a software instrument](software_instrument.md) | A simulated thermometer: a query, a command, and a choice of sensor, in the Instruments tab. About 15 minutes. |
| [Writing your own instrument](custom_instruments.md) | A driver for a device, and a trace method. |
| [Verifying instruments on real hardware](../dev/verifying_hardware.md) | Checking a driver against the device it drives. |

## Data

| Page | Covers |
|---|---|
| [Measurements and data files](measurements.md) | Units, queries with arguments, slow queries, failing measurements, and reading the data back. |
| [Calculations](calculations.md) | New columns worked out as you record: sums, rolling means, and your own. |
| [Traces and spectra](traces.md) | Whole arrays, such as spectra, taken beside the rows, reduced to columns, shown live, and saved beside the data file. |

## Tasks

| Page | Covers |
|---|---|
| [Writing tasks](tasks.md) | How a task runs, its hooks, and registering it. |
| [Composing tasks](composing_tasks.md) | Tasks built from tasks, and tasks run at the same time. |
| [Running tasks](running_tasks.md) | The queue, pause and abort, several task managers, and tasks queued from a script. |

## The experiment

| Page | Covers |
|---|---|
| [Experiment options](setting_up.md) | Setting an experiment's options in Python, and the `setup()` and `teardown()` hooks. |
| [Setting up in the interface](setup_page.md) | Building or changing a config file from forms, with `pyacquisition new`, and running it from there. |
| [The interface and the API](running.md) | Starting and stopping, running without a window, the web API, and a standalone application. |
