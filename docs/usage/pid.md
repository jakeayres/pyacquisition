# Hold a temperature with PID

<p class="pa-meta" markdown="span">About 20 minutes · Needs [Getting Started](../getting_started/python_api.md)</p>

A temperature controller holds a temperature from a thermometer on its own inputs. The thermometer you trust is often somewhere else: on the sample, a resistor measured by a lock-in. PyAcquisition's `PID` task closes the loop through your computer: every second it reads that thermometer, and sets the controller's heater to bring it to a setpoint. In this tutorial you hold a sample at about 8 K this way, with the heater of a Lakeshore 350 and a RuOx thermometer measured by an SR830. The PID runs on a queue of its own, for the whole experiment, and you change its setpoint from the interface while it runs.

You write `hold.py`, a new experiment, in your `my-lab` project, beside `stage.py`: a simulated sample stage over a 4.2 K bath, with the Lakeshore's heater on it and the thermometer on the sample. The code uses the real `Lakeshore_350` and `SR_830` drivers, so on your rig only their addresses change.

<div class="gs" data-files="hold.py:versions" data-lines="26" data-term-lines="4" markdown>

<div class="gs-stage" markdown>

<div class="gs-notes" markdown>

<section class="gs-step" data-new-file markdown>

## Connect the lock-in and the Lakeshore

```python title="hold.py"
--8<-- "examples/usage/pid/hold_1.py"
```

The instruments are the real `SR_830` and `Lakeshore_350` drivers. In place of an address, each is given a connection of `stage`'s, which answers as the instrument would, from a model of the sample stage. On your rig, give each its address, such as `"GPIB0::8::INSTR"`, and leave `stage` out: nothing else in `hold.py` changes.

??? abstract "stage.py: the cryostat, simulated"
    Save this beside `hold.py`. It answers the messages the two drivers send, as the instruments would, and you don't need to read it.

    ```python title="stage.py"
    --8<-- "examples/usage/pid/stage.py"
    ```

**More:** [a driver given an open connection](../reference/python_api/instrument.md), and [Connect a real instrument](connect_instrument.md).
{ .gs-more }

</section>

<section class="gs-step" markdown>

## Read the thermometer's resistance

```python title="hold.py" hl_lines="1 5 21-38"
--8<-- "examples/usage/pid/hold_2.py"
```

The lock-in's sine output, 1 V through a 10 MΩ resistor, drives 100 nA through the thermometer, and X is the voltage across it. So its resistance is X over that current: `resistance()`. A RuOx's resistance rises as it cools, and reads about 1995 Ω here at 4.2 K. The Lakeshore records its own thermometer on the stage as `T`, a check.

**More:** [the SR 830's queries](../reference/instruments/sr_830.md), and [measurements with arguments](measurements.md#pass-a-choice-the-input-channel).
{ .gs-more }

</section>

<section class="gs-step" markdown>

## Hand the heater to the computer

```python title="hold.py" hl_lines="6 30-36 48-55 57-60"
--8<-- "examples/usage/pid/hold_3.py"
```

In open loop mode, the Lakeshore's output 1 gives its manual output and nothing else: its own control is out of the way. Range 3 sets the heater's scale, and `heater(percent)` sets the output within it. `teardown()` turns the range off, so the heater is off however the experiment ends. `heater`, the output the heater gets, is recorded. A Lakeshore 340 takes these same lines.

**More:** [the Lakeshore 350's commands](../reference/instruments/lakeshore_350.md).
{ .gs-more }

</section>

<section class="gs-step" markdown>

## Hold the resistance with a PID

```python title="hold.py" hl_lines="3 39-50 70-72"
--8<-- "examples/usage/pid/hold_4.py"
```

Every second, the `PID` reads `resistance`, and writes `heater`: the functions, with no brackets. Its setpoint is the resistance for the temperature you want, from the thermometer's calibration: 1650 Ω is about 8 K. More heat lowers a RuOx's resistance, so `inverted=True`. The gains are in percent per ohm. The period, 1 s, is several of the lock-in's 100 ms time constants, so each reading is a new one. The PID never finishes, so it has a queue of its own.

**More:** [`PID`'s settings](../reference/tasks/pid.md#settings), and [`add_task_manager`](../reference/python_api/experiment.md#pyacquisition.core.experiment.Experiment.add_task_manager).
{ .gs-more }

</section>

<section class="gs-step" markdown>

## Change the setpoint from the interface

```python title="hold.py" hl_lines="2-6 56 86-109"
--8<-- "examples/usage/pid/hold_5.py"
```

A PID made in code isn't in the interface, so a small [software instrument](software_instrument.md) puts it there. `Controls` has a query for the setpoint, and commands to set it and the gains, which change the PID's attributes. The PID reads them on every cycle, so a change takes effect at once. It is added as the instrument `pid`.

**More:** [changing settings while it runs](../reference/tasks/pid.md#changing-settings-while-it-runs).
{ .gs-more }

</section>

<section class="gs-step" data-result="[sample] Holding 1650.0 (period 1.0 s)" markdown>

## Run the experiment

```bash
uv run hold.py
```

Plot `R` and `setpoint`. The heater starts at full power, and the resistance settles at 1650 Ω in about 20 s, with `T` at 7.97 K and `heater` at about 32 %. In the **Queue** tab, **Control** runs the PID, and **Main** is free for anything else.

Then, in the **Instruments** tab, send `pid`'s `set_setpoint` with **Ohms** 1560: the sample settles at about 10.1 K in 10 s, at about 50 %. When the experiment ends, the PID sets the heater to 0, and `teardown()` turns its range off.

**More:** [the Queue tab](../reference/interface.md#the-dock), and [when something goes wrong](../reference/tasks/pid.md#when-something-goes-wrong).
{ .gs-more }

</section>

</div>

</div>

</div>

## What you built

The sample held at 1650 Ω, then at 1560 Ω:

<div class="gs-shot" markdown>

![The interface running hold.py: the thermometer's resistance falling from 1995 ohms to settle at the setpoint of 1650, then following a step of the setpoint to 1560, and the Queue tab, where Main is idle and Control runs sample, a PID holding 1560.0, with its setpoint, gains, value, output and error](../images/usage/pid/hold.png){ .pa-shot }

<span class="gs-pin" style="--x: 59.3%; --y: 31.5%">1</span>
<span class="gs-pin" style="--x: 90.4%; --y: 69.4%">2</span>
<span class="gs-pin" style="--x: 12.8%; --y: 62.2%">3</span>

</div>

<div class="gs-legend" markdown>

1. **A new setpoint.** Sent from the **Instruments** tab: the resistance follows it to 1560 Ω, and the sample warms to 10.1 K.
2. **The PID, on its own queue.** Its setpoint and gains, and the latest value, output and error.
3. **The main queue, free.** For sweeps and the rest, while the PID runs.

</div>

!!! success "Checkpoint"
    `R` settles at 1650 Ω, with `T` at about 7.97 K and `heater` at about 32 %, and the log says `[sample] Holding 1650.0 (period 1.0 s)`. The **Queue** tab has two queues: **Control**, running the PID, and **Main**, free. After `set_setpoint` with 1560, `R` follows the setpoint there, and `T` rises to about 10.1 K. When the experiment ends, the terminal says `The heater is off.`

??? failure "Something not working?"
    - **The heater stays at 0 %, and `R` at its cold value.** `inverted=True` is missing. Without it the PID takes a resistance above the setpoint to mean too hot, so it turns the heater off.
    - **`R` swings around the setpoint, and the heater with it.** The gains are too high for your cryostat: halve `kp` and `ki` with `set_gains`, and try again. A noisy reading does it too: give the lock-in a longer time constant, and the PID a period of a few of them.
    - **`heater` stays at 0 % while the PID's output isn't.** The Lakeshore's output isn't in open loop mode, or its range is off. Check `get_control_mode` and `get_heater_range` in the **Instruments** tab.
    - **The experiment stops as it starts, with `Task group terminated due to an error: read and write must be functions.`** The PID was given a value, `resistance()`, instead of the function. Leave out the brackets.
    - **A task queued on `control` never starts.** The PID never finishes, so nothing queued behind it runs. Queue other tasks on **Main**.

## What you learned

- `PID` holds a value at a setpoint, reading with `read` and writing with `write`, within `output_min` and `output_max`. `inverted=True` is for a value that falls as the output rises, as a RuOx's resistance does.
- Any reading can be the value: here a resistance, worked out from the lock-in's X. The setpoint is in its units.
- In open loop mode, a Lakeshore's heater does what the computer sets with `set_manual_output`, and `teardown()` turns it off at the end.
- A task that never finishes goes on a task manager of its own, and a small software instrument can change its settings from the interface.

Next: [Set the experiment's options](options.md), such as where the data goes and how much the terminal says.
