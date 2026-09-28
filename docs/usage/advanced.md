# Advanced Usage

**Basic Usage** is a walkthrough: it takes you from nothing to a working, automated experiment, one lesson at a time. **Advanced Usage** is the other half. Each page takes one topic, such as composing tasks, writing your own instruments or running several task managers, and covers all of it, including the parts a walkthrough leaves out.

You do not need to read these pages in order, or before you start. Come to them when a lesson points you here, or when you need the detail.

## From the lessons to the detail

| When you have done | Read this for the whole story |
|---|---|
| [Lesson 1: your first experiment](first_experiment.md) | [Experiment options](setting_up.md), and [the interface and the API](running.md) |
| [Lesson 2: a simulated rig](simulated_rig.md) | [Adding instruments](instruments.md) and [writing your own instrument](custom_instruments.md) |
| [Lesson 3: recording data](recording_data.md) | [Measurements and data files](measurements.md) and [calculations](calculations.md) |
| [Lesson 4: your first task](first_task.md) | [Writing tasks](tasks.md) |
| [Lesson 5: composing tasks](building_a_sweep.md) | [Composing tasks](composing_tasks.md), including running tasks at the same time |
| [Lesson 6: running tasks](queueing_tasks.md) | [Running tasks](running_tasks.md), including several task managers and scripting |
| [Lesson 7: real instruments](real_instruments.md) | [Adding instruments](instruments.md#adding-hardware-instruments), and [verifying hardware](../dev/verifying_hardware.md) |

## The experiment

| Page | Covers |
|---|---|
| [Experiment options](setting_up.md) | Every option you can pass to `Experiment`, and the `setup()` and `teardown()` hooks. |
| [The interface and the API](running.md) | The windows and menus in detail, running without the interface, the local web API, and why `if __name__ == "__main__":` matters. |
| [TOML configuration](toml_config.md) | Describe an experiment in a `.toml` file instead of Python, and run hardware instruments without the device. |

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
