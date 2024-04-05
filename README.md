# PyAcquisition

PyAcquisition is designed to facilitate the quick creation of measurement software.

## Quick Example

The following is a quick example demonstrating the fastest path to a working measurement program. The example is for the running of one Lakeshore 350 temperature controller and two Stanford Research SR_830 lock-in amplifiers for a typical resistivity measurement.

```python
# import base Experiment class
from pyacquisition.experiment import Experiment

# import necessary instrument classes
from pyacquisition.instruments import (
	Clock,
	Lakeshore_350,
	SR_830,
)

# import resource_manager
from pyacquisition.visa import resource_manager



# Design your experiment
# Inheret from the base Experiment class
MyExperiment(Experiment):

	# Define all of your instruments and measureables in
	# the setup() method.
	def setup(self):

		# Setup a resource manager
		# one of ('prologix', 'pyvisa', 'dummy')
		rm = resource_manager('prologix')

		# Clock() instrument (software instrument) for handling time stamps
		clock = self.add_software_instrument('Clock', Clock)

		# Lakeshore_350() temperature controller (hardware instrument)
		lake = self.add_hardware_instrument(
			'Lake', 
			Lakeshore_340, 
			rm.open_resource('GPIB0::2::INSTR')
		)

		# First lock-in amplifier (hardware instrument)
		lockin1 = self.add_hardware_instrument(
			'Lockin1', 
			SR_830, 
			rm.open_resource('GPIB0::7::INSTR')
		)

		# Second lock-in amplifier (hardware instrument)
		lockin2 = self.add_hardware_instrument(
			'Lockin2', 
			SR_830, 
			rm.open_resource('GPIB0::8::INSTR')
		)

		# Add measurements to the experiment
		# These need to be of type callable
		self.add_measurement('time', clock.time)
		self.add_measurement('temperature', partial(lake.get_temperature, InputChannel.INPUT_A))
		self.add_measurement('field', magnet.get_output_field)
		self.add_measurement('x1', lockin1.get_x)
		self.add_measurement('y1', lockin1.get_y)
		self.add_measurement('x2', lockin2.get_x)
		self.add_measurement('y2', lockin2.get_y)



if __name__ == "__main__":

	# Instantiate your experiment
	# Only required arg is the desired location of saved data
	exp = MyExperiment('./data/')

	# Run the experiment
	exp.run()
```

Without all of the verbose commenting and formatting, this looks like:


```python
from pyacquisition.experiment import Experiment
from pyacquisition.instruments import Clock, Lakeshore_350, SR_830
from pyacquisition.visa import resource_manager


MyExperiment(Experiment):

	def setup(self):

		rm = resource_manager('prologix')

		clock = self.add_software_instrument('Clock', Clock)
		lake = self.add_hardware_instrument('Lake', Lakeshore_340, rm.open_resource('GPIB0::2::INSTR'))
		lockin1 = self.add_hardware_instrument('Lockin1', SR_830, rm.open_resource('GPIB0::7::INSTR'))
		lockin2 = self.add_hardware_instrument('Lockin2', SR_830, rm.open_resource('GPIB0::8::INSTR'))

		self.add_measurement('time', clock.time)
		self.add_measurement('temperature', partial(lake.get_temperature, InputChannel.INPUT_A))
		self.add_measurement('field', magnet.get_output_field)
		self.add_measurement('x1', lockin1.get_x)
		self.add_measurement('y1', lockin1.get_y)
		self.add_measurement('x2', lockin2.get_x)
		self.add_measurement('y2', lockin2.get_y)


if __name__ == "__main__":
	exp = MyExperiment('./data/')
	exp.run()
```