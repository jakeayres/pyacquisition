
## Software Instruments

Software instruments are *not* associated with a physical instrument and are defined entirely in software. The `Clock` is a simple example.

### Adding instruments in `setup()`


### Adding instruments in `.toml`



## Creating new software instruments


### Example: Random number generator

### Add to Experiment

### Measure random integers



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
