# Connect a real instrument

<p class="pa-meta" markdown="span">About 10 minutes · Needs [Getting Started](../getting_started/python_api.md), and an instrument on GPIB, USB or serial, or follow along with `mock`</p>

Getting Started's lock-in is a stand-in: the `mock` adapter answers for it. In this tutorial you connect the real one. You find its address, tell the experiment how to reach it, record what it measures, and check that it answers. Then you connect a second instrument, a multimeter, from Python. The same steps connect any instrument that has a [driver](../reference/instruments/overview.md).

It starts where [2. The Python API](../getting_started/python_api.md) ends: your `my-lab` project, with `rig.toml` and `lab.py`. With no instrument at hand, follow along and keep `adapter = "mock"`: everything runs, and the readings are 0.

<div class="gs" data-files="rig.toml:versions lab.py:versions" data-lines="22" data-term-lines="4" markdown>

<div class="gs-stage" markdown>

<div class="gs-notes" markdown>

<section class="gs-step" data-given markdown>

## Start from the Getting Started rig

```python title="lab.py"
--8<-- "examples/usage/connect_instrument/lab_1.py"
```

```toml title="rig.toml"
--8<-- "examples/usage/connect_instrument/rig_1.toml"
```

These are `rig.toml` and `lab.py` as [2. The Python API](../getting_started/python_api.md) left them. The lock-in, an SR830, is on `mock`, which answers every query with the value last set, or 0.

`lab.py`'s `setup()` sets the lock-in's frequency to 137 Hz, and `teardown()` turns its output down to 4 mV. A real lock-in does both, so change them to what your experiment needs before you connect it.

**More:** [2. The Python API](../getting_started/python_api.md), which builds them, and [the SR 830](../reference/instruments/sr_830.md).
{ .gs-more }

</section>

<section class="gs-step" markdown>

## Find the instrument's address

```bash
uv run python -c "import pyvisa; print(pyvisa.ResourceManager().list_resources())"
```

```text
('ASRL1::INSTR', 'ASRL3::INSTR', 'GPIB0::8::INSTR')
```

Every instrument has an **address**, and VISA, the library that talks to instruments, lists the ones it can reach. `pyvisa`, which PyAcquisition installs, asks it. This output is an example: yours lists what is connected to your computer.

`GPIB0::8::INSTR` is the instrument at GPIB address 8, on the first GPIB card. An instrument shows its own GPIB address in its front-panel settings, and an SR830's is 8 unless someone changed it. `ASRL` addresses are serial ports, and `USB0::…` ones are USB instruments.

??? tip "NI MAX lists them too"
    With NI-VISA installed, NI Measurement & Automation Explorer (NI MAX) lists the instruments under **Devices and Interfaces**, and can send `*IDN?` to one to find out which it is.

**More:** [the `pyvisa` adapter](../reference/adapters.md#pyvisa), and [installing a VISA library](../getting_started/installation.md#before-you-connect-real-instruments).
{ .gs-more }

</section>

<section class="gs-step" markdown>

## Connect it with pyvisa

```toml title="rig.toml" hl_lines="7"
--8<-- "examples/usage/connect_instrument/rig_2.toml"
```

`adapter = "pyvisa"` reaches the device itself, through VISA, instead of `mock`. `resource` is its address. Getting Started's is already `GPIB0::8::INSTR`, so change it only if yours is different.

The experiment opens the connection as it starts, and closes it as it ends, after `teardown()`.

??? tip "Behind a Prologix controller?"
    A Prologix GPIB-USB controller shows up as a serial port, and needs no VISA library. Use `adapter = "prologix"`, and the port and the GPIB address as the resource: `resource = "COM3::8"`.

??? tip "Over a serial cable?"
    The address is a serial port, and the connection needs the settings the instrument's manual gives, in `args`:

    ```toml
    resource = "ASRL3::INSTR"
    args = { baud_rate = 9600, read_termination = "\r" }
    ```

    `read_termination` is what ends each reply. These values are an example: use your manual's.

**More:** [the `pyvisa` adapter](../reference/adapters.md#pyvisa), [`prologix`](../reference/adapters.md#prologix), and [the `[instruments]` table](../reference/config_file.md#instruments).
{ .gs-more }

</section>

<section class="gs-step" markdown>

## Record its readings

```toml title="rig.toml" hl_lines="13-14"
--8<-- "examples/usage/connect_instrument/rig_3.toml"
```

Two measurements record the lock-in's outputs on every cycle, as its display shows them: `x`, the part of the signal in phase with the reference, and `y`, the part 90° out of phase. `unit` labels them in the interface.

Any query of a driver can be a measurement. [The SR 830's page](../reference/instruments/sr_830.md) lists them all, each with what it answers.

**More:** [the `[measurements]` table](../reference/config_file.md#measurements), and [Tune your measurements](measurements.md).
{ .gs-more }

</section>

<section class="gs-step" data-result="lockin answers in the Instruments tab." markdown>

## Check the lock-in answers

```bash
uv run lab.py
```

In the **Instruments** tab, pick `lockin`, then `identify`, and press **Read**. The lock-in answers with its make, model, serial number and firmware, such as `Stanford_Research_Systems,SR830,s/n12345,ver1.07`. An answer means the address is right. On `mock`, it is `MOCK,GPIB0::8::INSTR,0,0`.

The `x` and `y` tiles, in **Values**, follow the signal at the lock-in's input.

**More:** [the Instruments tab](../reference/interface.md#the-dock), and [testing an address in the setup page](setup_page.md), before a run.
{ .gs-more }

</section>

<section class="gs-step" markdown>

## Connect a multimeter in Python

```python title="lab.py" hl_lines="3-4 32-34"
--8<-- "examples/usage/connect_instrument/lab_2.py"
```

An instrument can be connected in `setup()` instead. A driver takes the instrument's name, its address, and options as keyword arguments, and `pyvisa` is the adapter unless you give another. This Keithley 2000 multimeter is at its usual GPIB address, 16, and waits up to 10 s for a reply (`timeout` is in milliseconds, 5000 by default), since averaging many readings can take seconds. With no multimeter, add `adapter="mock"`.

From the file, an instrument that can't be opened is left out, with a warning. From Python, the error stops the experiment.

**More:** [the Keithley 2000](../reference/instruments/keithley_2000.md), and [`Instrument`](../reference/python_api/instrument.md#pyacquisition.core.instrument.Instrument), which every driver takes its arguments from.
{ .gs-more }

</section>

<section class="gs-step" data-result="dmm is in the Instruments tab." markdown>

## Run the experiment

```bash
uv run lab.py
```

`dmm` joins the **Instruments** tab as **Keithley_2000**, and its reading, `v`, is recorded on every cycle with the rest. Its `identify` answers as the lock-in's did, with the multimeter's own make and model.

**More:** [the Instruments tab](../reference/interface.md#the-dock), and [data files](../reference/data_files.md).
{ .gs-more }

</section>

</div>

</div>

</div>

!!! success "Checkpoint"
    `identify` on `lockin` answers with the lock-in's own make and model (`MOCK,GPIB0::8::INSTR,0,0` on `mock`). `x` and `y` are recorded on every cycle, and so is `v`, from `dmm`, which is in the **Instruments** tab as **Keithley_2000**.

??? failure "Something not working?"
    - **`list_resources()` prints `()`.** VISA found nothing. Check the instrument is on, and its cable is in. GPIB needs a VISA library: without one, `pyvisa` uses `pyvisa-py`, which reaches some serial, USB and Ethernet instruments but no GPIB ones, and warns `TCPIP:instr resource discovery is limited to the default interface`.
    - **The log says `Failed to configure instrument 'lockin': Could not open 'GPIB0::8::INSTR' with the pyvisa adapter:`, and VISA's reason.** The experiment starts without the lock-in, and without its measurements (`Instrument 'lockin' not found for measurement 'x'`). Then `lab.py` stops with `Task group terminated due to an error: 'lockin'`, since its `setup()` uses the lock-in. Check the address against `list_resources()`. A reason of `Please install linux-gpib (Linux) or gpib-ctypes` means there is no VISA library.
    - **The experiment stops as it starts, with `Task group terminated due to an error: Could not open 'GPIB0::16::INSTR' with the pyvisa adapter:`, and VISA's reason.** There is no multimeter at that address. From Python, that stops the experiment.
    - **The log says `Error in measurement x: VI_ERROR_TMO (-1073807339): Timeout expired before operation completed.` on every cycle.** The connection opened, but nothing answered in time. The instrument's own GPIB address may differ from the resource's, or, over serial, `baud_rate` or `read_termination` may be wrong. A slow instrument needs a longer `timeout`, such as `args = { timeout = 10000 }`. The experiment carries on, and the column is left empty, or repeats the instrument's last answer if it gave one before.

## What you learned

- An instrument's **address** says how to reach it, and `pyvisa`'s `list_resources()` lists the ones VISA can see.
- `adapter = "pyvisa"` connects to the real device, `mock` stands in for it, and `prologix` goes through a Prologix controller. Options for the connection go in `args`.
- `identify` checks that the address is the instrument you meant.
- In Python, a driver takes a name, an address and options. A failure there stops the experiment, while from a file the instrument is left out.

Next: [Write a hardware instrument](hardware_instrument.md), for a device that has no driver yet.
