# Basic Usage

`pyacquisition` turns a short Python script into a complete data acquisition application. You describe your experiment in Python and `pyacquisition` provides:

- **Continuous recording.** The values you choose are polled at a fixed period and written to comma separated files.
- **A control panel.** A graphical interface is generated automatically. Every function of every instrument is available from a menu, with no GUI code to write.
- **Live feedback.** Live values, live plots and a scrolling log.
- **Automation.** Experimental procedures written as *tasks* run from a queue, and can be paused or aborted at any time.

This guide teaches you to use it by building a real experiment, one small step at a time.

## What you will build

A lock-in amplifier is measuring a sample inside a cryostat, and the sample's signal disappears as it warms. You will write an experiment that reads the temperature and the signal, and a **task that sweeps the temperature by itself**, recording a data file at each step. Then you will analyse the result in Python.

<div class="pa-pair" markdown>
<figure markdown="span">
  ![The live plot: the lock-in signal falls away around 14 K](../images/tutorial/sweep-plot.png){ .pa-shot .pa-medium }
  <figcaption>What the experiment measures, live in the interface.</figcaption>
</figure>
<figure markdown="span">
  ![The temperature sweep running in the interface](../images/tutorial/sweep-running.png){ .pa-shot .pa-medium }
  <figcaption>The sweep running, and its log.</figcaption>
</figure>
</div>

You do not need any hardware. The first six lessons use a **simulated rig** that behaves like a real temperature controller and lock-in amplifier, so you can follow every step at your desk. In the last lesson you swap in real instruments, and nothing else changes.

## The building blocks

Everything in `pyacquisition` is put together from four things. You will meet each one in turn.

| Building block | What it is | In the tutorial |
|---|---|---|
| **Instrument** | A Python object that represents a piece of hardware (or software that behaves like it). It has *queries* that read values and *commands* that change something. | The temperature controller and the lock-in |
| **Measurement** | A value that is read on every cycle, shown live and saved to the data file. | The temperature, and the lock-in's `x` and `y` |
| **Task** | A procedure that you queue and run: ramp, wait, start a new file. Tasks can be built out of other tasks. | Going to a temperature, and the sweep |
| **Experiment** | The class that you write to bring the others together. | `MyExperiment` |

## The lessons

Each lesson takes a few minutes, builds on the last, and ends with a checkpoint so you know it worked.

| Lesson | You will | Time |
|---|---|---|
| [Installation](installation.md) | Install `pyacquisition`. | 5 min |
| [1. Your first experiment](first_experiment.md) | Write, run and explore the smallest useful experiment. | 5 min |
| [2. A simulated rig](simulated_rig.md) | Add instruments and measurements, and drive the rig by hand. | 10 min |
| [3. Recording data](recording_data.md) | Understand data files, start new ones, and add a calculation. | 8 min |
| [4. Your first task](first_task.md) | Write a task that ramps the temperature, and run it. | 12 min |
| [5. Composing tasks](building_a_sweep.md) | Build a sweep out of smaller tasks, and analyse the result. | 15 min |
| [6. Running tasks](queueing_tasks.md) | Queue, reorder, pause and abort tasks safely. | 8 min |
| [7. Real instruments](real_instruments.md) | Swap the simulated rig for real hardware. | 10 min |

## How to use this guide

- **Do the lessons in order.** Every lesson starts from the file you finished the last one with.
- **Type the code, or copy it, but run it.** Each lesson shows the complete file, with the lines that are new highlighted.
- **The screenshots are real.** They were taken from the interface running these exact scripts, so what you see should match.
- **The code is tested.** Every script in the guide lives in the repository's [`examples/`](https://github.com/jakeayres/pyacquisition/tree/main/examples) folder, and is checked by the test suite.
- **When you want the whole story of a topic,** each lesson links to a page in [Advanced Usage](advanced.md) that covers it in full.

!!! note "Some Python helps, but you do not need much"
    You will write ordinary classes and functions. The one less common feature is that tasks use `async`/`await`, and the lesson that introduces it explains exactly what you need to know.
