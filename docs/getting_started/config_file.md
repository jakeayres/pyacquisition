# 1. The Config File

<p class="pa-meta" markdown="span">About 10 minutes · Needs [0. Installation](installation.md)</p>

An experiment in PyAcquisition is made of **instruments**, the things it reads from and controls, and **measurements**, the values it reads from them on every cycle. From those it makes the rest: the interface, a data file with a column for each measurement, and a log.

All of that can be described in one small file. It is written in [TOML](https://toml.io/en/), a simple format: `[tables]`, each with `key = value` lines under it. In this part you build the file a few lines at a time. There is no Python to write and nothing to plug in, since every instrument here is a software one or a stand-in for the real thing. Keep the `my-lab` project from [installation](installation.md) open in your editor, and follow along: every step runs.

<div class="gs" markdown>

<div class="gs-stage" markdown>

<div class="gs-notes" markdown>

<section class="gs-step" data-new-file data-result="The interface opens, with nothing in it yet." markdown>

## Start with an empty file

Make an empty file in `my-lab` called `rig.toml`, and run it:

```bash
uv run pyacquisition --toml rig.toml
```

`pyacquisition --toml` runs the experiment a file describes, and an empty file is already one. The window opens, titled `rig` after the file, with nothing in it yet, and the terminal logs what the experiment is doing.

It makes a `data` folder for its data files, and a `logs` folder too. Close the window, and choose **Stop experiment**.

**More:** [a tour of the window](../usage/running.md#the-interface), and [everything a config file can say](../usage/toml_config.md).
{ .gs-more }

</section>

<section class="gs-step" markdown>

## Add an instrument

```toml
[instruments]
clock = { instrument = "Clock" }
```

`[instruments]` is a table of the experiment's instruments, one to a line.

On the left, `clock` is the instrument's name: yours to choose, and how the rest of the file refers to it. `instrument = "Clock"` names its **driver**, the code that knows how to talk to it. `Clock` is a *software* instrument, which runs on your computer, so there is nothing to connect.

**More:** [every driver](../instruments/overview.md), and [the `[instruments]` table](../usage/toml_config.md#instruments-section).
{ .gs-more }

</section>

<section class="gs-step" markdown>

## Measure it

```toml
[measurements]
time = { instrument = "clock", method = "time" }
```

`[measurements]` is a table of what to read. Each names an instrument, and a `method`: one of the instrument's **queries**, here the clock's `time`, the seconds since the clock was made. The name on the left, `time`, is the column's.

On every cycle each measurement is read once, and becomes a live value, a line you can plot, and a column in the data file.

**More:** [the Clock's queries](../instruments/clock.md), and [the `[measurements]` table](../usage/toml_config.md#measurements-section).
{ .gs-more }

</section>

<section class="gs-step" markdown>

## Give it something to watch

```toml
[instruments]
signal = { instrument = "SignalGenerator" }

[measurements]
wave = { instrument = "signal", method = "sine", args = { frequency = 0.2 } }
```

`SignalGenerator` is another software instrument: it makes waveforms from the time. The `wave` measurement reads its sine wave, and `args` passes the query its arguments, here a `frequency` of 0.2 Hz, one cycle every five seconds. The others, such as `amplitude`, keep their defaults.

Add each line under its table. A table can only appear once in a file, so the tables are shown here only to say where the lines go.

**More:** [the Signal Generator's waveforms and their arguments](../instruments/signal_generator.md), and [queries with arguments](../usage/measurements.md#queries-with-arguments).
{ .gs-more }

</section>

<section class="gs-step" markdown>

## Measure faster

```toml
[rack]
period = 0.2
```

The **rack** is the part of the experiment that reads the measurements, each in turn, once a cycle. `[rack]` sets its options.

`period` is the time from one cycle to the next, in seconds: 0.25 unless you say otherwise. `0.2` makes it five times a second.

**More:** [the `[rack]` table](../usage/toml_config.md#rack-section), and [how often data is recorded](../usage/measurements.md#how-often-is-data-recorded).
{ .gs-more }

</section>

<section class="gs-step" markdown>

## Add a real instrument

```toml
[instruments.lockin]
instrument = "SR_830"
adapter = "mock"
resource = "GPIB0::8::INSTR"
```

`SR_830` is the driver for a Stanford Research SR830 lock-in amplifier. A hardware instrument needs two more keys: an `adapter`, how the computer reaches it, and a `resource`, its address.

The `mock` adapter stands in for the device, answering each query with the value last set, or 0. So the driver runs without one, and its queries and commands are all in the interface's **Instruments** tab to try.

??? tip "Have a real SR830 connected?"
    Use it instead: set `adapter = "pyvisa"`, and `resource` to its address, such as `GPIB0::8::INSTR` at GPIB address 8. Through a Prologix GPIB-USB controller, it is `adapter = "prologix"`, with the port and the GPIB address as the resource, such as `COM3::8`.

    Any other instrument with a driver connects the same way.

`[instruments.lockin]` is the same as a line under `[instruments]`, as a table of its own because it is longer.

**More:** [the SR 830](../instruments/sr_830.md), [the `mock` adapter](../usage/toml_config.md#running-hardware-instruments-without-the-device), [finding an instrument's address](../usage/instruments.md#finding-the-address), [a Prologix controller](../usage/toml_config.md#instruments-behind-a-prologix-gpib-usb-controller), and [installing a VISA library](installation.md#real-instruments-later) for GPIB.
{ .gs-more }

</section>

<section class="gs-step" data-result="Recording every 0.2 s to data/01.00 start.data" markdown>

## Run it

```bash
uv run pyacquisition --toml rig.toml
```

The same command as before, now with the whole rig. The experiment reads the measurements every 0.2 s, and writes each cycle as a row of a data file in `data`, with a column for each measurement.

Each run starts a new data file, numbered on from those already there, so that none is overwritten: after the empty run's `00.00 start.data`, this one is `01.00 start.data`. That is a whole experiment, in fifteen lines.

**More:** [data files and their names](../usage/measurements.md#data-files), and [reading your data](../usage/measurements.md#reading-your-data).
{ .gs-more }

</section>

</div>

</div>

</div>

## What you built

Everything in the window comes from the file:

<div class="gs-shot" markdown>

![The interface running rig.toml: a live plot of wave against time, 00.00 start.data and Every 0.2 s in the top bar, and a tile for each measurement](../images/getting_started/interface.png){ .pa-shot }

<span class="gs-pin" style="--x: 19%; --y: 3%">1</span>
<span class="gs-pin" style="--x: 26.8%; --y: 3%">2</span>
<span class="gs-pin" style="--x: 25.5%; --y: 16%">3</span>
<span class="gs-pin" style="--x: 39.6%; --y: 81.1%">4</span>
<span class="gs-pin" style="--x: 7.9%; --y: 72.2%">5</span>
<span class="gs-pin" style="--x: 14%; --y: 72.2%">6</span>

</div>

<div class="gs-legend" markdown>

1. **The data file.** Every row, saved as it is measured. Click it for more.
2. **Every 0.2 s.** The period from `[rack]`. The button beside it pauses measuring.
3. **The plot.** Any measurement against any other, live.
4. **Values.** A tile for each measurement, with its latest reading.
5. **Queue.** Waits, new files, and later your own tasks.
6. **Instruments.** Every query and command of each instrument, to send by hand.

</div>

!!! success "Checkpoint"
    The plot shows `wave` swinging between -1 and 1, the top bar says **Every 0.2 s**, and the newest file in `data` grows while it runs.

??? failure "Something not working?"
    - **`Cannot declare ('instruments',) twice`.** A table appears twice. Put the new lines under the `[instruments]` or `[measurements]` you already have.
    - **`Config contains instruments that are not in the instrument map`.** A driver's name is misspelt. Names are case sensitive: `SignalGenerator`, not `signalgenerator`. The [Instruments](../instruments/overview.md) pages list them.
    - **A real instrument is missing from the Instruments tab.** An instrument that can't be opened, at a wrong address say, is skipped with a warning in the log, and the rest of the experiment still starts. Check its address, and that a VISA library is installed for GPIB.
    - **No window appears.** Look at the terminal for an error. The page is also at [http://localhost:8000](http://localhost:8000) in a browser.

## What you learned

- A TOML file is a whole experiment: `[instruments]`, `[measurements]`, and options such as `[rack]`.
- An instrument has a name and a driver. A hardware one also needs an `adapter` and a `resource`, and `mock` stands in until the device is connected.
- A measurement reads one of an instrument's queries on every cycle, into a column of the data file. Each run starts a new data file.

Next: [2. The Python API](python_api.md) keeps this file as it is, and adds a calculation and a task of your own in a short Python file beside it.

!!! tip "Every option the file can take"
    [TOML Configuration](../usage/toml_config.md) lists them all, section by section. To write the file from forms instead, run `uv run pyacquisition new rig.toml` (see [Setting Up in the Interface](../usage/setup_page.md)).
