# Writing Your Own Instrument

A driver for a device that isn't among the [included instruments](instruments.md#instruments-that-are-included) is a class of your own, with a method for each thing to read or set. [Write a software instrument](software_instrument.md) shows the shape of one, a step at a time: the class, its queries and commands, and its choices. A driver for hardware is written the same way, as below.

## A hardware instrument

A hardware instrument is written as [a software instrument](software_instrument.md) is, with two differences. The class inherits from `Instrument`, and it receives an open connection to the device. Use `self.query()` to ask the device something and get its reply, and `self.command()` to send something without expecting a reply.

```python title="my_thermometer.py" linenums="1"
from pyacquisition.core.instrument import Instrument, mark_command, mark_query


class MyThermometer(Instrument):
    """A temperature controller."""

    name = "My Thermometer"

    @mark_query
    def get_temperature(self) -> float:
        """Read the temperature in kelvin."""
        return float(self.query("KRDG? A")) # (1)!

    @mark_command
    def set_setpoint(self, kelvin: float = 300.0) -> None:
        """Set the temperature setpoint in kelvin."""
        self.command(f"SETP 1,{kelvin}") # (2)!
```

1. `self.query()` sends the text to the device and returns its reply as text, so convert it to the type you promised.
2. `self.command()` sends the text and returns nothing.

The strings sent are whatever your instrument's manual says. Create it just like any [hardware instrument](instruments.md#adding-hardware-instruments):

```python
thermometer = MyThermometer("thermometer", resource)
self.add_instrument(thermometer)
```

## A trace method

A query gives one number. A method that gives a whole array (a spectrum, a sweep, a capture buffer) is a **trace method**, for a [trace](traces.md). Mark it with `@mark_trace`, and return a `TraceData`: the channels, by name, and the axis they are over.

```python title="my_analyser.py" linenums="1"
import numpy as np

from pyacquisition import TraceData
from pyacquisition.core.instrument import Instrument, mark_trace


class MyAnalyser(Instrument):
    """A spectrum analyser."""

    name = "My Analyser"

    def start_sweep(self) -> None:
        self.command("INIT") # (1)!

    def sweep_done(self) -> bool:
        return self.query("SWE:DONE?").strip() == "1"

    def stop_sweep(self) -> None:
        self.command("ABOR")

    @mark_trace(
        start="start_sweep",
        ready="sweep_done",
        stop="stop_sweep",
        timeout=120,
        channels=["power"],
    ) # (2)!
    def get_spectrum(self) -> TraceData:
        """Read the spectrum, in dBm."""
        values = np.array(self.query("TRAC? TRACE1").split(","), dtype=float)
        start = float(self.query("FREQ:STAR?"))
        stop = float(self.query("FREQ:STOP?"))
        return TraceData(
            {"power": values},
            x=(start, stop), # (3)!
            x_name="frequency",
            x_unit="Hz",
            unit="dBm",
        )
```

1. The commands are whatever your instrument's manual says. These are made up.
2. The **phases** of a trace that takes time: `start` is called first, then `ready` every 0.1 s until it is true, then the method itself fetches the trace. If the trace is cancelled (its task is aborted, or the experiment stops) or takes longer than `timeout` seconds, `stop` is called, so the instrument isn't left sweeping. A trace that is ready at once needs none of them: `@mark_trace` alone.
3. A linear axis is given by its ends, which is all the file keeps of it. For any other axis, give its value at every point, as an array as long as the channels.

- **`channels`** names the channels the traces have, so that their [reductions'](traces.md#reductions) columns are known before the first trace is taken. For channels that depend on a setting, give the name of a method that returns them instead of a list.
- **Several channels** (an `X` and a `Y`, say) are several entries in the dict, all as long as each other.
- **Inputs.** The trace method and its phases can take inputs, which are given to `Trace` as keyword arguments: `Trace("spectrum", analyser.get_spectrum, span=1e6)` passes `span` to each phase that has a parameter of that name.
- **A phase can be `async`.** It is awaited.
- **Trace methods don't appear in the Instruments tab.** They are taken as traces, with **Acquire now** and the rest.
