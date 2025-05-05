Whilst all of the core functionality of `pyacquisition` can be configured using an input `.toml` file, there will be occasions when you want to utilize some custom code, import your own `Instrument` or `Task` classes. In these cases, you should write your own `Experiment` class and put your own functionality in the `setup()` and `teardown()` methods. In fact, you can forgo using an input configuration file altogether. The following is an example that is exactly equivalent to instantiating an experiment via the `.toml` file in the basics section.

```python title="my_experiment.py"
from pyacquisition import Experiment
from pyacqusition.instruments import Clock, SR_830

class MyExperiment(Experiment):


    def setup(self):


        self.rack.add_instrument('clock', Clock())
        self.rack.add_instrument('lockin', SR_830())


        self.rack.add_measurement('clock', )
        self.rack.add_measurement('clock', )

```