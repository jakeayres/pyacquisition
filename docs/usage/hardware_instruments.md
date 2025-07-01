<!-- #  -->


## Hardware instruments

Hardware instruments are associated with a physical instrument. `pyacquisition` has implemented classes for a number of common instruments. Interfacting with these instruments is as simple as adding them to your experiment either within the `setup()` method or via a `.toml` configuration file.

### Add to experiment in `setup()`


### Add to experiment in `.toml`


### Add measurement




## Creating new instruments

The list of instrument classes implemented in `pyacquisition` is far from exhaustive. It is anticipated that you will need to write your own class that harnesses the functionality of your instrument. 

The process is simple. An outline of the workflow is as follows:

1.   Compose your instrument inhereting from `Instrument` or `SoftwareInstrument`
2.   Mark your public methods with either `@mark_command` or `@mark_query`
3.   Add the instrument in the `setup()` method of your experiment


### Create an instrument class

For the purpose of this example, we will show a minimal implementation of a class that interfaces with a Stanford Research Systems SR830 lock-in amplifier. A complete class is present within `pyacqusition`.

```python title="SR_830.py" linenums="1"
from pyacquisition import Instrument


class SR_830(Instrument):


    def measure_x():
        pass


    def measure_y():
        pass
```

### Add instrument to Experiment

User-created instruments can only be added to an experiment within the `setup()` method of a custom defined experiment class.

### Measure voltages (X and Y)

