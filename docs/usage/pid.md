# Hold a temperature with PID

<p class="pa-meta" markdown="span">About 15 minutes · Needs [Getting Started](../getting_started/python_api.md)</p>

A temperature controller holds a temperature by itself. For something with no controller, a heater driven by a power supply, say, PyAcquisition's `PID` task does it: every second it reads the temperature, and sets the heater's power to bring it to the setpoint. In this tutorial you hold a furnace at 60 °C with one, on a queue of its own, so that it runs for the whole experiment while the main queue stays free. You record what it does, and change its setpoint and gains from the interface while it runs.

You write `hold.py`, a new experiment, in your `my-lab` project, beside `furnace.py`: a simulated furnace, with a heater's power in and the temperature out, and nothing to control it. At full power it settles at 100 °C.

<div class="gs" data-files="hold.py:versions" data-lines="26" data-term-lines="3" markdown>

<div class="gs-stage" markdown>

<div class="gs-notes" markdown>

<section class="gs-step" data-new-file markdown>

## Start from a furnace

```python title="hold.py"
--8<-- "examples/usage/pid/hold_1.py"
```

`hold.py` measures the time, and the furnace's temperature, in °C. The furnace has what a PID needs: a query to read, `temperature`, and a command to write, `set_power`, in percent.

??? abstract "furnace.py: a furnace, simulated"
    Save this beside `hold.py`. It stands in for a real heater and thermometer, and you don't need to read it.

    ```python title="furnace.py"
    --8<-- "examples/usage/pid/furnace.py"
    ```

**More:** [Write a software instrument](software_instrument.md), for how `furnace.py` is written.
{ .gs-more }

</section>

<section class="gs-step" markdown>

## Run a PID on a queue of its own

```python title="hold.py" hl_lines="4 16-26"
--8<-- "examples/usage/pid/hold_2.py"
```

`PID` is a task that never finishes. Every second it reads `read`, works out an output from how far that is from `setpoint`, and writes it with `write`: give it the functions themselves, with no brackets. `kp` and `ki` are its proportional and integral gains, and `output_min` and `output_max` keep the power between 0 and 100 %. Always limit the output to what your hardware can take.

`add_task_manager` adds a second queue, `control`, and the PID is queued on it, so it starts with the experiment. A task that never finishes holds up everything behind it, so it has a queue of its own, and the main one stays free.

**More:** [`PID`'s settings](../reference/tasks/pid.md#settings), and [`add_task_manager`](../reference/python_api/experiment.md#pyacquisition.core.experiment.Experiment.add_task_manager).
{ .gs-more }

</section>

<section class="gs-step" markdown>

## Record what it is doing

```python title="hold.py" hl_lines="32-35"
--8<-- "examples/usage/pid/hold_3.py"
```

`pid.output` is the power it last wrote, and `pid.setpoint` the temperature it is holding. They are ordinary attributes, so a measurement records them with a `lambda`, a function of nothing that reads them each time. So the data file has the power and the setpoint beside the temperature, to plot now and to look back at later. `pid.error` is there too, the difference between the two.

**More:** [what the PID is doing](../reference/tasks/pid.md#what-the-pid-is-doing).
{ .gs-more }

</section>

<section class="gs-step" markdown>

## Change the setpoint from the interface

```python title="hold.py" hl_lines="3-7 32 44-67"
--8<-- "examples/usage/pid/hold_4.py"
```

A PID made in code isn't in the interface, so a small [software instrument](software_instrument.md) puts it there. `Controls` has a query for the setpoint, and commands to set it and the gains, which change the PID's attributes. The PID reads them on every cycle, so a change takes effect at once.

It is added as the instrument `pid`, and given the PID.

**More:** [changing settings while it runs](../reference/tasks/pid.md#changing-settings-while-it-runs).
{ .gs-more }

</section>

<section class="gs-step" data-result="[furnace] Holding 60.0 (period 1.0 s)" markdown>

## Run the experiment

```bash
uv run hold.py
```

Plot `temperature` and `setpoint`. The heater starts at full power, and the furnace settles at 60 °C in about 30 s, with `power` at about 50 %. In the **Queue** tab, **Control** runs the PID, with its latest value, output and error, and **Main** is free for anything else.

Then, in the **Instruments** tab, send `pid`'s `set_setpoint` with **Celsius** 80: the furnace settles there in about 25 s, at about 75 %. When the experiment ends, the PID sets the power to 0.

**More:** [the Queue tab](../reference/interface.md#the-dock), and [when something goes wrong](../reference/tasks/pid.md#when-something-goes-wrong).
{ .gs-more }

</section>

</div>

</div>

</div>

## What you built

The furnace held at 60 °C, then at 80 °C:

<div class="gs-shot" markdown>

![The interface running hold.py: temperature rising from 20 to settle at the setpoint of 60 degrees C, then following a step of the setpoint to 80, and the Queue tab, where Main is idle and Control runs furnace, a PID holding 80.0, with setpoint 80, kp 5, ki 0.5, value 80.06, output 75.06 and error -0.06](../images/usage/pid/hold.png){ .pa-shot }

<span class="gs-pin" style="--x: 54.8%; --y: 23.6%">1</span>
<span class="gs-pin" style="--x: 92.3%; --y: 69.4%">2</span>
<span class="gs-pin" style="--x: 12.0%; --y: 62.2%">3</span>

</div>

<div class="gs-legend" markdown>

1. **A new setpoint.** Sent from the **Instruments** tab: the temperature follows it to 80 °C.
2. **The PID, on its own queue.** Its setpoint and gains, and the latest value, output and error.
3. **The main queue, free.** For sweeps and the rest, while the PID runs.

</div>

!!! success "Checkpoint"
    The temperature settles at 60 °C, with `power` at about 50 %, and the log says `[furnace] Holding 60.0 (period 1.0 s)`. The **Queue** tab has two queues: **Control**, running the PID, and **Main**, free. After `set_setpoint` with 80, the setpoint steps, and the temperature follows it there, at about 75 %.

??? failure "Something not working?"
    - **The experiment stops as it starts, with `Task group terminated due to an error: read and write must be functions.`** The PID was given a value, `furnace.temperature()`, instead of the query. Leave out the brackets.
    - **The PID stops with an error after a few cycles.** `read` or `write` failed five times in a row, which is `max_failures`: the log says why each time.
    - **A task queued on `control` never starts.** The PID never finishes, so nothing queued behind it runs. Queue other tasks on **Main**.

## What you learned

- `PID` holds a value at a setpoint, reading with `read` and writing with `write`, within `output_min` and `output_max`.
- A task that never finishes goes on a task manager of its own, from `add_task_manager`, so it starts with the experiment and the main queue stays free.
- Its `output`, `setpoint` and `error` are attributes, which a `lambda` measurement records.
- A small software instrument can change its settings from the interface while it runs.

Next: [Set the experiment's options](setting_up.md), such as where the data goes and how much the terminal says.
