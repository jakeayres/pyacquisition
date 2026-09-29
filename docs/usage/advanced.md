# Advanced Usage

**Getting Started** is a walkthrough: it takes you from nothing to a working, automated experiment, one step at a time. **Advanced Usage** is the other half. Each page takes one topic, such as composing tasks, writing your own instruments or running several task managers, and covers all of it, including the parts a walkthrough leaves out.

You do not need to read these pages in order, or before you start. Come to them when Getting Started points you here, or when you need the detail.

## From Getting Started to the detail

| When you have done | Read this for the whole story |
|---|---|
| [0. Installation](../getting_started/installation.md) | [Adding instruments](instruments.md#adding-hardware-instruments), when you connect real hardware |
| [1. The Config File](../getting_started/config_file.md) | [TOML configuration](toml_config.md), [measurements and data files](measurements.md), and [the interface and the API](running.md) |
| [2. The Python API](../getting_started/python_api.md) | [`setup()`, `teardown()` and experiment options](setting_up.md), [calculations](calculations.md), [writing tasks](tasks.md), [composing tasks](composing_tasks.md) and [running tasks](running_tasks.md) |

## The experiment

| Page | Covers |
|---|---|
| [Experiment options](setting_up.md) | Every option you can pass to `Experiment`, and the `setup()` and `teardown()` hooks. |
| [The interface and the API](running.md) | The windows and menus in detail, running without the interface, the local web API, and why `if __name__ == "__main__":` matters. |
| [TOML configuration](toml_config.md) | Describe an experiment in a `.toml` file instead of Python, and run hardware instruments without the device. |
| [Setting up in the interface](setup_page.md) | Build or change a TOML config from forms, with `pyacquisition new`, and run it from there. |

## Instruments and data

| Page | Covers |
|---|---|
| [Adding instruments](instruments.md) | The instruments that are included, and how to add software and hardware instruments. |
| [Writing your own instrument](custom_instruments.md) | Wrap a new device, or write a software instrument. |
| [Measurements and data files](measurements.md) | Queries with arguments, slow queries, failing measurements, file names and reading data. |
| [Calculations](calculations.md) | Derive new columns as you record: sums, rolling means, and your own. |
| [Traces and spectra](traces.md) | Take whole arrays, such as spectra, beside the rows: occasionally, on a clock or with every row, reduced to columns, shown live and saved beside the data file. |

## Tasks and procedures

| Page | Covers |
|---|---|
| [Writing tasks](tasks.md) | How a task runs, `setup()` and `teardown()`, registering tasks, and the pitfalls. |
| [Composing tasks](composing_tasks.md) | Building tasks out of tasks, and running tasks at the same time. |
| [Running tasks](running_tasks.md) | The queue, pause and abort, several task managers, and running tasks from a script. |
| [The included tasks](../tasks/overview.md) | `NewFile`, `WaitFor`, `WaitUntil`, `PID` and the rest. |

## Reference

The [Experiment API](../experiment/experiment.md), the [instruments](../instruments/overview.md) and the [tasks](../tasks/overview.md) are all documented from the code's own docstrings.

If you are contributing to `pyacquisition` itself, or verifying an instrument against real hardware, start at [For developers](../dev/overview.md).
