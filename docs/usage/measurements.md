# Tune your measurements

<p class="pa-meta" markdown="span">About 10 minutes · Needs [Getting Started](../getting_started/python_api.md), and a lock-in and a Lakeshore 350 on your cryostat</p>

A **measurement** reads one query on every cycle, into a column of the data file. Getting Started's have a name, a query, and sometimes arguments. In this tutorial you tune them for a real measurement: a sample in a cryostat, measured with an SR830 lock-in, its temperature read by a Lakeshore 350. You give the values units, read the temperature from one of the controller's inputs, and read a value that rarely changes less often, so that the rest are read faster.

You write `sample.py`, a new experiment, in your `my-lab` project. Change the instruments' addresses to your own. With a Lakeshore 340, use `Lakeshore_340`: its queries take the same arguments.

<div class="gs" data-files="sample.py:versions" data-lines="24" data-term-lines="3" markdown>

<div class="gs-stage" markdown>

<div class="gs-notes" markdown>

<section class="gs-step" data-new-file markdown>

## Start from a lock-in and a Lakeshore

```python title="sample.py"
--8<-- "examples/usage/measurements/sample_1.py"
```

`sample.py` is an experiment in Python alone, with no config file. `setup()` makes a clock, the Lakeshore on the cryostat, and the lock-in on the sample, at their addresses, adds them, and measures the time and the lock-in's `x` and `y` on every cycle. `Sample().run()` starts it with the default options, which poll every 0.25 s.

**More:** [`Measurement`](../reference/python_api/measurement.md), and [Connect a real instrument](connect_instrument.md), to find the addresses.
{ .gs-more }

</section>

<section class="gs-step" markdown>

## Give the measurements units

```python title="sample.py" hl_lines="17-19"
--8<-- "examples/usage/measurements/sample_2.py"
```

`unit` is shown beside each value in the **Values** tab, and on a plot's axis, as `x (V)`. It is for reading: the data file's columns and numbers are the same either way. Any text is a unit (`"mV"`, `"Ω"`), and it isn't passed to the query.

A value with no unit is a number nobody can be sure of a month later, so give every one a unit.

**More:** [`Measurement`](../reference/python_api/measurement.md), and [`unit` in a config file](../reference/config_file.md#measurements).
{ .gs-more }

</section>

<section class="gs-step" markdown>

## Pass a choice: the input channel

```python title="sample.py" hl_lines="20-27"
--8<-- "examples/usage/measurements/sample_3.py"
```

A temperature controller reads several thermometers, and `get_temperature` takes which one, `input_channel`: a choice. A measurement passes a query's arguments by name, on every call, here the member `Lakeshore_350.InputChannel.INPUT_A`, the input your sample's thermometer is on. The driver holds its choices, so they need no import of their own.

Text works too: the name, `"INPUT_A"`, or the label the interface shows, `"Input A"`, in any case. Text that names no member stops the experiment at setup, and lists those that exist.

**More:** [the Lakeshore 350's queries](../reference/instruments/lakeshore_350.md), and [a choice in a config file](../reference/config_file.md#measurements).
{ .gs-more }

</section>

<section class="gs-step" markdown>

## Read the setpoint less often

```python title="sample.py" hl_lines="28-36"
--8<-- "examples/usage/measurements/sample_4.py"
```

The measurements are read one after another, every cycle. On real instruments each query takes time, tens of milliseconds over GPIB, so a long list slows every cycle. `call_every=10` reads the setpoint on every tenth cycle only, since it changes only when you change it. In between, the data file repeats its last value, so every row is complete.

The price is that it can be ten cycles out of date: 2.5 s at the default period.

**More:** [`Measurement`](../reference/python_api/measurement.md), and [how long the cycles really take](../reference/interface.md#the-top-bar).
{ .gs-more }

</section>

<section class="gs-step" data-result="[Experiment] API server on port 8000" markdown>

## Run the experiment

```bash
uv run sample.py
```

Plot `x` against `T`, with their units on the axes. Then, in the **Instruments** tab, pick `cryostat` and `set_setpoint`, with **Output Channel** Output 1 and a new **Setpoint**, and **Send**. `T` heads for it as your cryostat allows, and the `setpoint` tile changes on its next read, up to ten cycles later.

??? note "When a measurement fails"
    A query that raises an error, such as a timeout, is logged, in the **Logs** tab and the terminal, as `Error in measurement x: …`, and the experiment carries on. The row holds the measurement's last value, repeated, or nothing if it never had one. A column that stops changing is worth a look at the log.

**More:** [the plots](../reference/interface.md#the-plots), and [the Instruments tab](../reference/interface.md#the-dock).
{ .gs-more }

</section>

</div>

</div>

</div>

!!! success "Checkpoint"
    The **Values** tab shows `x` and `y` in V, and `T` and `setpoint` in K, and the plot's axes say `x (V)` and `T (K)`. After `set_setpoint`, the `setpoint` tile follows within ten cycles, and in the data file `setpoint` changes on a tenth row only.

??? failure "Something not working?"
    - **The experiment stops as it starts, with `Task group terminated due to an error: Could not open 'GPIB0::12::INSTR' with the pyvisa adapter:`, and VISA's reason.** No instrument answers at that address: see [Connect a real instrument](connect_instrument.md) to find it.
    - **The experiment stops as it starts, with ``Task group terminated due to an error: `input_channel`: 'INPUT_Z' is not one of INPUT_A, INPUT_B, INPUT_C, INPUT_D``.** The text names no member. Use one of those listed, or the label the interface shows.
    - **The experiment stops as it starts, with `Task group terminated due to an error: Invalid keyword argument 'channel' for function 'get_temperature'.`** The argument's name is wrong: the query's is `input_channel`. The [Lakeshore 350's page](../reference/instruments/lakeshore_350.md) lists each query's arguments.
    - **The experiment stops as it starts, with `Task group terminated due to an error:`, a number, and `is not a callable object`.** A measurement was given the query's answer, `lockin.get_x()`, instead of the query. Leave out the brackets.

## What you learned

- `unit` labels a value in the interface, and changes nothing in the data file.
- A query's arguments are keyword arguments of `Measurement`. A choice is a member, or text: its name or its label.
- `call_every` reads a value that rarely changes less often, repeating it in between, so that the rest are read faster.
- A measurement that fails is logged, and its last value is repeated, so the log says which values to trust.

Next: [Read your data](read_data.md) reads the data file into pandas, and plots it.
