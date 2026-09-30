# Record spectra and traces

<p class="pa-meta" markdown="span">About 15 minutes · Needs [Getting Started](../getting_started/python_api.md), and matplotlib (`uv add matplotlib`)</p>

A measurement is one number a row. A **trace** is a whole array at once: a spectrum, a network analyser's sweep, an oscilloscope's capture. PyAcquisition takes traces beside the rows, saves them in a file of their own beside the data file, links each to the row it was taken with, and shows them live. In this tutorial you take the spectrum of a sample as it cools: when you ask, then with every row, reduced to a column for the data file, and read back for analysis.

You write `sample.py` in your `my-lab` project, beside `simulated.py`: a cryostat, a lock-in, and a spectrometer, which stand in for real instruments. The sample has one resonance, which moves up in frequency as it warms.

<div class="gs" data-files="sample.py:versions spectra.py:versions" data-lines="24" data-term-lines="3" markdown>

<div class="gs-stage" markdown>

<div class="gs-notes" markdown>

<section class="gs-step" data-given markdown>

## Start from the simulated cryostat

```python title="sample.py"
--8<-- "examples/usage/traces/sample_1.py"
```

Copy this into `sample.py`. It is the sample from [Tune your measurements](measurements.md), at its third step: a clock, the cryostat, and the lock-in on the sample in it, measuring the time, the lock-in's `x` and `y`, and the temperature, `T`, each with its unit.

??? abstract "simulated.py: a cryostat, a lock-in and a spectrometer, simulated"
    Save this beside `sample.py`. It stands in for real hardware, and you don't need to read it.

    ```python title="simulated.py"
    --8<-- "examples/simulated_rig/simulated.py"
    ```

**More:** [Tune your measurements](measurements.md), which builds it.
{ .gs-more }

</section>

<section class="gs-step" markdown>

## Add a trace: the spectrum

```python title="sample.py" hl_lines="1 4-8 34-36"
--8<-- "examples/usage/traces/sample_2.py"
```

The simulated spectrometer takes the sample's spectrum, 2048 points from 100 to 300 GHz, in about a second. Its `get_spectrum` is a **trace method**, and `add_trace` adds a trace of it, called `spectrum`.

With nothing more, a spectrum is taken only when you ask: with **Acquire now** on its panel, or with the `AcquireTrace` task, which a task of your own can run at each step of a sweep.

??? tip "In a config file"
    A trace of a driver that comes with PyAcquisition can go in a config file's `[traces]`. The `TraceGenerator` is one:

    ```toml
    --8<-- "examples/traces.toml"
    ```

**More:** [`Trace`](../reference/python_api/traces.md#pyacquisition.core.trace_source.Trace), [`AcquireTrace`](../reference/tasks/acquire_trace.md), and [the `[traces]` table](../reference/config_file.md#traces).
{ .gs-more }

</section>

<section class="gs-step" markdown>

## Reduce each spectrum to a column

```python title="sample.py" hl_lines="36-38"
--8<-- "examples/usage/traces/sample_3.py"
```

`reduce` makes columns from each trace, on the row it was taken with. `peak_x` is where on its axis a trace peaks: here the resonance's frequency, as `spectrum_peak_x`, in GHz. So the resonance can be plotted against `T` like any other column, and the data file has it without the spectra. The others, such as `mean` and `max`, are listed with `Trace`, and a function of your own can be one too.

Every trace also has a column `spectrum_index`: the spectrum's number, on its row, which links the row to it.

**More:** [`Trace`'s reductions](../reference/python_api/traces.md#pyacquisition.core.trace_source.Trace), and [the data file's columns](../reference/data_files.md#the-data-file).
{ .gs-more }

</section>

<section class="gs-step" markdown>

## Take one with every row

```python title="sample.py" hl_lines="37-42"
--8<-- "examples/usage/traces/sample_4.py"
```

`every_rows=1` takes a spectrum within each row, and the row waits for it, so its columns are that row's. The rows slow to the spectrometer's pace, about 1 s, and the top bar says **slow**.

`every_rows=4` would take one with every fourth row. `every=10` would take one every 10 seconds instead, on a clock of its own, between the rows, which don't wait for it.

**More:** [`Trace`](../reference/python_api/traces.md#pyacquisition.core.trace_source.Trace), and [the top bar](../reference/interface.md#the-top-bar).
{ .gs-more }

</section>

<section class="gs-step" markdown>

## Run the experiment

```bash
uv run sample.py
```

**+ Add plot** now has a menu. Pick **Trace: spectrum**, for a panel of the latest spectrum and the three before it, fainter, and then **Map: spectrum**, for every spectrum of the file as a colour map, and set its **against** to `T`. Then cool the sample: in the **Instruments** tab, send `cryostat`'s `set_setpoint`, with **Output Channel** Output 1 and **Setpoint** 10. The resonance moves from about 230 GHz down to 190 GHz.

**More:** [trace and map panels](../reference/interface.md#the-plots).
{ .gs-more }

</section>

<section class="gs-step" markdown>

## Read the spectra back

```python title="spectra.py"
--8<-- "examples/usage/traces/spectra_1.py"
```

```bash
uv run spectra.py
```

```text
00.00 start.data: 23 spectra of 2048 points
from 20.0 K to 10.0 K
```

`max` picks the newest data file, and `read_traces` reads its spectra from the `.h5` file beside it. `traces.x` is the axis, `traces.channels["intensity"]` has a row for each spectrum, and `traces.info` is a table of when each was taken, with its row's values: `row.T` is the temperature it was taken at. The script plots every third spectrum, labelled with its temperature. It can read the file while the experiment is still writing it.

**More:** [`read_traces`](../reference/python_api/traces.md#pyacquisition.core.trace_file.read_traces), and [the trace file](../reference/data_files.md#the-trace-file), which xarray and h5py read too.
{ .gs-more }

</section>

<section class="gs-step" markdown>

## Give your own instrument a trace method

A trace method is a driver's method marked `@mark_trace`, which returns a `TraceData`: its channels by name, and its axis. The simulated spectrometer's is a model. A sweep that takes time names the methods that start it, say when it is done, and stop it. The trace is taken by calling them in turn, and stopped if it is aborted or takes longer than `timeout`. `channels` names the channels, so the reductions' columns are known before the first trace.

A trace method isn't in the **Instruments** tab: it is taken as a trace.

??? example "`SimulatedSpectrometer`, from simulated.py"
    ```python
    --8<-- "examples/simulated_rig/simulated.py:spectrometer"
    ```

**More:** [`mark_trace`](../reference/python_api/traces.md#pyacquisition.core.instrument.mark_trace), [`TraceData`](../reference/python_api/traces.md#pyacquisition.core.trace.TraceData), and [Write a hardware instrument](hardware_instrument.md), for the rest of a driver.
{ .gs-more }

</section>

</div>

</div>

</div>

## What you built

The spectrum through a cooldown from 20 K to 10 K:

<div class="gs-shot" markdown>

![The interface running sample.py: a trace panel of the latest spectrum, a peak at 190 GHz, with Acquire now, and a map panel of every spectrum against T from 10 to 20 K, the peak moving from 190 GHz at 10 K to 230 GHz at 20 K; the top bar says slow, and the Values tab has a spectrum_index tile](../images/usage/traces/panels.png){ .pa-shot }

<span class="gs-pin" style="--x: 28.0%; --y: 21.0%">1</span>
<span class="gs-pin" style="--x: 75.0%; --y: 42.9%">2</span>
<span class="gs-pin" style="--x: 31.5%; --y: 3.0%">3</span>
<span class="gs-pin" style="--x: 88.3%; --y: 84.3%">4</span>

</div>

<div class="gs-legend" markdown>

1. **Acquire now.** Takes a spectrum when you ask, whatever else is going on.
2. **The map.** Every spectrum of the file against `T`: the resonance moves down as the sample cools.
3. **slow.** Each row waits for its spectrum, so the rows take about 1 s, not 0.25.
4. **The spectrum's number.** `spectrum_index`, on its row, links the row to the spectrum in the trace file.

</div>

!!! success "Checkpoint"
    A trace panel shows the latest spectrum, and the map every spectrum against `T`, the resonance moving from about 230 GHz at 20 K to 190 GHz at 10 K. Every row of the data file has `spectrum_index` and `spectrum_peak_x`, with a `.h5` file of the same name beside it, and `spectra.py` says how many spectra it read, and draws them.

??? failure "Something not working?"
    - **The experiment stops as it starts, with `Task group terminated due to an error: Trace 'spectrum' needs an instrument's trace method (marked @mark_trace), such as generator.get_spectrum, not TraceData(...)`.** The trace was given a spectrum, `spectrometer.get_spectrum()`, instead of the method. Leave out the brackets.
    - **`FileNotFoundError: data\03.03 run 3.data has no trace file beside it.`** The newest data file isn't the sample's: it is from another experiment in the same folder. Give `read_traces` the file's name instead of `newest`.
    - **`KeyError: "There is no trace called 'spectra' in data\\00.00 start.h5."`** The name is the one given to `Trace`: `spectrum`.
    - **`ValueError: max() iterable argument is empty`.** There are no data files where the script looked: the terminal isn't in `my-lab`.

## What you learned

- A trace is a whole array at once, taken beside the rows and saved in a `.h5` file beside the data file.
- With neither `every` nor `every_rows`, a trace is taken when asked: **Acquire now**, or `AcquireTrace`. `every_rows` takes one within each row, which waits for it, and `every` one on a clock of its own.
- `reduce` makes columns from each trace, such as `peak_x`, on its row, and `<name>_index` links the row to the trace.
- The trace panel shows the latest, the map shows them all, and `read_traces` reads them back.
- A driver's trace method is marked `@mark_trace`, and returns a `TraceData`.

Next: [Writing tasks](tasks.md), to take a spectrum at each step of a sweep.
