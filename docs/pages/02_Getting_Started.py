import streamlit as st


st.title('Getting Started')

st.write('''The following is a detailed walk-through for users setting up their first experiment or measurement
	with `PyAcquisition`. This page runs step-by-step through a simple (one file) project that introduces and 
	explains the core functionality of `PyAcquisition`. If more complex behaviours are required, more can be learned
	from the more detailed pages accessible on the left. By working through a toy example, it is hoped that how to proceed with your own experiment will 
	be self-apparent.
	''')

st.success('''**Example Scenario**\n\n We would like to interface with a Stanford Research Instruments SR 830
	lockin amplifier and study the reference frequency and amplitude response of an input signal (perhaps the
	electrical voltage developed across a sample). The procedure involves setting a reference frequency and
	sweeping the reference amplitude between limits. We would like to visualize the data in real time and automate
	the recording of time-stamped voltages to a different and labelled file for each frequency.''')


st.write('#')
st.header("Building an ```Experiment```", divider=True)

st.write('''As a user, it is expected that for each experiment or measurement, you 
	will write a class that inherets from the `Experiment` class. The `Experiment` class 
	manages communication with instruments, logging, the recording of data to files and a task 
	queue to which instructions can be sent for sequential execution.''')

st.write('''The details of this functionality are intended to be managed "behind the scenes".
	As a user, you simply need to create your `experiment`, define what `instruments` you
	would like to interface with and define what `measurements` you would like to record in a `setup()`
	method.''')

st.write('''A "blank" experiment (that does nothing) may look like:''')


st.code('''
	from pyacquisition.experiment import Experiment


	class MyExperiment(Experiment):

		def setup(self):
			pass


	if __name__ == "__main__":

		my_experiment = MyExperiment()
		my_experiment.run()

	''', line_numbers=True)

st.write('''In the above, we have constructed a new experiment named `MyExperiment` with the necessary `setup()` method. We have yet 
	to add any instruments or define what we would actually like to record. Nevertheless, if `MyExperiment` is instantiated **[L.12]** and then run **[L.13]**, a
	user interface is generated that reveals most of the core functionality of `PyAcquisition`.
	''')

st.write('###')
st.subheader('`Scribe`: Recording of data to files')
st.write('###')
st.subheader('''`Rack`: Accessing instruments' functionality''')
st.write('###')
st.subheader('''`Experiment`: Managing the overall experiment''')
st.write('###')
st.subheader('''`Coroutines`: Queuing sequential tasks''')
st.write('###')
st.subheader('''`Plotting`: Visualizing your measurement data live''')


st.write('#')
st.header('Adding a `SoftwareInstrument`', divider=True)

st.write('''A `SoftwareInstrument` is an instrument that runs purely in software. I expect the most widely used `SoftwareInstrument`
	to be the `Clock`. In the simplest case, the `Clock` can be used to generate timestamps for your data. Beyond that, it can also
	be used to generate dates and manage timers. Lets add a `Clock` for recording timestamps.''')

st.write('''**1. Import the `Clock` instrument** with a simple import statement. All instruments can be imported from `pyacquisition.instruments`:''')
st.code('from pyacquisition.instruments import Clock')

st.write('''**2. Within `setup()`, add a `Clock` to the experiment** using the `add_software_instrument` method.
	The two arguments of `add_softare_instrument` are the label for your instrument and the instrument class to be added. It returns
	an instantiated instrument object (of type `Clock` in this case):''')
st.code('''
		my_clock = self.add_software_instrument('clock_name', Clock)
	''')


st.write('''**3. Also within `setup()`, add the `clock.time` measurement to the experiment** using the `add_measurement` method.
	The two arguements are a label for the measurement and a `callable` method or function that is expected to return a value. The method we
	will call is `my_clock.time` which returns a time (in seconds) since the object was instantiated (i.e. since the experiment was run):''')
st.code('''
		self.add_measurement('time', my_clock.time)
	''')
st.info('''**Note:** We do ***not*** want to call the `my_clock.time` method and pass the result to `add_measurement`. This would provide the
	experiment only with the current time from the clock. Instead, we want to pass the `my_clock.time` method itself such that the 
	experiment can repeatedly call the method and get live timestamps. `self.add_measurement('time', my_clock.time())` is incorrect.''')

st.write('The code thus far might look like:')


st.code('''
	from pyacquisition.experiment import Experiment
	from pyacquisition.instruments import Clock


	class MyExperiment(Experiment):

		def setup(self):
			my_clock = self.add_software_instrument('clock_name', Clock)
			self.add_measurement('time', my_clock.time)


	if __name__ == "__main__":

		my_experiment = MyExperiment()
		my_experiment.run()

	''', line_numbers=True)


st.write('''When run, you should now see that the live data stream has now been populated with a measurement named `time` that
	is recording the time since the code started running. This data is all being recorded to a file that can be managed by 
	the `Scribe` under the `Scribe` tab.''')

st.write('''Finally, you can also access additional functionality of the `Clock` by exploring within the `Rack` tab. 
	You should see that `my_clock` has been added to the `Rack` of instruments and that all of its functionality is accessible
	via automatically generated popup widgets.
	''')


st.write('#')
st.header('Adding a `HardwareInstrument`', divider=True)

st.write('''Adding a `HardwareInstrument` is much that same as adding a `SoftwareInstrument` except that an additional
	argument is required that specifies details of communication with the physical hardware. `PyAcquisition` has been designed
	to be as agnostic to these details as possible but mimic the behaviour `pyvisa`. For the purpose of this walkthrough, 
	we will interface with a Stanford Research Systems `SR_830` lock-in amplifier and use it to record the in-phase and 
	out-of-phase signals using a `pyvisa`-compatible interface like the National Instruments USB-GPIB adapter. ''')

st.subheader('Using `pyvisa`')

st.write('''If using a National Instruments USB-GPIB adapter or other physical hardware
	that is compatible with `pyvisa`, one can proceed as follows:
	''')

st.write('''**1. Import the `SR_830` instrument** with an import statement.''')
st.code('from pyacquisition.instruments import SR_830')

st.write('''**2. Within `setup()`, define a resource manager** that will handle details of the communication. In the simplest
	case, this is `pyvisa`. A full list of compatible communication backends are found ***here***:''')
st.code('''rm = resource_manager('pyvisa')''')


st.write('''**3. Also within `setup()`, add the `SR_830` to the experiment** using the `add_hardware_instrument` method.
	The three arguments of `add_hardware_instrument` are the label for your instrument, the instrument class to be added and
	the visa resource associated with the physical instrument. In this example, it is a visa instrument found at GPIB address `7`. 
	It returns an instantiated instrument object (of type `SR_830` in this case):''')
st.code('''
		my_lockin = self.add_hardware_instrument(
			'lockin_name', 
			SR_830, 
			rm.open_resource('GPIB0::7::INSTR')
		)''', line_numbers=True)


st.write('''**4. Also within `setup()`, add the `my_lockin.get_x` and `my_lockin.get_y` measurements to the experiment** using the `add_measurement` method.
	The two arguements for each of these methods are a label for the measurement and an appropriate `callable` method or function. The methods we
	will call are `my_lockin.get_x` and `my_lockin.get_y` which return the current in-phase and out-of-phase voltages from the `SR_830` device:''')
st.code('''
		self.add_measurement('x', my_lockin.get_x)
		self.add_measurement('y', my_lockin.get_y)
	''')
st.info('''**Note:** Again, we do not want to call the `get_x` and `get_y` methods and pass the result to `add_measurement`. 
	We want to pass the methods themselves such that the experiment can repeatedly call them and retrieve updated values from the
	instrument.''')


st.write('Your code may now look like:')


st.code('''
	from pyacquisition.experiment import Experiment
	from pyacquisition.instruments import Clock, SR_830


	class MyExperiment(Experiment):

		def setup(self):

			my_clock = self.add_software_instrument('clock_name', Clock)
			self.add_measurement('time', my_clock.time)

			rm = resource_manager('pyvisa')
			my_lockin = self.add_hardware_instrument(
				'lockin_name', 
				SR_830, 
				rm.open_resource('GPIB0::7::INSTR')
			)

			self.add_measurement('x', my_lockin.get_x)
			self.add_measurement('y', my_lockin.get_y)


	if __name__ == "__main__":

		my_experiment = MyExperiment()
		my_experiment.run()

	''', line_numbers=True)


st.write('''When run, you should now see two additional measurements in the stream of live data corresponding to
	the values displayed live on the front panel of your lock-in amplifier. You should also find your instrument
	in the `Rack` tab with the majority of the instrument's functionality accessible from within your program.''')

st.write('#')
st.header('Building a custom `Coroutine`', divider=True)

st.write('''You have now successfully interfaced with a hardware device and are recording timestamped data. This may
be sufficient if you are happy to operate your experiment (change relvant experimental conditions and instrument
settings) manually. For more automation, you can define a set of instructions within a `Coroutine` which can then be
added to the experiment's task queue.''')

st.write('''As an example, we will write a short `Coroutine` that will change the lock-in excitation frequency to
	a user-provided value and then sweep the excitation amplitude between user-provided limits. It will also automate
	the creation of new data files and generate a set of informative logs.''')

st.write('''To write a `Coroutine`, you need to create a new class that inherets from `pyacquuisition.Coroutine` 
	in the same way that your experiment inherets from `pyacquisition.Experiment` and define its functionality
	within some obligatory methods.''')

st.write('''A blank `Coroutine` looks as follows:''')

st.code('''

	from pyacquisition import Coroutine
	from dataclasses import dataclass


	@dataclass
	class MyCoroutine(Coroutine):

		def string(self):
			return 'An informative label'

		async def run(self):
			yield ''

	''', line_numbers=True)


st.write('''We have imported `Coroutine` from `PyAcquuisition`, `dataclass` from the `python` standard library and
	defined a new `Coroutine` named `MyCoroutine` with its two required methods. `MyCoroutine.string()` simply
	needs to return a descriptive string for the purpose of informing the user of its functionality/purpose 
	and logging. The asynchronous method `MyCoroutine.run()` is where the functionality is defined. This method
	needs to be an `async` method in order to run concurrently with other functions of your experiment (polling
	instruments and saving data to files etc.).''')

st.write('''To accept user-provided arguments, we can simply add properties to `MyCoroutine`. We will also need 
	to pass a reference to the lock-in instrument object such that `MyCoroutine` can access methods that control
	the instrument:''')

st.code('''

	from pyacquisition import Coroutine
	from dataclasses import dataclass
	from pyacquisition.instruments import SR_830


	@dataclass
	class MyCoroutine(Coroutine):

		lockin: SR_830
		frequency: float
		start_amplitude: float
		end_amplitude: float

		def string(self):
			return 'An informative label'

		async def run(self):
			yield ''

	''', line_numbers=True)

st.info('''In general, type hints are not required in `python`. Well known packages like `pydantic` utilize these
	type hints for the purpose of type checking. Similarly, `PyAcquisition` uses type hints for the purpose of both type
	checking (reducing errors) and generating appropriate widgets in the automatically generated user interface.''')


st.write('''We have imported `SR_830` from `pyacquisition.instrument` and added four properties to `MyCoroutine`.
	The first is of type `SR_830` (will be the lock-in object to be manipulated) and the others are of type `float`
	and correspond to user-provided parameters for our amplitude-sweep at fixed frequency.''')


st.write('''Next, we can update `MyCoroutine.string()` to display a more informative label and add some functionality
	to control the lock-in amplifier within `MyCoroutine.run()`:''')


st.code('''

	from pyacquisition import Coroutine
	from dataclasses import dataclass
	from pyacquisition.instruments import SR_830
	import asyncio


	@dataclass
	class MyCoroutine(Coroutine):

		lockin: SR_830
		frequency: float
		start_amplitude: float
		end_amplitude: float

		def string(self):
			return f'Frequency set to {self.frequency} Hz. Sweeping from {self.start_amplitude} to {self.end_amplitude} V.'

		async def run(self):
			self.lockin.set_frequency(self.frequency)
			
			amplitude = self.start_amplitude
			self.lockin.set_excitation(amplitude)
			await asyncio.sleep(1.0)

			while amplitude < self.end_amplitude:
				amplitude += 0.1
				self.lockin.set_excitation(amplitude)
				await asyncio.sleep(1.0)

			yield ''

	''', line_numbers=True)