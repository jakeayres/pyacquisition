# 7. Real Instruments

<p class="pa-meta" markdown="span">About 10 minutes · Needs [lesson 5](building_a_sweep.md) · Needs the instruments</p>

Everything so far ran against a stand-in. In this lesson you will point the same experiment at a real SR 830 lock-in amplifier and a real Lakeshore 350 temperature controller. Because the simulated instruments have the same queries and commands as the real ones, **it is a two-line change**. Your measurements, calculation and tasks do not change at all.

!!! warning "Read the safety notes before you run a task"
    A task drives real hardware: it changes a setpoint and a ramp rate on a temperature controller connected to a heater. Read [Before you run a task](#before-you-run-a-task) below before you queue one.

## Connect to the instruments

Instruments are usually controlled through **VISA**. `pyvisa` is installed with `pyacquisition`, and it talks to your hardware through a *VISA library* (for example the one that comes with NI-VISA). If you have not installed one yet, see [VISA in the installation page](installation.md#instrument-communication-visa).

Every instrument has an **address**, such as `GPIB0::7::INSTR`. To see what `pyvisa` can find, run this once:

```python
import pyvisa

print(pyvisa.ResourceManager().list_resources())
```

Vendor tools such as NI MAX show the same addresses. Note down the address of each instrument. In the examples below they are `GPIB0::7::INSTR` for the lock-in and `GPIB0::12::INSTR` for the temperature controller, so use your own.

## Swap them in

Two things change: the import, and the two lines in `setup()` that create the instruments. The import is one line, and it replaces the import of `simulated.py`, which is no longer needed:

```python
from pyacquisition.instruments import SR_830, Clock, Lakeshore_350
```

The instruments themselves:

<div class="pa-annot" data-source="examples/tutorial/step_7_real_instruments.py:instruments" markdown>

<div class="pa-ide" markdown>

```python title="my_experiment.py" linenums="1" hl_lines="1-2 4-5"
--8<-- "examples/tutorial/step_7_real_instruments.py:instruments"
```

</div>

<div class="pa-annot__notes" markdown="0">
<div class="pa-note" style="--from: 1; --to: 2" data-contains="Lakeshore_350"><b>The temperature controller</b><span>An id and an address. It opens its own connection, so there is no <code>pyvisa</code> code to write.</span></div>
<div class="pa-note" style="--from: 4; --to: 5" data-contains="SR_830"><b>The lock-in</b><span>The same two arguments. Nothing after this changes.</span></div>
</div>

</div>

Every hardware instrument class takes an id and an address, in that order. Here is the complete file, if you want to compare it with yours:

??? example "The complete my_experiment.py, with real instruments"

    ```python title="my_experiment.py" linenums="1" hl_lines="5 93 96"
    --8<-- "examples/tutorial/step_7_real_instruments.py"
    ```

Everything else is the same: the `id`s are still `"lockin"` and `"lakeshore"`, so `SetTemperature` still finds them with `experiment.instruments["lakeshore"]`; the measurements still call `get_x`, `get_y` and `get_temperature`; `RecordAt` and `TemperatureSweep` are untouched.

That is the whole point of writing against instruments that have a common interface: you built and debugged the experiment on a desk, and moved it to the lab by changing where the instruments come from.

### If it cannot connect

A wrong address stops the experiment during `setup()` with an error that names the address and lists what was found:

```text
ConnectionError: Could not open 'GPIB0::12::INSTR' with the pyvisa adapter: VI_ERROR_RSRC_NFOUND ... Available resources: GPIB0::7::INSTR.
```

Compare it with the address you noted down, and check that the instrument is on and connected.

### Other kinds of connection

`pyvisa` is used unless you say otherwise. Give `adapter` to reach an instrument another way, and any options `pyvisa` accepts, such as `timeout` (in milliseconds, 5000 by default):

```python
cryostat = Lakeshore_350("lakeshore", "COM3::12", adapter="prologix")
lockin = SR_830("lockin", "GPIB0::7::INSTR", timeout=10000)
```

See [Adding hardware instruments](instruments.md#adding-hardware-instruments) for the adapters.

## Check it before you trust it

Run it without any tasks first.

1. **Just measure.** Comment out the three `register_task` lines, and run the experiment. Look at the **Values** tab and compare each number with the instrument's own display. Does `T` match the front panel? Is `x` what the lock-in shows?
2. **Try a query and a command by hand.** Use the **Instruments** tab, exactly as in [lesson 2](simulated_rig.md#talk-to-an-instrument). Query first, and change only harmless settings.
3. **Then a small task.** Put the tasks back, and queue **Set Temperature** for a temperature a degree or two from where you are, with a gentle `ramp_rate`.

Real instruments differ from the simulation in ways it cannot warn you about. A real temperature controller responds slowly and overshoots, a real lock-in has a sensitivity and a time constant that you must set for your signal (both are commands in the **Instruments** tab), and a real sample is noisier.

## Before you run a task

`SetTemperature` sets a ramp rate and a setpoint on **Output 1** of the controller. That is the right thing to do only if your controller is configured for it.

- **Check the output.** `OutputChannel.OUTPUT_1` must be the loop that controls your sample. If it is not, change it in the task.
- **Know what can be queued.** A task that comes with an instrument, here **Ramp Temperature** for the Lakeshore, is registered for you when the instrument is in the experiment, so it is in **Add task** without you writing anything. Like `SetTemperature`, it changes the ramp rate and the setpoint of the output you name, so treat it the same way. To keep it out, set `auto_tasks = False` in your experiment class (see [tasks that are already included](tasks.md#tasks-that-are-already-included)).
- **Check the limits.** The controller has its own setpoint limits and heater ranges. Set them to suit your cryostat, and do not rely on the task to protect the hardware. A task does exactly what you wrote.
- **Choose a safe `ramp_rate`.** The `30` in the example is a kelvin per minute that suits the simulation, not your cryostat. Use a rate your system tolerates.
- **Test `teardown()` on the real thing.** Abort a task on purpose, and check that the instrument ends up somewhere you are happy with. [Lesson 6](queueing_tasks.md) shows how.

## Verify your instruments

`pyacquisition` includes a verification tool that runs each supported instrument's queries and commands against real hardware and checks the replies, with read-only and reversible modes. Use it when you set up a new instrument. See [Verifying hardware](../dev/verifying_hardware.md).

!!! success "Checkpoint"
    With the real instruments connected, the **Values** tab shows the temperature and lock-in readings you see on the instruments themselves, and **lakeshore** and **lockin** in the **Instruments** tab list the same queries and commands you used in the simulation.

## What you learned

- Real and simulated instruments with the same queries and commands are interchangeable. Move an experiment to hardware by changing where the instruments come from.
- A hardware instrument is made from an id and an address. It opens its own connection, and the experiment closes it when it ends.
- Test hardware in stages: measure only, then queries and commands by hand, then tasks.
- A task does exactly what you wrote. Check limits, output channels and ramp rates for your hardware.

## Where to go next

You have built and run a real, automated experiment. The rest of the documentation goes deeper:

- **Instruments that are not included.** [Write your own instrument](custom_instruments.md). It takes a few lines.
- **Feedback control.** The included [PID task](../tasks/pid.md) holds a quantity at a setpoint.
- **Configuration files.** [TOML configuration](toml_config.md) describes an experiment without writing any Python.
- **Everything about tasks.** [Writing](tasks.md), [composing](composing_tasks.md) (including running tasks at the same time) and [running](running_tasks.md) tasks.
- **The whole of Advanced Usage.** [The overview](advanced.md) lists every page, grouped by topic.
- **Calculations.** [Rolling means, sums and your own](calculations.md).
- **Running headless, and the API.** [The interface and the API](running.md).
- **The reference.** Every instrument, task and class is documented from its docstrings: see the [Experiment API](../experiment/experiment.md), [Instruments](../instruments/overview.md) and [Tasks](../tasks/overview.md) sections.
