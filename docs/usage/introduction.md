# Introduction

`pyacquisition` turns a short Python script into a complete data acquisition application. You describe your experiment in Python and `pyacquisition` provides:

- **Continuous recording.** The values you choose are polled at a fixed period and written to comma separated files.
- **A control panel.** A graphical interface is generated automatically. Every function of every instrument is available from a menu, with no GUI code to write.
- **Live feedback.** Live values, live plots and a scrolling log.
- **Automation.** Experimental procedures written as *tasks* run from a queue, and can be paused or aborted at any time.

Everything the interface does is also available over a local HTTP API, so it can be driven from other programs.

## The building blocks

An experiment is put together from four things:

| Building block | What it is | Example |
|---|---|---|
| **Instrument** | A Python object that represents a piece of hardware (or a piece of software that behaves like one). It has *queries* that read values and *commands* that change something. | A lock-in amplifier, a temperature controller, a clock |
| **Measurement** | A value that is read on every cycle and saved to the data file. | The lock-in's X voltage |
| **Task** | A procedure that you queue up and run: sweep a parameter, wait, start a new file. Tasks can be built out of other tasks. | Record for ten minutes, then start a new file |
| **Experiment** | The class that you write to bring the others together. | `MyExperiment` |

## What you will build

The rest of this guide builds one experiment step by step. It uses a *simulated* random number generator, so you can follow every step at your desk without any hardware connected. Swapping in a real instrument is a small change, which is shown along the way.

| Page | What you will do |
|---|---|
| [Installation](installation.md) | Install `pyacquisition`. |
| [Setting up an experiment](setting_up.md) | Write the skeleton of an experiment. |
| [Running an experiment](running.md) | Start it, and find your way around the interface and your data. |
| [Adding instruments](instruments.md) | Add software and hardware instruments. |
| [Writing your own instrument](custom_instruments.md) | Wrap a new device, or write a software instrument. |
| [Measurements and data files](measurements.md) | Choose what is recorded and where it goes. |
| [Writing tasks](tasks.md) | Automate a procedure. |
| [Composing tasks](composing_tasks.md) | Build larger procedures out of smaller ones. |
| [Running tasks](running_tasks.md) | Queue, pause, abort and script tasks. |

!!! note "Some Python helps, but you do not need much"
    You will write ordinary classes and functions. The one less common feature is that tasks use `async`/`await`, and this guide explains exactly what you need to know when you get there.
