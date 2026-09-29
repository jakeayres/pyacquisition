# Adding Instruments

An **instrument** is a Python object that represents a device. It offers two kinds of function:

- **Queries** read something from the device: a voltage, a temperature, the time.
- **Commands** make the device do something: set a frequency, start a ramp.

Every function of every instrument is available in the interface, in the **Instruments** tab, and can be used from your own code and from tasks.

## Instruments that are included

Instrument classes are imported from `pyacquisition.instruments`.

| Instrument | Type | Description |
|---|---|---|
| [`Clock`](../instruments/clock.md) | Software | Elapsed time and named timers. |
| [`RandomNumberGenerator`](../instruments/random_number_generator.md) | Software | Random numbers from the common probability distributions. Stands in for real hardware while you develop. |
| [`SignalGenerator`](../instruments/signal_generator.md) | Software | Waveforms (sine, square, triangle, chirp and more) computed from the time. |
| `Calculator` | Software | A mock calculator (addition, trigonometry) that is mainly used to test the framework. |
| [`SR_830`](../instruments/sr_830.md), [`SR_860`](../instruments/sr_860.md) | Hardware | Stanford Research Systems lock-in amplifiers. |
| [`Keithley_2000`](../instruments/keithley_2000.md) | Hardware | Keithley 6½-digit multimeter: volts, current, resistance, frequency, temperature, with an optional scanner card. |
| [`Keithley_6221`](../instruments/keithley_6221.md) | Hardware | Keithley AC and DC current source, with wave generator, sweeps and delta mode. |
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

A hardware instrument also needs the address of the device. Give it to the instrument along with its id, and the instrument opens the connection itself.

```python
from pyacquisition import Experiment
from pyacquisition.instruments import SR_830


class MyExperiment(Experiment):

    def setup(self):
        lockin = SR_830("lockin", "GPIB0::7::INSTR") # (1)!
        self.add_instrument(lockin)
```

1. Every hardware instrument class takes an id and an address. The connection is made here, so a wrong address stops the experiment during `setup()`, with an error that lists the addresses that were found.

### Choosing how to connect

By default the instrument connects with `pyvisa`. To connect another way, give the `adapter`. Any other options are passed on when the connection is opened.

```python
lockin = SR_830("lockin", "GPIB0::7::INSTR", timeout=10000)
cryostat = Lakeshore_350("lakeshore", "COM3::12", adapter="prologix")
```

| Adapter | Use it for | Address |
|---|---|---|
| `pyvisa` (the default) | GPIB, USB, serial and Ethernet instruments, through a VISA library | `GPIB0::7::INSTR` |
| `prologix` | GPIB instruments behind a [Prologix GPIB-USB controller](toml_config.md#instruments-behind-a-prologix-gpib-usb-controller) | `COM3::7` (serial port, then GPIB address) |
| `mock` | Running the instrument class with no device, to [develop without the hardware](toml_config.md#running-hardware-instruments-without-the-device) | anything |

The options are those of the adapter. For `pyvisa` and `prologix` they include `timeout` (in milliseconds, 5000 by default), `read_termination` and `write_termination`. For `mock` they include `responses`, the replies to give:

```python
thermometer = Lakeshore_350(
    "lakeshore", "mock", adapter="mock", responses={"KRDG? A": "4.2"}
)
```

### Connections are closed for you

A connection that an instrument opened is closed when the experiment ends, after your `teardown()` has run, so `teardown()` can still talk to the instrument. You do not need to close anything yourself.

If you would rather open the connection yourself, pass an open `pyvisa` resource instead of an address. The instrument uses it as it is, and closing it stays your job. `adapter` and the options only apply to an address.

### Finding the address

To find the address of your instrument, list everything `pyvisa` can see:

```python
import pyvisa

print(pyvisa.ResourceManager().list_resources())
```

Vendor tools such as NI MAX also show addresses. If nothing is listed, see [installing a VISA library](../getting_started/installation.md#real-instruments-later).

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

The choices that an instrument's queries and commands take, such as a channel or a range, are enums, and each instrument has them as attributes, so there is nothing to import:

```python
cryostat = self.instruments["lakeshore"]
cryostat.set_setpoint(cryostat.OutputChannel.OUTPUT_1, 4.2)
Measurement("T", cryostat.get_temperature, input_channel="INPUT_A") # (1)!
```

1. A [measurement](measurements.md#choices-such-as-a-channel) also takes the text that names a member.

To remove an instrument again, call `self.remove_instrument("lockin")`. Like adding, this is only possible before the experiment starts running. The experiment no longer looks after the instrument, so it does not close its connection. Call `close()` on the instrument if you are done with it.

## Using an instrument from the interface

Open the **Instruments** tab. Pick an instrument to list all of its queries and commands, pick one, fill in any inputs, and press **Read** (or **Send**, for a command). The reply is shown beside the form, with the replies before it. ++ctrl+k++ finds any of them from anywhere, and takes their inputs on the same line: `clock read_timer lap` and ++enter++ reads the clock's timer `lap`.

**Add to queue**, beside **Read** or **Send**, queues the call instead, with the inputs in the form, to run in its turn after the tasks already queued. A query's reply is then logged, and shown in the **Queue** tab as the last result: `Last: lakeshore.get_temperature completed → 4.21`. A queue holding calls can be saved as a sequence, like any other.

Reading values continuously and saving them to file is done with a [measurement](measurements.md).
