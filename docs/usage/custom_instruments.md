# Writing Your Own Instrument

The list of [included instruments](instruments.md#instruments-that-are-included) is far from exhaustive, so you will probably want to write your own. It is quick to do:

1. Write a class that inherits from `SoftwareInstrument` (no hardware) or `Instrument` (a hardware device).
2. Mark the methods you want to expose with `@mark_query` (reads something) or `@mark_command` (does something).
3. Add an instance to your experiment.

The marked methods appear in the interface and the API automatically.

## A software instrument

A software instrument is not connected to anything. It is useful for things like timers and calculations, and for standing in for real hardware while you develop your experiment. Here is a random number generator, which we will use for the rest of this guide. It can draw its numbers from a Gaussian or a uniform distribution, and you choose which with a command.

Save this in a file called `random_number_generator.py`, next to `my_experiment.py`:

```python title="random_number_generator.py" linenums="1"
import random

from pyacquisition.core.instrument import SoftwareInstrument, mark_command, mark_query


class RandomNumberGenerator(SoftwareInstrument):
    """A software random number generator with a choice of distribution."""

    name = "Random Number Generator" # (1)!

    def __init__(self, uid):
        super().__init__(uid) # (2)!
        self._distribution = "gaussian"
        self._parameters = (0.0, 1.0)

    @mark_command # (3)!
    def use_gaussian(self, mean: float = 0.0, sigma: float = 1.0) -> None: # (4)!
        """Draw numbers from a Gaussian distribution.""" # (5)!
        self._distribution = "gaussian"
        self._parameters = (mean, sigma)

    @mark_command
    def use_uniform(self, low: float = 0.0, high: float = 1.0) -> None:
        """Draw numbers uniformly between low and high."""
        self._distribution = "uniform"
        self._parameters = (low, high)

    @mark_query
    def get_distribution(self) -> str:
        """Get the name of the distribution that is in use."""
        return self._distribution

    @mark_query
    def random_number(self) -> float:
        """Draw one random number from the current distribution."""
        if self._distribution == "gaussian":
            return random.gauss(*self._parameters)
        return random.uniform(*self._parameters)
```

1. A readable name for the instrument.
2. `SoftwareInstrument.__init__` takes the instrument's id. Pass it on.
3. A **command** changes the state of the instrument.
4. Type hints on the arguments are required. The interface uses them to validate input and to choose the right kind of input box.
5. The docstring is shown in the interface as the description of the function.

Now add it to the experiment, and record its numbers. Make these changes to `my_experiment.py`:

```python title="my_experiment.py" linenums="1" hl_lines="3 13 15 18"
from pyacquisition import Experiment, Measurement
from pyacquisition.instruments import Clock
from random_number_generator import RandomNumberGenerator


class MyExperiment(Experiment):

    def __init__(self):
        super().__init__(data_path="my_data")

    def setup(self):
        clock = Clock("clock")
        rng = RandomNumberGenerator("rng")
        self.add_instrument(clock)
        self.add_instrument(rng)

        self.add_measurement(Measurement("time", clock.time))
        self.add_measurement(Measurement("random", rng.random_number))


if __name__ == "__main__":
    MyExperiment().run()
```

Run it. **Instruments → rng** now includes **Use Gaussian**, **Use Uniform**, **Get Distribution** and **Random Number**, and the **Live Data** window shows `random` changing on every cycle. Choose **Use Uniform**, enter a `low` of `10` and a `high` of `20`, and press **Send Request**. From then on `random` stays between 10 and 20.

## A hardware instrument

The process for a hardware instrument is the same, with two differences. The class inherits from `Instrument`, and it receives an open connection to the device. Use `self.query()` to ask the device something and get its reply, and `self.command()` to send something without expecting a reply.

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

## Rules for queries and commands

- **Mark every method you want exposed.** Unmarked methods are ordinary Python methods. They still work in your own code, but do not appear in the interface.
- **Type hints on every argument are required.** Use `int`, `float`, `str` or `bool` for the arguments.
- **Docstrings are strongly recommended.** They are shown in the interface next to the function.
- **Return plain Python values** (`float`, `int`, `str`, `bool`) from queries you intend to record.
- **Queries should not change the instrument, and commands should.** Nothing enforces this, but it makes your instrument predictable to use. Queries are what you record with [measurements](measurements.md).
- **Default values are used when you call the method from Python.** The interface currently starts its input boxes at `0`, empty or `False`, whatever the default is.
- **Keep queries quick.** Measurements run one after another on every cycle, so a slow query slows the whole experiment down.
