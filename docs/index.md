---
hide:
  - navigation
  - toc
  - path
---

<div class="pa-hero" markdown>

<div class="pa-hero__text" markdown>

<p class="pa-eyebrow">Python · Lab automation</p>

# Talk to your instruments.<br><span class="pa-gradient">Skip the boilerplate.</span>

Compose your own tasks to build automated experiments of any complexity,
using ready-made instruments or your own, and write only the logic that is
unique to your science. Scheduling, logging, data files, live graphing and a
full GUI all come free.

[Get started](getting_started/installation.md){ .md-button .md-button--primary }
[Install](getting_started/installation.md){ .md-button }
[GitHub](https://github.com/jakeayres/pyacquisition){ .md-button }

<div class="pa-install" markdown>

```
uv add pyacquisition
```

</div>

</div>

</div>

<div class="pa-section pa-showcase" markdown>

## One experiment. Two ways to write it.

The interface, the recording and the data files are generated either way.

/// tab | <span class="pa-opt"><span class="pa-opt__kicker">In Python</span><span class="pa-opt__title">Two instruments. Three measurements. One command.</span><span class="pa-opt__text">A short script you can read top to bottom.</span></span>

<p class="pa-step"><span>1</span> Describe the experiment</p>

<div class="pa-annot" data-source="examples/front_page.py" markdown>

<div class="pa-ide" markdown>

```python title="my_experiment.py" linenums="1" hl_lines="5-6 9-10 11-12 14-18 21-22"
--8<-- "examples/front_page.py"
```

</div>

<div class="pa-annot__notes" markdown="0">
<div class="pa-note" style="--from: 5; --to: 6" data-contains="class MyExperiment"><b>Your experiment</b><span>Inherits the recording and the interface. Options such as <code>data_path</code> go in the class body.</span></div>
<div class="pa-note" style="--from: 9; --to: 10" data-contains="add_instrument"><b>Add an instrument</b><span>An id and an address. Its commands appear in the menus.</span></div>
<div class="pa-note" style="--from: 11; --to: 12" data-contains="add_measurement"><b>Add measurements</b><span>Any query, read every cycle and saved to the data file.</span></div>
<div class="pa-note" style="--from: 14; --to: 18" data-contains="Lakeshore_350"><b>Repeat for the rest of the rig</b><span>A second instrument, and a measurement that takes an argument.</span></div>
<div class="pa-note" style="--from: 21; --to: 22" data-contains=".run()"><b>Run it</b><span>Starts the recording and the interface.</span></div>
</div>

</div>

<p class="pa-step"><span>2</span> Run it</p>

<div class="pa-flow" markdown="0"><span class="cmd"><b>$</b> uv run my_experiment.py</span></div>

///

/// tab | <span class="pa-opt"><span class="pa-opt__kicker">In a config file</span><span class="pa-opt__title">Name your instruments. Get a lab.</span><span class="pa-opt__text">Declare the rig in TOML. There is no Python to write.</span></span>

<p class="pa-step"><span>1</span> Describe the experiment</p>

<div class="pa-annot" data-source="examples/front_page.toml" markdown>

<div class="pa-ide" markdown>

```toml title="rig.toml" linenums="1" hl_lines="1-2 4-12 14-20 22-25"
--8<-- "examples/front_page.toml"
```

</div>

<div class="pa-annot__notes" markdown="0">
<div class="pa-note" style="--from: 1; --to: 2" data-contains="[data]"><b>Set options</b><span>Where the data files go, and any other option.</span></div>
<div class="pa-note" style="--from: 4; --to: 12" data-contains="Lakeshore_350"><b>Add instruments</b><span>A class name, an adapter and an address. The key is the instrument's id.</span></div>
<div class="pa-note" style="--from: 14; --to: 20" data-contains="get_x"><b>Add measurements</b><span>An instrument and one of its queries, read every cycle and saved to the data file.</span></div>
<div class="pa-note" style="--from: 22; --to: 25" data-contains="args"><b>With arguments</b><span><code>args</code> gives a query its arguments. An enum member is named as text.</span></div>
</div>

</div>

<p class="pa-step"><span>2</span> Run it</p>

<div class="pa-flow" markdown="0"><span class="cmd"><b>$</b> uv run pyacquisition --toml rig.toml</span></div>

Or build the file in a window, from forms, with `uv run pyacquisition new rig.toml`: see [Setting Up in the Interface](usage/setup_page.md).

///

<!-- A screenshot of the running interface goes here. Suggested caption:
     "The interface is generated from the experiment above: live plots and values, every instrument query and command, the task queue and the log." -->

</div>

<div class="pa-section pa-features" markdown>

## Everything the experiment needs

<div class="grid cards" markdown>

-   :material-language-python:{ .middle } **All Python**

    Instruments, measurements, tasks and calculations are ordinary Python. Analyse the data with pandas, script a run from a notebook, and keep the whole experiment in version control.

    [The Python API](getting_started/python_api.md)

-   :material-file-cog-outline:{ .middle } **Configure, don't code**

    Describe the rig in a `.toml` file: instruments, measurements, data folder and logging. Drivers are included for lock-ins, temperature controllers, source meters and a magnet supply, and a mock adapter lets you develop without the device.

    [TOML configuration](usage/toml_config.md)

-   :material-monitor-dashboard:{ .middle } **A GUI for free**

    A control panel generated from your code: live plots and values, every instrument query and command, a task queue with pause and abort, and the log. There is no GUI code to write, and it opens in a browser too.

    [The interface](usage/running.md)

-   :material-format-list-checks:{ .middle } **Tasks that compose**

    Write a procedure as a small task, then build bigger ones from it, in sequence or at the same time. Pause, resume or abort at any point, and `teardown()` leaves the instruments safe. Ready-made: waits, PID control, temperature ramps and magnet sweeps.

    [Composing tasks](usage/composing_tasks.md)

-   :material-function-variant:{ .middle } **Calculations**

    Add columns as data is recorded: sums, rolling means, or any function of a row, saved next to the raw values. A calculation that needs a memory is a short class.

    [Calculations](usage/calculations.md)

-   :material-check-decagram-outline:{ .middle } **Verify against hardware**

    A built-in tool runs each supported instrument's queries and commands against the real device and checks the replies. It is read-only by default, with opt-in checks that change settings, and a dry run that contacts nothing.

    [Verifying hardware](dev/verifying_hardware.md)

</div>

</div>

<div class="pa-section" markdown>

## Supported instruments

<div class="pa-chips" markdown>
[Keithley 2000](instruments/keithley_2000.md)
[Keithley 6221](instruments/keithley_6221.md)
[Lakeshore 340](instruments/lakeshore_340.md)
[Lakeshore 350](instruments/lakeshore_350.md)
[Oxford Mercury iPS](instruments/mercury_ips.md)
[SR 830](instruments/sr_830.md)
[SR 860](instruments/sr_860.md)
[Signal generator](instruments/signal_generator.md)
[Clock](instruments/clock.md)
[Random number generator](instruments/random_number_generator.md)
</div>

Missing one? [Write your own instrument](usage/custom_instruments.md) by
following a worked example.

</div>

<div class="pa-cta" markdown>

## Ready to record some data?

[Get started](getting_started/installation.md){ .md-button .md-button--primary }
[How it compares](overview/comparison.md){ .md-button }

</div>
