# Hold a temperature with PID

<p class="pa-meta" markdown="span">About 20 minutes · Needs [Getting Started](../getting_started/python_api.md), and a lock-in and a Lakeshore 340 or 350 on your cryostat</p>

A temperature controller holds a temperature from a thermometer on its own inputs. The thermometer you trust is often somewhere else: on the sample, a resistor measured by a lock-in. PyAcquisition's `PID` task closes the loop through your computer: every second it reads that thermometer, and sets the controller's heater to bring it to a setpoint. In this tutorial you write the experiment that does it, with a RuOx thermometer measured by an SR830 and the heater on a Lakeshore 350's output 1. The PID runs on a queue of its own, for the whole experiment, and you change its setpoint and gains from the interface while it runs.

You write `hold.py`, a new experiment, in your `my-lab` project. Change the addresses, the excitation current and the setpoint to your own. Check each step on your cryostat before the next: the PID relies on all of them.

<div class="gs" data-files="hold.py:versions" data-lines="26" data-term-lines="4" markdown>

<div class="gs-stage" markdown>

<div class="gs-notes" markdown>

<section class="gs-step" data-new-file markdown>

## Connect the lock-in and the Lakeshore

```python title="hold.py"
--8<-- "examples/usage/pid/hold_1.py"
```

The instruments are the `SR_830` and `Lakeshore_350` drivers, at their addresses on your rig. Run it, and check that both answer in the **Instruments** tab: `lockin`'s `get_x`, and `lakeshore`'s `get_temperature`. With a Lakeshore 340, use `Lakeshore_340`: every line of this tutorial works with it too.

**More:** [Connect a real instrument](connect_instrument.md), to find the addresses.
{ .gs-more }

</section>

<section class="gs-step" markdown>

## Read the thermometer's resistance

```python title="hold.py" hl_lines="1 4-6 21-38"
--8<-- "examples/usage/pid/hold_2.py"
```

The lock-in's sine output, 1 V through a 10 MΩ resistor, drives 100 nA through the thermometer, and X is the voltage across it. So its resistance is X over that current: `resistance()`. Set `EXCITATION` for your own circuit, and a sensitivity that suits the voltage. The Lakeshore records its own thermometer on the stage as `T`. With the heater off, check `R` against the thermometer's calibration at that temperature, before a PID relies on it.

**More:** [the SR 830's queries](../reference/instruments/sr_830.md), and [measurements with arguments](measurements.md#pass-a-choice-the-input-channel).
{ .gs-more }

</section>

<section class="gs-step" markdown>

## Hand the heater to the computer

```python title="hold.py" hl_lines="7 30-37 49-56 58-61"
--8<-- "examples/usage/pid/hold_3.py"
```

In open loop mode, the Lakeshore's output 1 gives its manual output and nothing else, and `heater(percent)` sets it. Choose the range whose power suits your heater and stage. `teardown()` turns the range off, so the heater is off however the experiment ends. Before a PID drives it, try it by hand: send `lakeshore`'s `set_manual_output` with a few percent from the **Instruments** tab, and watch `heater` rise and `R` fall.

**More:** [the Lakeshore 350's commands](../reference/instruments/lakeshore_350.md).
{ .gs-more }

</section>

<section class="gs-step" markdown>

## Hold the resistance with a PID

```python title="hold.py" hl_lines="3 40-51 71-73"
--8<-- "examples/usage/pid/hold_4.py"
```

Every second, the `PID` reads `resistance`, and writes `heater`: the functions, with no brackets. Its setpoint is the resistance at the temperature you want, from the thermometer's calibration. More heat lowers a RuOx's resistance, so `inverted=True`. The gains are in percent per ohm: a start, to tune. Keep the period to several of the lock-in's time constants, so each reading is a new one, and `output_max` to what your heater can take. The PID never finishes, so it has a queue of its own.

**More:** [`PID`'s settings](../reference/tasks/pid.md#settings), and [`add_task_manager`](../reference/python_api/experiment.md#pyacquisition.core.experiment.Experiment.add_task_manager).
{ .gs-more }

</section>

<section class="gs-step" markdown>

## Change the setpoint and gains from the interface

```python title="hold.py" hl_lines="2-6 57 87-110"
--8<-- "examples/usage/pid/hold_5.py"
```

A PID made in code isn't in the interface, so a small [software instrument](software_instrument.md) puts it there. `Controls` has a query for the setpoint, and commands to set it and the gains, which change the PID's attributes. The PID reads them on every cycle, so a change takes effect at once, which is what tuning needs. It is added as the instrument `pid`.

**More:** [changing settings while it runs](../reference/tasks/pid.md#changing-settings-while-it-runs).
{ .gs-more }

</section>

<section class="gs-step" data-result="[sample] Holding 1650.0 (period 1.0 s)" markdown>

## Run it, and tune the gains

```bash
uv run hold.py
```

Plot `R`, `setpoint` and `heater`. How fast `R` settles, and at what heater output, depends on your cryostat. To tune, send `pid`'s `set_gains` from the **Instruments** tab while it runs: set `ki` to 0, and raise `kp` until `R` starts to swing around the setpoint, then halve it. Then raise `ki` until `R` settles on the setpoint without overshooting far. Put the gains you settle on in `hold.py`.

**More:** [how the PID works](../reference/tasks/pid.md#how-it-works), and [when something goes wrong](../reference/tasks/pid.md#when-something-goes-wrong).
{ .gs-more }

</section>

</div>

</div>

</div>

!!! success "Checkpoint"
    With the heater off, `R` matches the thermometer's calibration at `T`, and a few percent set by hand lowers it. With the PID running, the log says `[sample] Holding 1650.0 (period 1.0 s)`, and `R` settles on the setpoint, and follows it when you send a new one. The **Queue** tab has two queues: **Control**, running the PID, and **Main**, free. When the experiment ends, the PID sets the heater to 0, and the terminal says `The heater is off.`

??? failure "Something not working?"
    - **The heater stays at 0 %, and `R` at its cold value.** `inverted=True` is missing. Without it the PID takes a resistance above the setpoint to mean too hot, so it turns the heater off.
    - **`R` swings around the setpoint, and the heater with it.** The gains are too high for your cryostat: halve `kp` and `ki` with `set_gains`. A noisy reading does it too: give the lock-in a longer time constant, and the PID a period of a few of them.
    - **`heater` stays at 0 % while the PID's output isn't.** The Lakeshore's output isn't in open loop mode, or its range is off. Check `get_control_mode` and `get_heater_range` in the **Instruments** tab.
    - **The experiment stops as it starts, with `Task group terminated due to an error: read and write must be functions.`** The PID was given a value, `resistance()`, instead of the function. Leave out the brackets.
    - **A task queued on `control` never starts.** The PID never finishes, so nothing queued behind it runs. Queue other tasks on **Main**.

## What you learned

- `PID` holds a value at a setpoint, reading with `read` and writing with `write`, within `output_min` and `output_max`. `inverted=True` is for a value that falls as the output rises, as a RuOx's resistance does.
- Any reading can be the value: here a resistance, worked out from the lock-in's X. The setpoint is in its units.
- In open loop mode, a Lakeshore's heater does what the computer sets with `set_manual_output`, and `teardown()` turns it off at the end.
- A task that never finishes goes on a task manager of its own, and a small software instrument can change its settings, to tune it while it runs.

Next: [Set the experiment's options](options.md), such as where the data goes and how much the terminal says.
