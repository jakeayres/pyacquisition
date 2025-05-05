# Creating Custom Instruments

`pyacquisition` has implemented classes for a number of common instruments. The list is far from exhaustive. It is anticipated that you will need to write your own class that harnesses the functionality of your instrument. The process is simple. An outline of the workflow is as follows:

1. Compose your instrument inhereting from `Instrument` or `SoftwareInstrument`
2. Mark your public methods with either `@mark_command` or `@mark_query`
3. Add the instrument in `your_experiment.setup()`


## Example software instrument: Random Number Generator

Here we will run through the creation of an example software instrument (inheretting from `SoftwareInstrument`) -- a random number generator -- that illustrates how to implement your own instrument classes. The process for hardware instruments is the same except you need to inheret from the `Instrument` class.

### Compose the instrument class

Inheret from `SoftwareInstrument` and mark your query methods (methods that return values from your instrument) with the `@mark_query` decorator and command methods with the `@mark_command` decorator.

```python title="random_number_generator.py"
from pyacquisition import SoftwareInstrument
import random

class RandomNumberGenerator(SoftwareInstrument):
    """ A software random number generator instrument
    """

    @mark_query
    def random_integer(minimum: int, maximum: int) -> int:
        """Generates a random integer within a specified range.

        Args:
            minimum (int): The lower bound of the range (inclusive).
            maximum (int): The upper bound of the range (inclusive).

        Returns:
            int: A random integer between `minimum` and `maximum`.
        """
        return random.randint(minimum, maximum)
```

!!! Note
    **Type hints are mandatory**. `pyacquisition` uses type hints for both data validation and the generation of appropriate GUI widgets and are therefore non-optional. The docstring is not strictly requried but is used in the GUI as a helpful label if provided.


### Add the instrument to your experiment

```toml title="experiment_config.toml"
[experiment]
root_path = "C://data"

[data]
path = "my_data_folder"

[instruments]
clock = {instrument = "Clock"}

[measurements]
time = {instrument = "clock", method = "time"}
```


```python title="my_experiment.py"
from pyacquisition import Experiment
from .random_number_generator import RandomNumberGenerator

class MyExperiment(Experiment):


    def setup(self):

        self.rack.add_instrument('rng', RandomNumberGenerator())



if __name__ == "__main__":

    my_experiment = MyExperiment.from_config('experiment_config.toml')
    my_experiment.run()
```