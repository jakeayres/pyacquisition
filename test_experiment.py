from pyacquisition import Experiment, Measurement
from pyacquisition.instruments.software import Clock

#
#  This should be put pytested
#

class MyExperiment(Experiment):


    def __init__(self):
        super().__init__(data_path='data')

    
    def setup(self):
        
        clock = Clock("clock")
        self.add_instrument(clock)

        measurement = Measurement('time', clock.timestamp_ms)
        self.add_measurement(measurement)
        