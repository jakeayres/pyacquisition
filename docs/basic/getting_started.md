# Getting Started

The following is a complete step-by-step guide to setting up an experiment. In this walkthrough, we shall: 

1. Initialize a basic experiment
2. Add software (`Clock`) and hardware (`SR_830` lock-in) instruments
3. Add measurements (time and voltages) that are saved to a file
4. Write a custom instrument class (software random number generator)
5. Write a `Task` to automate our experimental procedure

in only a few dozen lines of code. A feature-full GUI allowing you to control the instruments, run your `Task` and visualize the live data will be automatically generated.

It is hoped that the `pyacquisition` API is sufficiently simple that this walkthrough and example code adequately illustrates how to proceed with your own experiment. More verbose descriptions of each step in the code can be found in **:material-plus-circle: annotations** . Where certain internal design choices impose specific and non-obvious requirements, a **:material-pencil-circle: note** can be found under the code.


## Experiment configuration

Getting started is as simple as composing a `.toml` configuration file and instantiating an `Experiment` using the `Experiment.from_config()` classmethod. All of the in-build functionality of `pyacquisition` can be configured via this method. 

### Configuration

A simple configuration file that loads a software `Clock` and a Stanford Research Systems `SR_830` lock-in amplifier on GPIB address 7 might look like:

```toml title="my_configuration_file.toml linenums="1""
[experiment]
root_path = "C://data"

[data]
path = "my_data_folder"

[instruments]
clock = {instrument = "Clock"}
lockin = {instrument = "SR_830", adapter = "pyvisa", resource = "GPIB0:7:INSTR"}

[measurements]
time = {instrument = "clock", method = "timestamp_ms"}
voltage = {instrument = "lockin", method = "get_x"}
```

The full list of configurable keys is available [under the configation submenu](configuration.md).

### Execution

A short `python` script for initializing and running your experiment might look like:

```python title="experiment_script.py linenums="1""
from pyacquisition import Experiment

my_experiment = Experiment.from_config('my_configuration_file.toml')
my_experiment.run()
```

which can be run directly with python (`python experiment_script.py`) or using a dependency manager like `uv` (`uv run experiment_scripy.py`).

Voila! A user interface should be running and recording a stream of timestamped voltages as comma separated values in `C://data/my_data_folder`. All of the functionality of each instrument is available from the top menu. If all you require is recording timestamped voltages, you may already by content. You can change file, control your lock-in amplifier, visualize the live data via the automatically populated menus.


## Custom Instruments

`pyacquisition` has implemented classes for a number of common instruments. The list is far from exhaustive. It is anticipated that you will need to write your own class that harnesses the functionality of your instrument. The process is simple. An outline of the workflow is as follows:

1. Compose your instrument inhereting from `Instrument` or `SoftwareInstrument`
2. Mark your public methods with either `@mark_command` or `@mark_query`
3. Add the instrument in `your_experiment.setup()`

### Example software instrument

Here we will run through the creation of an example software instrument (inheretting from `SoftwareInstrument`) -- a random number generator -- that illustrates how to implement your own instrument classes. The process for hardware instruments is the same except you need to inheret from the `Instrument` class.

Inheret from `SoftwareInstrument` and mark your query methods (methods that return values from your instrument) with the `@mark_query` decorator and command methods with the `@mark_command` decorator. We will write this into a new file named `random_number_generator.py` for import into this experiment and any others that may use it.

```python title="random_number_generator.py" linenums="1"
from pyacquisition import SoftwareInstrument
import random

class RandomNumberGenerator(SoftwareInstrument):
    """ A software random number generator instrument
    """

    @mark_query
    def random_number() -> float:
        """ Generate a random float in [0, 1]
        """
        return random.random()

    @mark_query
    def random_integer(minimum: int, maximum: int) -> int:
        """Generate a random integer within a specified range.
        """
        return random.randint(minimum, maximum)
```

!!! Notes
    **Type hints are mandatory.** `pyacquisition` uses type hints for both data validation and the generation of appropriate GUI widgets and are therefore non-optional on all `@mark_query` and `@mark_command` methods.
    
    **Default values are optional, but preferred.** Default values are not required, but are used to prepopulate the GUI widgets with default values. We suggest that sensible defaults are always provided to mitigate against undesired (erroneous/null) user inputs.
    
    **Docstrings are optional, but preferred.** The docstring is not strictly requried but is used in the GUI as a helpful descriptive label if provided. We suggest that they are used.


### Add the instrument to your experiment

To add the instrument to your experiment, you need to create your own experiment class that inherets from `Experiment`. The `Experiment` class has `setup()` and `teardown()` methods that are called upon starting and ending your experiment respectively. Add the instrument within the `setup()` method. If needed, any cleanup code can be added to `teardown()`.

```python title="my_experiment.py" linenums="1" hl_lines="2 4-9 14-15"
from pyacquisition import Experiment
from .random_number_generator import RandomNumberGenerator

class MyExperiment(Experiment):

    def setup(self):

        rng = RandomNumberGenerator('rng')
        self.rack.add_instrument(rng)


if __name__ == "__main__":

    my_experiment = MyExperiment.from_config('experiment_config.toml')
    my_experiment.run()
```

!!! Notes
    The first argument when instantiating instruments must be a **unique** string. This string will be used by both users (e.g. when composing tasks to automate experimental procedures) and the internals of `pyacquisition`. An error will be raised if two instruments with the same id are added to the experiment.

You can see that your instrument named `"rng"` is now available under the "Instruments" menu. All of the methods marked with `@mark_query` and `@mark_command` are accessible with automatically generated gui widgets.

### Add measurements

Whilst your instrument is now fully controllable via the GUI, you will probably want to poll one or many of the instruments query methods and save the data to file. To do this, you need to add a `Measurement` to the experiment. This can also be done in the `setup()` method of your experiment.

```python title="my_experiment.py" linenums="1" hl_lines="1 11-12"
from pyacquisition import Experiment, Measurement
from .random_number_generator import RandomNumberGenerator

class MyExperiment(Experiment):

    def setup(self):

        rng = RandomNumberGenerator('rng')
        self.rack.add_instrument(rng)

        rng_measurement = Measurement('random', rng.random_number) # (1)!
        self.rack.add_measurement(rng_measurement) # (2)!


if __name__ == "__main__":

    my_experiment = MyExperiment.from_config('experiment_config.toml')
    my_experiment.run()
```

1. Instantiate a new `Measurement` object named `random` that polls `rng.random_number`, the first method that we wrote in our `RandomNumberGenerator` class. Ensure that you are passing the method itself and not passing the return value of the method (by accidentally calling the method).
2. Pass the instantiated `Measurement` object to `self.rack.add_measurement()` to add the measurement to your experiment. 

!!! Notes
    **Pass a method to `Measurement()`** and not a value returned by the method. The measurement expects to receive a `callable`, namely a method of your instrument class. Do not call, the method. Pass the method itself.

In the above, we have added a measurement labelled "random" which polls `rng.random_number`. When run, you can see "random" and a live stream of random numbers in the "Live Data" window in the GUI. This is being saved to the active data file.

### Adding measurements with `kwargs`

If you would like to poll an instruments method that takes arguments, simply pass them as keyword arguments (received internally as `**kwargs`) when initializing the relevant `Measurement` object. These keyword arguments will be used with each function call.

```python title="my_experiment.py" linenums="1" hl_lines="14-15"
from pyacquisition import Experiment, Measurement
from .random_number_generator import RandomNumberGenerator

class MyExperiment(Experiment):

    def setup(self):

        rng = RandomNumberGenerator('rng')
        self.rack.add_instrument(rng)

        rng_measurement = Measurement('random', rng.random_number)
        self.rack.add_measurement(rng_measurement)

        another_rng_measurement = Measurement('random_int', rng.random_int, minimum=-10, maximum=10)
        self.rack.add_measurement(another_rng_measurement)


if __name__ == "__main__":

    my_experiment = MyExperiment.from_config('experiment_config.toml')
    my_experiment.run()
```
We have instantiated the second measurement with the two keywork arguments of `rng.random_int` such that a stream of random numbers between -10 and 10 are being recorded in your experiment.


## Tasks

We assume that you are very likely to want to automate aspects of your experimental procedure. For example, you may want to sweep the excitation frequency between two user provided values at a number of select excitation amplitudes with the data being saved to clearly labelled files. This can be accomplished using a `Task`.


### Adding a `Task`

A number of generic tasks have been added to `pyacquisition`. Browse through them [either here](../tasks/overview.md) or under "Tasks" in the main menu at the top of this page. Adding them to your experiment is as simple as calling `register_task()` in the `setup()` method of your experiment:

```python title="my_experiment.py" hl_lines="2 18"
from pyacquisition import Experiment, Measurement
from pyacquisition.tasks import WaitFor # (1)!
from .random_number_generator import RandomNumberGenerator

class MyExperiment(Experiment):

    def setup(self):

        rng = RandomNumberGenerator('rng')
        self.rack.add_instrument(rng)

        rng_measurement = Measurement('random', rng.random_number)
        self.rack.add_measurement(rng_measurement)

        another_rng_measurement = Measurement('random_int', rng.random_int, minimum=-10, maximum=10)
        self.rack.add_measurement(another_rng_measurement)

        self.register_task(WaitFor) # (2)!


if __name__ == "__main__":

    my_experiment = MyExperiment.from_config('experiment_config.toml')
    my_experiment.run()
```

1. Import the `WaitFor` task from `pyacquisition.tasks`. All standard tasks are importable from this submodule.
2. Pass the `WaitFor` class to `register_task()` to register the task to your experiment.

!!! Notes
    **Pass the uninstantiated class to `register_task()`**. We need to pass the WaitFor class and *not* an instantiated object of type `WaitFor`. Pass the class itself, not an instantiated object.

You will see that "WaitFor" is now accessible from the "Tasks" menu in the GUI. Clicking it will open a GUI widget with a useful description, appropraite widgets for the various user-providable inputs and an execute button that adds the task to the experiment "Task Queue".


### Writing a new `Task`

The following shows a new `FreuencySweep(Task)` class that inherets from `Task`. Any parameters can be defined as required and optional attributes of your class. Tasks have three `async` methods `setup()`, `run()` and `teardown()` within which you can add functionality. The `setup()` and `teardown()` methods are simple `async` methods that are called before and after your task is run. `run()` is an `async` generator method.

```python title="experiment_script.py" linenums="1" hl_lines="1 5-33"
from pyacquisition import Experiment, Measurement, Task
from .random_number_generator import RandomNumberGenerator
import asyncio

class FrequencySweep(Task):
    # (1)!
    """Sweep the lock-in frequency at fixed excitation amplitude.
    """

    start_frequency: float # (2)!
    end_frequnecy: float
    amplitude: float = 1.0 # (3)!

    async def setup(self, experiment): # (4)!
        file_name = f"sweep_at_{self.amplitude:.2f}V"
        experiment.scribe.new_file(filename)

        lockin = experiment.rack.instruments['lockin']
        lockin.set_excitation(self.amplitude)
        lockin.set_frequency(self.start_frequency)

    async def run(self, experiment): # (5)!
        frequency = self.start_frequency
        yield f'Sweep starting at {frequency}'
        while frequency <= self.end_frequency:
            await asyncio.sleep(1)
            frequency += 0.1
            yield None # (6)!
        yield f'Sweep ended at {frequency}' 

    async def teardown(self, experiment): # (7)!
        lockin = experiment.rack.instruments['lockin']
        lockin.set_excitation(0)


class MyExperiment(Experiment):

    def setup(self):

        rng = RandomNumberGenerator('rng')
        self.rack.add_instrument(rng)

        rng_measurement = Measurement('random', rng.random_number)
        self.rack.add_measurement(rng_measurement)

        another_rng_measurement = Measurement('random_int', rng.random_int, minimum=-10, maximum=10)
        self.rack.add_measurement(another_rng_measurement)


if __name__ == "__main__":

    my_experiment = MyExperiment.from_config('experiment_config.toml')
    my_experiment.run()
```

1. The first line of the docstring will be used as a display message in the GUI.
2.  Required arguments can be added using type-hinted attributes of your class. Here, two have been added.
3.  Optional arguements can be added by using type-hinted attributes and providing a default value. Here, one has been added with a default value of `float 1.0`.
4.  --- To be completed ---
5.  --- To be completed ---
6.  Printing a log every second would be excessive. We will therefore return `None` in the main `while` loop.
7.  The lockin excitation amplitude is set to `0`.

!!! Notes
    **Provide a docstring for the class**. The first line of the docstring is used as the help text in the generated GUI widget for the task.

    **Type hints are mandatory.** Again, type hints are used for data validation and the rendering of appropriate widgets in the GUI. They are therefore mandatory for correct operation.

    **Default values are optional, but preferred.** Default values are not required, but are used to prepopulate the GUI widgets with default values. We suggest that sensible defaults are always provided to mitigate against undesired (erroneous/null) user inputs.

    **`teardown()` is always called**. This is true even in the cases when a task is aborted by the user mid execution or aborted abrupted when an error is raised. It can therefore be used to put instruments into a safe state.

    **The `run()` method must be an async generator method** i.e. must include yield statements. Whatever is yielded is simply logged. Internally, these provide the breakpoints at which the main asyncio event loop cedes control to other parts of the code and also where pause and abort flags are checked. Without any yield statements, your task will effectively be unpauseble and unabortable. If you do not wish to print any logs at each step, simply `yield None`.


In order to use the `FrequencySweep` task, it also needs to be registered to the experiment. This is done in the `setup()` method using the `register_task()` method:

```python title="experiment_script.py" linenums="1" hl_lines="46"
from pyacquisition import Experiment, Measurement, Task
from .random_number_generator import RandomNumberGenerator
import asyncio

class FrequencySweep(Task):

    start_frequency: float
    end_frequnecy: float
    amplitude: float = 1

    async def setup(self, experiment):
        file_name = f"sweep_at_{self.amplitude:.2f}V"
        experiment.scribe.new_file(filename)

        lockin = experiment.rack.instruments['lockin']
        lockin.set_excitation(self.amplitude)
        lockin.set_frequency(self.start_frequency)

    async def run(self, experiment):
        frequency = self.start_frequency
        yield f'Sweep starting at {frequency}'
        while frequency <= self.end_frequency:
            await asyncio.sleep(1)
            frequency += 0.1
            yield None
        yield f'Sweep ended at {frequency}' 

    async def teardown(self, experiment):
        lockin = experiment.rack.instruments['lockin']
        lockin.set_excitation(0)


class MyExperiment(Experiment):

    def setup(self):

        rng = RandomNumberGenerator('rng')
        self.rack.add_instrument(rng)

        rng_measurement = Measurement('random', rng.random_number)
        self.rack.add_measurement(rng_measurement)

        another_rng_measurement = Measurement('random_int', rng.random_int, minimum=-10, maximum=10)
        self.rack.add_measurement(another_rng_measurement)

        self.register_task(FrequencySweep) # (1)!


if __name__ == "__main__":

    my_experiment = MyExperiment.from_config('experiment_config.toml')
    my_experiment.run()
```

1. Pass the `FrequencySweep` class to `register_task()` to register the task to your experiment.

!!! Notes
    **Pass the uninstantiated class to `register_task()`**. We need to pass the FrequencySweep class and *not* an instantiated object of type `FrequencySweep`. Simply, don't put brackets after `FrequencySweep`.


You should now see that `FrequencySweep` is available under "Tasks" in the GUI. Clicking it should create a popup within which the experimental parameters `start_frequency`, `end_frequency` and `amplitude` can be provided. Submitting the form adds the task to the task queue for execution.


## Summary

In total, you have written:

- a simple `.toml` configuration file
- a ~20 line `Instrument` class with custom functionality
- a ~25 line `Task` class to automate your experimental procedure
- a ~15 line `Experiment` class connecting them together

and for free, you get a fully featured gui exposing all of the core functionality of `pyacquisition` (file I/O, logging, visualization) and all of the functionality of your `Instrument` and `Task` classes with robust data validation and error handling baked in.