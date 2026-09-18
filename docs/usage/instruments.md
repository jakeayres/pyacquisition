# Adding Instruments

An **instrument** is a Python object that represents a device. It offers two kinds of function:

- **Queries** read something from the device: a voltage, a temperature, the time.
- **Commands** make the device do something: set a frequency, start a ramp.

Every function of every instrument is available in the interface under the **Instruments** menu, and can be used from your own code and from tasks.

## Instruments that are included

Instrument classes are imported from `pyacquisition.instruments`.

| Instrument | Type | Description |
|---|---|---|
| [`Clock`](../instruments/clock.md) | Software | Elapsed time and named timers. |
| `Calculator` | Software | A mock calculator (addition, trigonometry) that is mainly used to test the framework. |
| [`SR_830`](../instruments/sr_830.md), [`SR_860`](../instruments/sr_860.md) | Hardware | Stanford Research Systems lock-in amplifiers. |
| [`Lakeshore_340`](../instruments/lakeshore_340.md), [`Lakeshore_350`](../instruments/lakeshore_350.md) | Hardware | Lakeshore temperature controllers. |
| [`Mercury_IPS`](../instruments/mercury_ips.md) | Hardware | Oxford Instruments magnet power supply. |

If your device is not on the list, [write your own instrument class](custom_instruments.md). It takes a few lines.

## Adding software instruments

A software instrument needs nothing but an id. Add it in `setup()`:

```python
from pyacquisition import Experiment
from pyacquisition.instruments import Clock


class MyExperiment(Experiment):

    def setup(self):
        clock = Clock("clock")
        self.add_instrument(clock)
```

The id, `"clock"`, identifies the instrument everywhere: in the interface, in the API (`/clock/time`), and in your tasks. It must be different for every instrument, because a second instrument with the same id silently replaces the first. Also avoid ids that start with another id (such as `lockin` and `lockin2`), and the names the interface already uses: `rack`, `scribe`, `task_manager`, `tasks` and `experiment`.

## Adding hardware instruments

A hardware instrument also needs a connection to the device. Open the connection with `pyvisa` and pass it to the instrument along with its id.

```python
import pyvisa
from pyacquisition import Experiment
from pyacquisition.instruments import SR_830


class MyExperiment(Experiment):

    def setup(self):
        resource_manager = pyvisa.ResourceManager()
        resource = resource_manager.open_resource("GPIB0::7::INSTR", timeout=5000) # (1)!

        lockin = SR_830("lockin", resource) # (2)!
        self.add_instrument(lockin)
```

1. The address of your instrument, and how long (in milliseconds) to wait for it to respond.
2. Every hardware instrument class takes an id and an open resource.

To find the address of your instrument, list everything `pyvisa` can see:

```python
import pyvisa

print(pyvisa.ResourceManager().list_resources())
```

Vendor tools such as NI MAX also show addresses. If nothing is listed, see [VISA installation](installation.md#instrument-communication-visa).

!!! tip "Try it without hardware first"
    Build and test your whole experiment with software instruments such as the one in [Writing your own instrument](custom_instruments.md#a-software-instrument), then swap in the real one. Nothing else needs to change if the two have the same queries and commands.

## Using an instrument in your code

`self.instruments` is a read-only dictionary of everything you have added, keyed by id. Tasks use it to reach the instruments that they control:

```python
lockin = self.instruments["lockin"]
lockin.set_frequency(1000.0)
x = lockin.get_x()
```

Inside a task, the experiment is passed to you, so it is `experiment.instruments["lockin"]`. See [Writing tasks](tasks.md).

To remove an instrument again, call `self.remove_instrument("lockin")`. Like adding, this is only possible before the experiment starts running.

## Using an instrument from the interface

Open the **Instruments** menu. Each instrument has a submenu listing all of its queries and commands. Choose one, fill in any inputs, and press **Send Request**. The reply is shown in the same window.

Reading values continuously and saving them to file is done with a [measurement](measurements.md).
